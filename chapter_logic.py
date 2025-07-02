from calendar import c
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import inspect

from pydantic import BaseModel

from server_communication.events import EventBuilder
if TYPE_CHECKING:
    from game import Game
    

import json
from generator import ObjectGenerator
from models.game_modes import GameMode
from models.schemas import (
    Character, 
    Scene, 
    ActionOutcome, 
    UserRequest, 
    RequestType, 
    ChangesToMake, 
    TurnList, 
    NextScene,
    ProactiveChangeType,
    AfterActionAnalysis
)
from server_communication.events import EventBuilder
from story_manager import StoryManager
from utils import *
from global_defines import *
from imagen import ImageGenerator
from classifier import Classifier
from prompter import Prompter


class CorrectionList(BaseModel):
    corrections: List[ChangesToMake]

class Chapter:
    """Fight logic for a chapter in a game, handling character interactions and actions."""

    
    def __init__(self, context: str, story_manager: StoryManager, game : 'Game', characters: List[Character] = [], language: str = "Russian"):
        self.context = context
        self.last_scene = context
        self.characters = characters        
        self.generator = ObjectGenerator()
        self.scene = None
        self.classifier = Classifier()
        self.language = language
        self.turn_order = [char.name for char in self.characters]
        self.current_turn = 0
        self.game_mode = GameMode.NARRATIVE
        self.story_manager = story_manager
        self.prompter = Prompter()
        self.event_log: List[Dict[str, Any]] = []
        self.game = game
        self.image_generator = ImageGenerator(game)
        self.image_generator.start()
        self.generate_scene()

    def generate_character(self, prompt : str, context : Optional[str]) -> Character:
        """Used to generate a NEW character. 

        Args:
            prompt (str): prompt for character generation

        Returns:
            Character: generated character
        """
        new_character =  self.generator.generate(
            pydantic_model=Character,
            prompt=prompt,
            context=context,
            language=self.language
        )
        self.image_generator.submit_generation_task(new_character.appearance, new_character.name)
        return new_character
         
    def add_character(self, character: Character):
        self.characters.append(character)
        self.turn_order.append(character.name)
        
    def log_event(self, event_type: str, **kwargs):
        """Logs a game event to the event log."""
        self.event_log.append({"event": event_type, "details": kwargs})
    
    def shuffle_turns(self):
        """
        Used to set up turn order (using AI).
        """
        prompt = f"""
<ROLE>
You are a D&D Turn Order Strategist. Your task is to analyze the current game situation and a list of characters to determine the most logical turn order for the upcoming round.
</ROLE>

<GOAL>
Create a new turn order for the characters involved in the scene. The order should reflect the flow of action, character initiative, and tactical common sense.
</GOAL>

<CONTEXT>
{self.get_actual_context()}
</CONTEXT>

<CHARACTERS_IN_SCENE>
{json.dumps(self.turn_order)}
</CHARACTERS_IN_SCENE>

<HEURISTICS_FOR_DETERMINING_TURN_ORDER>
1.  **Action-Reaction:** The character who was just targeted or is most immediately threatened by the last action should likely act soon. The character who just acted should typically be placed later in the new turn order.
2.  **Initiative & Alertness:** Characters who are alert, quick, or have high initiative (represented by dexterity) should generally act before slower or less aware characters.
3.  **Narrative Flow:** The order should make sense story-wise. If a goblin ambush was just described, the goblins should probably act first.
4.  **Inclusion Criteria:** Only include characters who are actively participating or are present and able to participate in the scene. If a character is unconscious (`is_alive: false`) or otherwise incapacitated, they should not be in the turn list.
</HEURISTICS_FOR_DETERMINING_TURN_ORDER>

<TASK>
Based on the context and heuristics, generate a JSON object that conforms to the `TurnList` model. The `turn_list` field should contain the names of the characters in the new logical order. The `reasoning` field should briefly explain your logic.
</TASK>
"""
        new_turns : TurnList = self.classifier.generate(
            contents=prompt,
            pydantic_model=TurnList,
        ) # type: ignore
        print(f"Raw turn shuffle result:{DEBUG_COLOR} {new_turns.turn_list}{Colors.RESET}")
        print(f"Reasoning : {new_turns.reasoning}") # type: ignore
        verify_turns = []
        for char in new_turns.turn_list:
            verify_turns.append(find_closest_match(char, self.turn_order))
        self.turn_order = verify_turns
        
    
    async def update_scene(self, scene_name: str, changes_to_make: str):
        """
        Updates the current scene with the provided changes.
        
        :param scene_name: The name of the scene to update.
        :param changes_to_make: A string describing the changes to apply.
        """
        print(f"\n{ENTITY_COLOR}{scene_name}{Colors.RESET} {INFO_COLOR}updates attributes with:{Colors.RESET} {changes_to_make}")
        try:
            original_scene_json = self.scene.model_dump_json(indent=2) # type: ignore
            self.log_event("scene_update_start", scene_name=scene_name, changes=changes_to_make, original_scene=original_scene_json)
            
            # Create a prompt that instructs the LLM to modify the scene based on relative changes
            prompt = f"""
<ROLE>
You are a meticulous D&D Game State Engine. Your task is to receive the current JSON data of a scene and a description of relative changes, then output a new, updated JSON object for that scene.
</ROLE>

<GAME_RULES>
1.  **Rule of Minimal Change:** Only modify fields that are directly and logically affected by the requested changes.
2.  **Rule of Atomicity:** Apply each change as a single, atomic operation.
</GAME_RULES>

<TASK>
Update the following scene's data based on the described changes.

<SCENE_DATA_BEFORE_CHANGES>
{original_scene_json}
</SCENE_DATA_BEFORE_CHANGES>

<CHANGES_TO_APPLY>
{changes_to_make}
</CHANGES_TO_APPLY>

<OUTPUT_INSTRUCTIONS>
Your response must be ONLY the complete, updated JSON object for the scene. Do not include any explanations, markdown formatting, or any other text outside of the final JSON structure.
</OUTPUT_INSTRUCTIONS>
"""

            self.scene = self.generator.generate(
                pydantic_model=Scene,
                prompt=prompt,
                language=self.language
            )
            
            update_log = f"<SCENE_UPDATE>\n<NAME>{scene_name}</NAME>\n<CHANGES>{changes_to_make}</CHANGES>\n</SCENE_UPDATE>"
            self.context += f"\n{update_log}\n"
            self.log_event("scene_update_success", scene_name=scene_name, changes=changes_to_make)
            
            print(f"{SUCCESS_COLOR} Scene updated successfully!{Colors.RESET}")
        except Exception as e:
            print(f"{ERROR_COLOR} Error updating scene: {e}{Colors.RESET}")
            self.log_event("scene_update_failure", scene_name=scene_name, error=str(e))
            raise e
    
    async def update_character(self, character_name: str, changes_to_make: str):
        """
        Updates a character's attributes based on the provided changes using a robust, rule-based LLM prompt.
        
        :param character_name: The name of the character to update.
        :param changes_to_make: A string describing the changes to apply.
        """
        print(f"\n{ENTITY_COLOR}{character_name}{Colors.RESET} {INFO_COLOR}updates attributes with:{Colors.RESET} {changes_to_make}")
        try:        
            char_name_list = [char.name for char in self.characters]
            char_dict = {char.name: char for char in self.characters}
            
            target_char_name = find_closest_match(character_name, char_name_list)
            character = char_dict[target_char_name]
            # Convert the current character object to a JSON string for clean input to the LLM
            character_json = character.model_dump_json(indent=2)
            self.log_event("character_update_start", character_name=character_name, changes=changes_to_make, original_character=character.model_dump())

            prompt = f"""
<ROLE>
You are a meticulous D&D Game State Engine. Your task is to receive the current JSON data of a character and a description of relative changes, then output a new, updated JSON object for that character. You must follow the game rules precisely and only output the final JSON.
</ROLE>

<GAME_RULES>
You MUST strictly follow these rules when updating the character. These rules have absolute priority.

1.  **Rule of Life and Death:** If a character takes damage that reduces their `current_hp` to 0 or below, you MUST set `current_hp` to exactly `0` and set `is_alive` to `false`. A character cannot have negative HP. Conversely, if a dead character is healed, their `is_alive` status must become `true`.

2.  **Rule of Inventory Management:** If the changes describe an item being added or removed, you MUST update the `inventory` list accordingly.

3.  **Rule of Armor Class (AC):** If a character equips or unequips armor or a shield, you MUST adjust their `ac` value accordingly.

4.  **Rule of Health Cap:** A character's `current_hp` can NEVER exceed their `max_hp`. If healing would take them above the maximum, cap it at `max_hp`.

5.  **Rule of Minimal Change:** Only modify fields that are directly and logically affected by the requested changes. Do NOT change unrelated fields like `personality_history`, `abilities`, or `appearance` unless the changes explicitly require it.
</GAME_RULES>

<TASK>
Update the following character's data based on the described changes.

<CHARACTER_DATA_BEFORE_CHANGES>
{character_json}
</CHARACTER_DATA_BEFORE_CHANGES>

<CHANGES_TO_APPLY>
{changes_to_make}
</CHANGES_TO_APPLY>

<OUTPUT_INSTRUCTIONS>
Your response must be ONLY the complete, updated JSON object for the character. Do not include any explanations, markdown formatting, or any other text outside of the final JSON structure.
</OUTPUT_INSTRUCTIONS>
    """
            
            if character:
                self.characters.remove(character) 
            
            updated_character = self.generator.generate(
                pydantic_model=Character,
                prompt=prompt,
                language=self.language
            )
            self.characters.append(updated_character)
            
            update_log = f"<CHARACTER_UPDATE>\n<NAME>{character_name}</NAME>\n<CHANGES>{changes_to_make}</CHANGES>\n</CHARACTER_UPDATE>"
            self.context += f"\n{update_log}\n"
            self.log_event("character_update_success", character_name=character_name, changes=changes_to_make)
            
            print(f"{SUCCESS_COLOR} Character '{updated_character.name}' updated successfully!{Colors.RESET}")
            
            # Add a clear message if the character's life status changed
            if not updated_character.is_alive and character.is_alive:
                print(f"{ERROR_COLOR} Character {updated_character.name} has died!{Colors.RESET}")
                self.log_event("character_death", character_name=updated_character.name)

        except Exception as e:
            print(f"{ERROR_COLOR} Error updating character: {e}{Colors.RESET}")
            self.log_event("character_update_failure", character_name=character_name, error=str(e))
            # Optionally re-add the original character on any failure
            if 'character' in locals() and character not in self.characters: # type: ignore
                self.characters.append(character) # type: ignore
            raise e
            
    def generate_scene(self, scene_prompt: Optional[NextScene] = None):
        # If this is the very first scene generation, use the story's starting info.
        if self.scene is None:
            current_plot = self.story_manager.get_current_plot_point()
            if current_plot:
                prompt = f"""
                Generate the very first scene for our D&D campaign.
                The campaign is titled '{self.story_manager.story.title}'.
                The players are starting in a location called '{self.story_manager.story.starting_location}'.
                The current objective is: '{current_plot.title} - {current_plot.description}'.
                Based on this, create a compelling and detailed opening scene.
                The scene should be mysterious and engaging, drawing the players into the world.
                """
            else:
                prompt = f"""
                Generate the very first scene for our D&D campaign.
                The campaign is titled '{self.story_manager.story.title}'.
                The players are starting in a location called '{self.story_manager.story.starting_location}'.
                The initial objective is not clear, so create a scene of arrival with an air of mystery.
                The scene should be mysterious and engaging, drawing the players into the world.
                """
            scene_d : NextScene = self.classifier.generate(prompt, NextScene) # type: ignore
        elif scene_prompt is None:
            scene_d : NextScene = self.classifier.generate(
                f"Generate a scene description and difficulty based on the context: {self.context}",
                NextScene
            ) # type: ignore
        else:
            scene_d : NextScene = scene_prompt

        self.scene = self.generator.generate(
            pydantic_model=Scene,
            prompt=str(scene_d.scene_description), # type: ignore
            context=self.context,
            language=self.language
        )
        
        if scene_d.new_characters:
            for character in scene_d.new_characters:
                print(f"(generate_scene) New character {character}")
                self.add_character(
                    self.generator.generate(Character, character) 
                )

        print(f"\n{SUCCESS_COLOR}Generated Scene:{Colors.RESET} {ENTITY_COLOR}{self.scene.name}{Colors.RESET}")
        print(f"{INFO_COLOR} Difficulty: {scene_d.scene_difficulty}{Colors.RESET}") # type: ignore
        print(f"{INFO_COLOR} Description:{Colors.RESET} {self.scene.description}")
        self.log_event("scene_generated", scene_name=self.scene.name, description=self.scene.description, difficulty=scene_d.scene_difficulty) # type: ignore
        self.image_generator.submit_generation_task(self.scene.description , self.scene.name, generation_type="SCENE")


    def setup_fight(self):
        """
        Initializes the fight by generating objects and their actions based on the context.
        """
        self.game_mode = GameMode.COMBAT
        print(f"\n{HEADER_COLOR} Generating Scene...{Colors.RESET}")
        
        
        # Here i remove unnecessary parts from the context to reduce memory usage
        self.context = self.classifier.general_text_llm_request(
        f"""
            Provide the details that matter for the next scene. 
            Store which characters are allied with which ones and what can change this alliance. Store their motivations and goals.
            Dont ask additional information.
            Imagine where all the players should be located in the scene. Dont analyze characters at all.
            Give more attention to the script and story and less to the scene and characters details.
            IMPORTANT: Keep your response maximum {MAX_CONTEXT_LENGTH} words.
            ---
            <Context>
            {self.get_actual_context()}
            </Context>
        """
        )
        
        self.turn_order = [char.name for char in self.characters]
        # random.shuffle(self.turn_order)
        self.shuffle_turns()
        print(f"{INFO_COLOR}Turn order shuffled{Colors.RESET}")
        
        
    def move_to_next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.turn_order) # type: ignore

    def get_active_character_name(self) -> str:
        return self.turn_order[self.current_turn] # type: ignore

    def get_active_character(self) -> Character: # type: ignore
        for character in self.characters:
            if character.name == self.get_active_character_name():
                return character

    def get_actual_context(self, active_character_name = None) -> str:
        """
        Generates a comprehensive and clearly structured JSON string representing the current game state.
        An optional active_character_name can be provided to mark who is currently acting.
        """
        all_characters_data = []
        for char in self.characters:
            char_data = char.model_dump()
            # Mark the active character if one is specified
            if active_character_name and char.name == active_character_name:
                char_data['is_currently_acting'] = True
            else:
                char_data['is_currently_acting'] = False
            all_characters_data.append(char_data)

        # NEW: Include the last 10 events for short-term memory
        recent_events = self.event_log[-10:]

        context_dict = {
            "game_state": {
                "summary_of_past_events": self.context,
                "recent_events": recent_events,  # <-- ADDED
                "current_scene": self.scene.model_dump() if self.scene else "No scene is currently active.",
                "participants": {
                    "description": "A list of all characters currently in the scene.",
                    "characters": all_characters_data
                }
            },
            "global_story_context": self.story_manager.get_current_plot_context()
        }

        return f"<CONTEXT_DATA>\n{json.dumps(str(context_dict), indent=2, ensure_ascii=False)}\n</CONTEXT_DATA>"
    
    def trim_context(self):
        print(f"\n{DEBUG_COLOR}Context trimming...{Colors.RED} {len(self.context)} chars of context {Colors.RESET}") # type: ignore
        print(f"{Colors.RED}context before{self.context}")
        self.context = self.classifier.general_text_llm_request(
            f"""
<ROLE>
Ты — ассистент Мастера Игры. Твоя задача — сжать длинную историю в краткую, но информативную сводку для следующей сцены.
</ROLE>

<FULL_CONTEXT>
{self.get_actual_context()}
</FULL_CONTEXT>

<TASK>
<TASK>
Создай новую сводку (не более {MAX_CONTEXT_LENGTH} слов), которая сохраняет только самую важную информацию для предстоящей сцены. Обязательно включи в нее:
1.  **Расположение персонажей:** Проанализируй и кратко опиши, где находятся все персонажи в текущей сцене.
2.  **Основная цель:** Какова главная цель группы авантюристов в данный момент?
3.  **Основная цель врагов:** Какова главная цель их противников?
4.  **Ключевые отношения:** Какие союзы или конфликты существуют между персонажами?
5.  **Важные детали прошлого:** Упомяни 1-2 самых важных события из прошлого, которые напрямую влияют на текущую мотивацию персонажей.
6.  **Намерение DM:** Если в тексте есть намеки на будущие события или секреты от Мастера, сохрани их.

Не включай в сводку нерелевантные детали или описания уже прошедших действий, если они не влияют на будущее.
</TASK>
</TASK>
"""
        )
        print(f"{Colors.GREEN}context after{self.context} {Colors.RESET}")
        

    async def process_interaction(self, character: Character, interaction: str):
        """
        Processes a character's interaction, deciding the outcome of actions and questions.
        Returns a tuple containing the event generator and a boolean indicating if a turn-consuming action was taken.
        """
        if not character.is_alive:
            # return self.askedDM(character, interaction), False
            pass

        # Get the full game context to help the AI make a better decision
        context = self.get_actual_context(active_character_name=character.name)

        user_request: UserRequest = self.classifier.generate(
            contents=f"""
<ROLE>
You are an intelligent request router for a D&D game. Your task is to analyze a player's request in the context of recent events and classify it as either an in-game character action OR a meta-question to the Dungeon Master.
</ROLE>

<TASK_DEFINITION>
Analyze the player's request below, using the provided game context. Your goal is to determine if the player is speaking **AS THEIR CHARACTER** (performing an action) or **AS A PLAYER** (asking a question to the DM).
</TASK_DEFINITION>

<CONTEXT_AWARENESS_RULE>
**CRITICAL:** You MUST use the `<CONTEXT_FOR_DECISION>` to understand the flow of conversation. A player's message might look like a question out of context, but be a direct reply to an NPC in the context of the recent events.

*   **Example:** If an NPC just asked the player, "Do you yield?", the player's response "Do you know who I am?" is a **Character Action** (a defiant, in-character response), NOT a question to the DM.
</CONTEXT_AWARENESS_RULE>

<CATEGORY_DEFINITIONS>
1.  **Действие Персонажа (Character Action) -> `request_type: 'action'`**
    *   The player describes what their character is doing, saying, or attempting within the game world.
    *   This includes direct replies to NPCs, even if phrased as a question.
    *   **Keywords:** "Я атакую", "Я иду", "Я говорю ему", "Я осматриваю комнату".

2.  **Запрос к Мастеру (Query to the DM) -> `request_type: 'question'`**
    *   The player asks a question directly to the Dungeon Master about rules, the world, or their character's state. This is a meta-request for information.
    *   **Keywords:** "Что я вижу?", "Могу ли я...?", "Расскажи подробнее о...", "OOC".
</CATEGORY_DEFINITIONS>

<CONTEXT_FOR_DECISION>
{self.get_actual_context()}
</CONTEXT_FOR_DECISION>

<PLAYER_REQUEST_TO_CLASSIFY>
{interaction}
</PLAYER_REQUEST_TO_CLASSIFY>

<OUTPUT_INSTRUCTIONS>
Provide your response as a single JSON object matching the `UserRequest` model, with no other text.
</OUTPUT_INSTRUCTIONS>
""",
            pydantic_model=UserRequest
        ) # type: ignore
        
        return self.process_player_input(character, user_request), user_request.request_type == "action"

    async def process_player_input(self, character: Character, user_request: UserRequest, is_NPC = False):
        """
        Executes an action and immediately gets both the narrative and the structured changes.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}performs action:{Colors.RESET} {user_request.text}")
        self.log_event("action_start", character_name=character.name, action_text=user_request.text, is_npc=is_NPC)

        # Use a generator that can directly output a Pydantic object
        outcome: ActionOutcome = self.generator.generate(
            pydantic_model=ActionOutcome,
            prompt=self.prompter.get_process_player_input_prompt(self, character, user_request, is_NPC),
            language=self.language
        )

        narrative = outcome.narrative_description
        changes = outcome.structural_changes
        changes_as_dicts = [change.model_dump() for change in changes]
        self.log_event("action_outcome", character_name=character.name, narrative=narrative, changes=changes_as_dicts, is_legal=outcome.is_legal)

        # The rest of the a
        action_summary = f"Action by {character.name}: '{user_request.text}'. Outcome: {narrative}"
        self.context += f"\n\n<ACTION_LOG>\n{action_summary}\n</ACTION_LOG>\n"
        yield EventBuilder.DM_message(narrative) # type: ignore

        if is_NPC: outcome.is_legal = True
        
        if outcome.is_legal:
            if changes:
                for i, change in enumerate(changes, 1):
                    if change.object_type == "character":
                        await self.update_character(change.object_name, change.changes)
                    elif change.object_type == "scene":
                        await self.update_scene(change.object_name, change.changes)
                        
                    yield EventBuilder.state_update_required(
                        update=f"{change.object_name} был обновлен ({change.changes})",
                        total=len(changes), 
                        current=i
                    )
                    yield EventBuilder.alert(f"{change.object_name}: {change.changes}", inspect.currentframe().f_code.co_name) # type: ignore
            else:
                self.context += "<ACTION_OUTCOMES>No structural changes occurred.</ACTION_OUTCOMES>"
            
            async for event in self.audit_action_application(outcome):
                yield event

            print(f"{SUCCESS_COLOR}All changes applied successfully{Colors.RESET}")    
            async for value in self.after_action(outcome):
                yield value
        else:
            self.context += f"\n<ACTION_FAILURE>Action by {character.name} ('{user_request.text}') was deemed illegal. No changes were made.</ACTION_FAILURE>\n"
            yield EventBuilder.alert("Impossible to act...", inspect.currentframe().f_code.co_name) # type: ignore

    async def audit_action_application(self, outcome: ActionOutcome):
        """
        Audits the result of an action, finds discrepancies, and applies corrections.
        """
        print(f"\n{INFO_COLOR}Auditing application of action: {outcome.narrative_description[:50]}...{Colors.RESET}")

        prompt = self.prompter.get_audit_prompt(self, outcome)

        
        correction_wrapper = self.generator.generate(
            pydantic_model=CorrectionList,
            prompt=prompt,
            language=self.language
        )

        corrections = correction_wrapper.corrections

        if not corrections:
            print(f"{SUCCESS_COLOR}Audit passed. No corrections needed.{Colors.RESET}")
            return

        print(f"{WARNING_COLOR}Audit found {len(corrections)} discrepancies. Applying corrections...{Colors.RESET}")
        self.log_event("audit_found_discrepancies", count=len(corrections), corrections=corrections)

        for change in corrections:
            try:
                if change.object_type == "character":
                    await self.update_character(change.object_name, change.changes)
                elif change.object_type == "scene":
                    await self.update_scene(change.object_name, change.changes)
                yield EventBuilder.alert(f"AUDIT CORRECTION: {change.object_name}: {change.changes}", inspect.currentframe().f_code.co_name) # type: ignore
            except Exception as e:
                print(f"{ERROR_COLOR}Failed to apply audit correction: {e}{Colors.RESET}")
                self.log_event("audit_correction_failed", error=str(e), change=change)
    
    def get_character_by_name(self, name: str) -> Character:
        """
        Finds and returns a character object by its name using fuzzy matching.

        :param name: The name of the character to find.
        :return: The Character object with the closest matching name.
        :raises Exception: If no character is found.
        """
        char_name_list = [char.name for char in self.characters]
        char_dict = {char.name: char for char in self.characters}
        
        try:
            target_char_name = find_closest_match(name, char_name_list)
            return char_dict[target_char_name]
        except ValueError as e:
            # Re-raise with a more specific message
            raise Exception(f"Character '{name}' not found. {e}")

    def get_last_dm_messages(self, n: int) -> str:
        """
        Retrieves the last n messages from the DM.
        """
        dm_messages = [msg['message_text'] for msg in self.game.message_history if msg['sender_name'] == 'DM']
        last_n_messages = dm_messages[-n:]
        return "\n".join(last_n_messages)
    
    
    async def after_action(self, outcome: ActionOutcome):
        """
        Analyzes the outcome of an action to determine game mode changes and proactive world events.
        This combines the previous turn analysis and narrative analysis into a single LLM call.
        """
        print(f"\n{HEADER_COLOR}Analyzing turn outcome...{Colors.RESET}")

        # 1. Get the combined analysis from the LLM
        analysis: AfterActionAnalysis = self.generator.generate(
            pydantic_model=AfterActionAnalysis,
            prompt=self.prompter.get_after_action_analysis_prompt(self),
            language="Russian"
        )
        print(f"{DEBUG_COLOR}Raw analysis: {analysis.model_dump_json(indent=2)}{Colors.RESET}")

        # 2. Handle Game Mode Change
        if self.game_mode != analysis.recommended_mode:
            self.game_mode = analysis.recommended_mode
            yield EventBuilder.alert(f'Game mode changed to <span class="keyword">{self.game_mode.name}</span>', inspect.currentframe().f_code.co_name) # type: ignore

        # 3. Process Proactive World Changes
        if self.game_mode == GameMode.NARRATIVE:
            for change in analysis.proactive_world_changes:
                try:
                    if not isinstance(change.change_type, ProactiveChangeType):
                        print(f"{WARNING_COLOR}Skipping invalid change type: {change.change_type}{Colors.RESET}")
                        continue

                    payload = change.payload
                    change_type = change.change_type

                    if change_type in {ProactiveChangeType.ADD_OBJECT, ProactiveChangeType.UPDATE_OBJECT, ProactiveChangeType.REMOVE_OBJECT, ProactiveChangeType.UPDATE_SCENE, ProactiveChangeType.UPDATE_CHARACTER}:
                        if hasattr(payload, 'object_type') and hasattr(payload, 'object_name') and hasattr(payload, 'changes'):
                            if payload.object_type == "character": # type: ignore
                                await self.update_character(payload.object_name, payload.changes) # type: ignore
                            elif payload.object_type == "scene": # type: ignore
                                await self.update_scene(payload.object_name, payload.changes) # type: ignore
                            yield EventBuilder.alert(f"(narrative){payload.object_name}: {payload.changes}", inspect.currentframe().f_code.co_name) # type: ignore
                        else:
                            raise TypeError(f"Invalid payload for {change_type}: {payload}")

                    elif change_type == ProactiveChangeType.ADD_CHARACTER:
                        new_char = self.generate_character(change.description, self.context)
                        self.add_character(new_char)
                        yield EventBuilder.alert(f"(narrative) A new character, {new_char.name}, appears: {change.description}", inspect.currentframe().f_code.co_name) # type: ignore

                    elif change_type == ProactiveChangeType.REMOVE_CHARACTER:
                        if isinstance(payload, str):
                            char_to_remove = self.get_character_by_name(payload)
                            self.characters.remove(char_to_remove)
                            yield EventBuilder.alert(f"(narrative){payload} was removed: {change.description}", inspect.currentframe().f_code.co_name) # type: ignore
                        else:
                            raise TypeError(f"REMOVE_CHARACTER payload must be a string, but got {type(payload)}")

                    elif change_type == ProactiveChangeType.CHANGE_SCENE:
                        if isinstance(payload, NextScene):
                            self.generate_scene(payload)
                        else:
                            raise TypeError(f"CHANGE_SCENE payload must be a NextScene object, but got {type(payload)}")
                    
                    else:
                        print(f"{WARNING_COLOR}Unhandled proactive change type: {change_type}{Colors.RESET}")

                except Exception as e:
                    error_message = f"Error processing proactive change '{change.change_type}': {e}"
                    print(f"{ERROR_COLOR}{error_message}{Colors.RESET}")
                    yield EventBuilder.error(error_message)
                    continue
        
            self.story_manager.check_and_advance(self.context)

        # 4. End of Turn and Context Trimming
        yield EventBuilder.end_of_turn()
        if len(self.context) > MAX_CONTEXT_LENGTH_CHARS:
            self.trim_context()
            if self.context:
                print(f"{SUCCESS_COLOR}Context updated{Colors.RESET}")

    async def NPC_turn(self):
        """
        Handles the npc's turn in the fight.
        """
        active_char = self.get_active_character()
        print(f"\n{HEADER_COLOR}NPC's turn: {active_char.name}{Colors.RESET}")
        
        context_with_active_char = self.get_actual_context(active_character_name=active_char.name)
        
        NPC_action_prompt = f"""
