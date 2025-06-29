from typing import TYPE_CHECKING

from server_communication.events import EventBuilder
if TYPE_CHECKING:
    from game import Game
    

import json
from dotenv import load_dotenv
from generator import ObjectGenerator
from models.game_modes import GameMode
from models import *
from server_communication.events import EventBuilder
from story_manager import StoryManager
from utils import *
from global_defines import *
import global_defines
from models import *
from imagen import ImageGenerator
from classifier import Classifier
from prompter import Prompter
from imagen import ImageGenerator


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
        self.prompter = Prompter()
        self.story_manager = story_manager
        self.event_log: List[Dict[str, Any]] = []
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
        self.image_generator.submit_generation_task(new_character.model_dump_json(), new_character.name)
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
            self.scene = self.generator.generate(
                pydantic_model=Scene,
                prompt=f"""
                Make following changes to the scene:
                {str(self.scene)}
                Changes to make: {changes_to_make}
                """,
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
You are a meticulous D&D Game State Engine. Your task is to receive the current JSON data of a character and a description of changes, then output a new, updated JSON object for that character. You must follow the game rules precisely and only output the final JSON.
</ROLE>

<GAME_RULES>
You MUST strictly follow these rules when updating the character. These rules have absolute priority.

1.  **Rule of Life and Death:** If a character takes damage that reduces their `current_hp` to 0 or below, you MUST set `current_hp` to exactly `0` and set `is_alive` to `false`. A character cannot have negative HP. Conversely, if a dead character is healed, their `is_alive` status must become `true`.

2.  **Rule of Inventory Management:** If the changes describe an item being used up (like a potion), destroyed, dropped, or unequipped (like a character taking off their armor), you MUST remove that item from the `inventory` list.

3.  **Rule of Armor Class (AC):** If a character equips or unequips armor or a shield, you MUST adjust their `ac` value accordingly. If an item providing AC is removed from inventory (Rule 2), the `ac` value must be decreased.

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
                Based on this, create a compelling and detailed opening scene. Describe the atmosphere, the immediate surroundings, and introduce the initial situation or NPC from the campaign prompt: '{self.story_manager.story.initial_character_prompt}'.
                The scene should be mysterious and engaging, drawing the players into the world.
                """
            else:
                prompt = f"""
                Generate the very first scene for our D&D campaign.
                The campaign is titled '{self.story_manager.story.title}'.
                The players are starting in a location called '{self.story_manager.story.starting_location}'.
                The initial objective is not clear, so create a scene of arrival with an air of mystery.
                Introduce the initial situation or NPC from the campaign prompt: '{self.story_manager.story.initial_character_prompt}'.
                The scene should be mysterious and engaging, drawing the players into the world.
                """
            scene_d = self.classifier.generate(prompt, NextScene)
        elif scene_prompt is None:
            scene_d = self.classifier.generate(
                f"Generate a scene description and difficulty based on the context: {self.context}",
                NextScene
            )
        else:
            scene_d = scene_prompt

        self.scene = self.generator.generate(
            pydantic_model=Scene,
            prompt=str(scene_d),
            context=self.context,
            language=self.language
        )

        print(f"\n{SUCCESS_COLOR}Generated Scene:{Colors.RESET} {ENTITY_COLOR}{self.scene.name}{Colors.RESET}")
        print(f"{INFO_COLOR} Difficulty: {scene_d.scene_difficulty}{Colors.RESET}") # type: ignore
        print(f"{INFO_COLOR} Description:{Colors.RESET} {self.scene.description}")
        self.log_event("scene_generated", scene_name=self.scene.name, description=self.scene.description, difficulty=scene_d.scene_difficulty) # type: ignore
        self.image_generator.submit_generation_task(self.scene.description , self.scene.name)


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

        context_dict = {
            "game_state": {
                "summary_of_past_events": self.context,
                "current_scene": self.scene.model_dump() if self.scene else "No scene is currently active.",
                "participants": {
                    "description": "A list of all characters currently in the scene.",
                    "characters": all_characters_data
                }
            },
            "global_story_context": self.story_manager.get_current_plot_context()
        }

        return f"<CONTEXT_DATA>\n{json.dumps(context_dict, indent=2, ensure_ascii=False)}\n</CONTEXT_DATA>"






    async def action(self, character: Character, action_text: str, is_NPC = False):
        """
        Executes an action and immediately gets both the narrative and the structured changes.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}performs action:{Colors.RESET} {action_text}")
        self.log_event("action_start", character_name=character.name, action_text=action_text, is_npc=is_NPC)

        # Use a generator that can directly output a Pydantic object
        # лол
        # это вообще не та функция, которую я сюда планировал
        outcome: ActionOutcome = self.generator.generate(
            pydantic_model=ActionOutcome,
            prompt=self.prompter.get_action_prompt(self, character, action_text, is_NPC),
            language=self.language
        )

        narrative = outcome.narrative_description
        changes = outcome.structural_changes
        changes_as_dicts = [change.model_dump() for change in changes]
        self.log_event("action_outcome", character_name=character.name, narrative=narrative, changes=changes_as_dicts, is_legal=outcome.is_legal)

        # The rest of the a
        action_summary = f"Action by {character.name}: '{action_text}'. Outcome: {narrative}"
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
                    yield EventBuilder.alert(f"{change.object_name}: {change.changes}")
            else:
                self.context += "<ACTION_OUTCOMES>No structural changes occurred.</ACTION_OUTCOMES>"
            print(f"{SUCCESS_COLOR}All changes applied successfully{Colors.RESET}")    
            async for value in self.after_action(outcome):
                yield value
        else:
            self.context += f"\n<ACTION_FAILURE>Action by {character.name} ('{action_text}') was deemed illegal. No changes were made.</ACTION_FAILURE>\n"
            yield EventBuilder.alert("Impossible to act...")
        
    async def askedDM(self, character: Character, question: str):
        """
        Handles a character asking the DM a question, ensuring the response is in the second person.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}asks:{Colors.RESET} {question}")
        self.log_event("asked_dm", character_name=character.name, question=question)
        
        # Pass the active character's name to get the right context
        context_with_active_char = self.get_actual_context(active_character_name=character.name)
        
        prompt = f"""