<ROLE>
Ты — тактический ИИ, управляющий неигровым персонажем (NPC) в бою в D&D.
Твоя задача — выбрать наиболее логичное, тактически верное и соответствующее характеру действие для этого NPC на его ходу.
</ROLE>

<CHARACTER_PROFILE>
{active_char.model_dump_json(indent=2)}
</CHARACTER_PROFILE>

<SITUATION_CONTEXT>
{context_with_active_char}
</SITUATION_CONTEXT>

<TACTICAL_HEURISTICS>
Проанализируй ситуацию и выбери действие, основываясь на следующих приоритетах:

1.  **Самосохранение (Высший приоритет):**
    *   Если у NPC **мало здоровья** (`current_hp` < 25% от `max_hp`), его главный приоритет — выживание.
    *   **Действия:** Использовать лечащее зелье, применить способность к исцелению, выйти из боя (если это соответствует характеру), найти укрытие или использовать защитное умение.

2.  **Выполнение Роли:**
    *   **Целитель (Healer):** Если союзники ранены, основная задача — лечить их. Атаковать только в крайнем случае.
    *   **Танк (Tank):** Защищать более слабых союзников. Привлекать на себя внимание самых опасных врагов, использовать провоцирующие умения.
    *   **ДД (Damage Dealer):** Наносить максимальный урон. Фокусироваться на самых опасных или уязвимых целях (враги с низким HP, вражеские лекари или маги).
    *   **Контроль (Controller):** Использовать способности, которые ослабляют врагов или контролируют поле боя (оглушение, паралич, создание препятствий).