<ROLE>
{global_defines.dungeon_master_core_prompt}
</ROLE>

<TASK>
1.  **Identify the Player:** In the `<CONTEXT_DATA>` and `<PLAYER_WHO_IS_ASKING>`, find the character where `is_currently_acting` is `true`. This is the player you are speaking to.
2.  **Address Them Directly:** Formulate your response in the second person, as if you are speaking directly to that player. Use "you" and "your".
3.  **Answer the Question:** Based on the full context provided, answer the player's question clearly and concisely.
4.  **Use Highlighting:** Emphasize important keywords and names using `<span class='keyword'>keyword</span>` and `<span class='name'>Name</span>` tags.
5.  **Do Not Affect the World:** Your response is purely informational. It should not cause any changes to the game state.
</TASK>

<EXAMPLE>
- **Player's Question:** "What do I see in the room?"
- **Your Response:** "You see a large, dusty room with a wooden table in the center. On the table, you notice an old <span class='keyword'>book</span> and a single <span class='name'>silver key</span>."
</EXAMPLE>

<CONTEXT_DATA>
{context_with_active_char}
</CONTEXT_DATA>

<PLAYER_WHO_IS_ASKING>
{character.name}
</PLAYER_WHO_IS_ASKING>

<PLAYER_QUESTION>
"{question}"
</PLAYER_QUESTION>
"""
        reply = self.classifier.general_text_llm_request(prompt)
        self.context += f"<player asked the DM>{character.name} asks DM: {question}\nDM's response: {reply}</player asked the DM>\n"
        self.log_event("dm_reply", character_name=character.name, reply=reply)
        yield EventBuilder.DM_message(reply)

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
6.  **Намерение DM:** Если в тексте есть намеки на будущие события или секреты от Ма��тера, сохрани их.

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
            return self.askedDM(character, interaction), False
        decision: ClassifyInformationOrActionRequest = self.classifier.generate(
    contents=f"""
<ROLE>
You are an intelligent request router for a D&D game. Your task is to analyze a player's request and classify it into one of two categories: an in-game character action OR a meta-question to the Dungeon Master.
</ROLE>

<TASK_DEFINITION>
Analyze the player's request provided below. Your goal is to determine if the player is speaking **AS THEIR CHARACTER** to perform an action in the game world, or if the player is speaking **AS A PLAYER** to the Dungeon Master (DM) to ask a question or clarify rules.

To make the right choice, ask yourself this key question: **"Is this something the character DOES, or something the player ASKS?"**
</TASK_DEFINITION>

<CATEGORY_DEFINITIONS>
You must classify the request into one of these two categories, which correspond to a boolean value in the `decision` field.

**1. Действие Персонажа (Character Action) -> `decision: false`**
   - This is when the player describes what their character is doing, attempting, or saying *within the game world*.
   - These are commands for the character to interact with the environment, other characters, or items.
   - **Keywords:** "Я атакую", "Я иду", "Я пытаюсь взломать", "Я говорю ему", "Я использую зелье".
   - **IMPORTANT:** Actions that gather information *through a character's senses or skills* are still ACTIONS. For example, "Я осматриваю комнату" or "Я пытаюсь понять, лжет ли он" are actions that would require a Perception or Insight check. They are NOT questions to the DM.

**2. Запрос к Мастеру (Query to the DM) -> `decision: true`**
   - This is when the player asks a question directly to the Dungeon Master about the world, rules, or their character's state. It is a meta-request for information, not an in-world action.
   - **Keywords:** "Что я вижу?", "Могу ли я...?", "Расскажи подробнее о...", "Какие у меня есть предметы?", "Что произойдет, если...?", "OOC (Out of Character)".
   - This category is for clarifying information that the player needs to decide on an action.

</CATEGORY_DEFINITIONS>

<EXAMPLES>
- Запрос: "Я атакую гоблина своим длинным мечом." -> `decision: false` (Пояснение: Четкое действие персонажа).
- Запрос: "Расскажи мне, как выглядит этот гоблин?" -> `decision: true` (Пояснение: Запрос информации к Мастеру).
- Запрос: "Я внимательно осматриваюсь в поисках ловушек." -> `decision: false` (Пояснение: Это действие, требующее проверки навыка Внимания, а не просто вопрос).
- Запрос: "Могу ли я допрыгнуть до того уступа?" -> `decision: true` (Пояснение: Вопрос к Мастеру о правилах и возможностях, предшествующий действию).
- Запрос: "Я хочу убедить стражника пропустить меня." -> `decision: false` (Пояснение: Заявка на социальное действие, требующее проверки Харизмы).
- Запрос: "OOC: мне нужно отойти на пару минут." -> `decision: true` (Пояснение: Мета-комментарий, не относящийся к игровому миру).
</EXAMPLES>

<PLAYER_REQUEST_TO_CLASSIFY>
{interaction}
</PLAYER_REQUEST_TO_CLASSIFY>