3.  **Тактическое Преимущество:**
    *   **Фокусировка огня:** Если другие NPC уже атакуют одну цель, присоединяйся к ним, чтобы быстрее ее уничтожить.
    *   **Устранение угроз:** В первую очередь выводи из строя врагов, которые представляют наибольшую угрозу (те, кто наносит много урона, лечит или контролирует).
    *   **Использование окружения:** Если в описании сцены есть интерактивные объекты (`scene.objects`), которые можно использовать в бою (сбросить люстру, опрокинуть стол), рассмотри возможность их использования.
    *   **Позиционирование:** Перемещайся, чтобы занять выгодную позицию (например, лучнику — на возвышенность, разбойнику — за спину врага).

4.  **Соответствие Характеру:**
    *   **Трус (Cowardly):** Будет атаковать только слабых или исподтишка. При малейшей опасности попытается сбежать.
    *   **Берсерк (Berserk):** Всегда будет атаковать ближайшего врага самым мощным оружием, не думая о последствиях.
    *   **Тактик (Tactician):** Будет действовать согласно вышеописанным тактическим приоритетам, выбирая самое умное действие.
</TACTICAL_HEURISTICS>

<TASK>
Проанализируй профиль персонажа, его роль, состояние и тактическую обстановку. Выбери его следующее действие.
Твой ответ должен быть **короткой фразой, описывающей действие от первого лица**, как будто ее говорит игрок.
Не пиши полную историю, только само действие.

**Примеры хороших ответов:**
- "Атакую Бориса Бритву своим ледяным копьем, целясь в его раненое плечо."
- "Использую 'Ледяную стену', чтобы отрезать вражеского лекаря от его союзников."
- "Я тяжело ранен, поэтому отступаю за колонну и пью лечебное зелье."
- "Защищаю нашего мага, становясь между ним и ворвавшимся орком."

Твой ответ:
"""
        NPC_action = self.classifier.general_text_llm_request(NPC_action_prompt)
        user_request = UserRequest(request_type=RequestType.ACTION, text=NPC_action)
        async for value in self.process_player_input(self.get_active_character(), user_request, is_NPC=True):
            yield value