<OUTPUT_INSTRUCTIONS>
Provide your response as a single JSON object matching the `ClassifyInformationOrActionRequest` model, with no other text.
</OUTPUT_INSTRUCTIONS>
""",
    pydantic_model=ClassifyInformationOrActionRequest
)  # type: ignore
        if decision.decision: # type: ignore
            print(f"{INFO_COLOR}Request for info {Colors.RESET}")
            return self.askedDM(character, interaction), False
        else:
            print(f"{INFO_COLOR}Request for action {Colors.RESET}")
            return self.action(character, interaction), True
    
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
    
    
    async def after_action(self, outcome:ActionOutcome):
        print("after action processing")
        prompt = self.prompter.get_turn_analysis_prompt(self, self.game_mode)
        analisys : TurnAnalysisOutcome = self.generator.generate(
            pydantic_model=TurnAnalysisOutcome,
            prompt=prompt,
            language="Russian"
        )
        print(f"\n{HEADER_COLOR} Analyzing turn outcome...{Colors.RESET}")
        print(analisys)
        if self.game_mode != analisys.recommended_mode:
            self.game_mode = analisys.recommended_mode
            yield EventBuilder.alert(f'Game mode changed to <span class="keyword">{self.game_mode.name}</span>')
        yield EventBuilder.end_of_turn()
    
    async def after_turn(self):
        print(f"\n{INFO_COLOR} Processing after-turn effects...{Colors.YELLOW} {len(self.context)} chars of context {Colors.RESET}") # type: ignore
        if self.game_mode == GameMode.NARRATIVE:
            async for event in self.after_narrative(): # type: ignore
                yield event
        if len(self.context) > MAX_CONTEXT_LENGTH_CHARS:  # type: ignore
            self.trim_context()
            if self.context: 
                print(f"{SUCCESS_COLOR} Context updated{Colors.RESET}")

    async def after_narrative(self):
        analisys : NarrativeTurnAnalysis = self.generator.generate(
            pydantic_model=NarrativeTurnAnalysis,
            prompt=self.prompter.get_narrative_analysis_prompt(self)
        )
        print(f"\n{HEADER_COLOR} Analyzing narrative turn outcome...{Colors.RESET}")
        print(f"{DEBUG_COLOR}Raw analysis: {analisys}{Colors.RESET}")
        
        for i, change in enumerate(analisys.proactive_world_changes, 1):
            try:
                if not isinstance(change.change_type, ProactiveChangeType):
                    print(f"{WARNING_COLOR}Skipping invalid change type: {change.change_type}{Colors.RESET}")
                    continue

                payload = change.payload
                match change.change_type:
                    case ProactiveChangeType.ADD_OBJECT | ProactiveChangeType.UPDATE_OBJECT | ProactiveChangeType.REMOVE_OBJECT | ProactiveChangeType.UPDATE_SCENE:
                        try:
                            if payload.object_type == "character": # type: ignore
                                await self.update_character(payload.object_name, payload.changes) # type: ignore
                            elif payload.object_type == "scene": # type: ignore
                                await self.update_scene(payload.object_name, payload.changes) # type: ignore
                            yield EventBuilder.alert(f"(narrative){payload.object_name}: {payload.changes}") # type: ignore
                        except Exception as e:
                            yield EventBuilder.error(f"Error processing object change for '{getattr(payload, 'object_name', 'N/A')}': {e}")
                            print(f"{ERROR_COLOR}Error in object change: {e}{Colors.RESET}")

                    case ProactiveChangeType.ADD_CHARACTER:
                        try:
                            new_character : Character = self.generate_character(change.description, self.context)
                            self.add_character(new_character)
                            yield EventBuilder.alert(f"(narrative) A new character, {new_character.name}, appears: {change.description}")
                        except Exception as e:
                            yield EventBuilder.error(f"Error adding character: {e}")
                            print(f"{ERROR_COLOR}Error in ADD_CHARACTER: {e}{Colors.RESET}")

                    case ProactiveChangeType.REMOVE_CHARACTER:
                        try:
                            if not isinstance(payload, str):
                                raise TypeError(f"REMOVE_CHARACTER payload must be a string, but got {type(payload)}")
                            char = self.get_character_by_name(payload)
                            self.characters.remove(char)
                            yield EventBuilder.alert(f"(narrative){payload} was removed: {change.description}")
                        except Exception as e:
                            yield EventBuilder.error(f"Error removing character '{payload}': {e}")
                            print(f"{ERROR_COLOR}Error in REMOVE_CHARACTER: {e}{Colors.RESET}")

                    case ProactiveChangeType.UPDATE_CHARACTER:
                        try:
                            if not hasattr(payload, 'object_name'):
                                raise TypeError(f"UPDATE_CHARACTER payload is not a valid ChangesToMake object: {payload}")
                            await self.update_character(payload.object_name, payload.changes) # type: ignore
                            yield EventBuilder.alert(f"(narrative){payload.object_name} was updated: {change.description}") # type: ignore
                        except Exception as e:
                            yield EventBuilder.error(f"Error updating character '{getattr(payload, 'object_name', 'N/A')}': {e}")
                            print(f"{ERROR_COLOR}Error in UPDATE_CHARACTER: {e}{Colors.RESET}")

                    case ProactiveChangeType.CHANGE_SCENE:
                        try:
                            if not isinstance(payload, NextScene):
                                raise TypeError(f"CHANGE_SCENE payload must be a NextScene object, but got {type(payload)}")
                            self.generate_scene(payload)
                            # yield EventBuilder.scene_change(change.description)
                        except Exception as e:
                            yield EventBuilder.error(f"Error changing scene: {e}")
                            print(f"{ERROR_COLOR}Error in CHANGE_SCENE: {e}{Colors.RESET}")
                            
                    case _:
                        print(f"{WARNING_COLOR}Unhandled proactive change type: {change.change_type}{Colors.RESET}")

            except Exception as e:
                yield EventBuilder.error(f"Outer error in after_narrative loop for change '{change.change_type}': {e}")
                print(f"{ERROR_COLOR}Critical error processing change '{change.change_type}': {e}{Colors.RESET}")
                # Continue to the next change to avoid a single failure stopping all subsequent changes.
                continue
        self.story_manager.check_and_advance(self.context)

    async def NPC_turn(self):
        """
        Handles the npc's turn in the fight.
        """
        active_char = self.get_active_character()
        print(f"\n{HEADER_COLOR}NPC's turn: {active_char.name}{Colors.RESET}")
        
        context_with_active_char = self.get_actual_context(active_character_name=active_char.name)
        
        NPC_action_prompt = f"""
<ROLE>
Ты — искусственный интеллект, управляющий неигровым персонажем (NPC) в бою.
Твоя задача — выбрать наиболее логичное и эффективное действие для этого NPC на его ходу.
</ROLE>

<CHARACTER_PROFILE>
{active_char.model_dump_json(indent=2)}
</CHARACTER_PROFILE>

<SITUATION_CONTEXT>
{context_with_active_char}
</SITUATION_CONTEXT>

<TASK>
Проанализируй личность персонажа, его цели и текущую боевую обстановку. Выбери его следующее действие.
Твой ответ должен быть **короткой фразой, описывающей действие**, как буд��о ее говорит игрок.
Не пиши полную историю, только само действие.

Примеры хороших ответов:
- "Атакую Бориса Бритву своим ледяным копьем."
- "Использую способность 'Ледяная стена', чтобы разделить группу."
- "Пытаюсь отступить в тень, чтобы подготовить засаду."

Твой ответ:
"""
        NPC_action = self.classifier.general_text_llm_request(NPC_action_prompt)
        async for value in self.action(self.get_active_character(), NPC_action, is_NPC=True):
            yield value
        