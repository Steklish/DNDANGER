import json
from math import e
import random
from dotenv import load_dotenv
from classifier import Classifier
from generator import ObjectGenerator
from models import *
from prompter import Prompter
from server_communication.events import EventBuilder
from utils import *
from global_defines import *
import global_defines
from models import *



class ChapterLogicFight:
    """Fight logic for a chapter in a game, handling character interactions and actions."""

    
    def __init__(self, context: str, characters: List[Character] = [], language: str = "Russian"):
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
    
    def update_scene(self, scene_name: str, changes_to_make: str):
        """
        Updates the current scene with the provided changes.
        
        :param scene_name: The name of the scene to update.
        :param changes_to_make: A string describing the changes to apply.
        """
        print(f"\n{ENTITY_COLOR}{scene_name}{Colors.RESET} {INFO_COLOR}updates attributes with:{Colors.RESET} {changes_to_make}")
        try:
            self.scene = self.generator.generate(
                pydantic_model=Scene,
                prompt=f"""
                Make following changes to the scene:
                {str(self.scene)}
                Changes to make: {changes_to_make}
                """,
                language=self.language
            )
            print(f"{SUCCESS_COLOR}✨ Scene updated successfully!{Colors.RESET}")
        except Exception as e:
            print(f"{ERROR_COLOR}❌ Error updating scene: {e}{Colors.RESET}")
            return
    
    # Assuming your Character class and other imports are defined elsewhere
# from your_models_file import Character, Item, Ability
# from your_colors_file import ENTITY_COLOR, INFO_COLOR, SUCCESS_COLOR, ERROR_COLOR, Colors
# from your_utils_file import find_closest_match

    def update_character(self, character_name: str, changes_to_make: str):
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
            if not target_char_name:
                print(f"{ERROR_COLOR}❌ Error: Character '{character_name}' not found.{Colors.RESET}")
                return
                
            character = char_dict[target_char_name]

            # Convert the current character object to a JSON string for clean input to the LLM
            character_json = character.model_dump_json(indent=2)

            # --- ENHANCED PROMPT ---
            # This new prompt is highly structured and provides explicit rules to the LLM.
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
            # --- END OF ENHANCED PROMPT ---

            # The old character object is removed before generating the new one
            if character:
                self.characters.remove(character) 
            
            updated_character = self.generator.generate(
                pydantic_model=Character,
                prompt=prompt,
                language=self.language
            )

            if not updated_character:
                # If the LLM fails, re-add the original character to avoid data loss
                self.characters.append(character)
                raise ValueError("LLM failed to return a valid updated character object.")

            self.characters.append(updated_character)
            print(f"{SUCCESS_COLOR}✨ Character '{updated_character.name}' updated successfully!{Colors.RESET}")
            
            # Add a clear message if the character's life status changed
            if not updated_character.is_alive and character.is_alive:
                print(f"{ERROR_COLOR}💀 Character {updated_character.name} has died!{Colors.RESET}")

        except Exception as e:
            print(f"{ERROR_COLOR}❌ Error updating character: {e}{Colors.RESET}")
            # Optionally re-add the original character on any failure
            if 'character' in locals() and character not in self.characters: # type: ignore
                self.characters.append(character) # type: ignore
            yield EventBuilder.error(f"Error updating character {character_name}: {e}")
        

    def setup_fight(self):
        """
        Initializes the fight by generating objects and their actions based on the context.
        """
        self.game_mode = GameMode.NARRATIVE
        print(f"\n{HEADER_COLOR}🎲 Generating Scene...{Colors.RESET}")
        
        # scene context is the same one as the chapter context (context at creating the chapter)
        scene_d = self.classifier.generate(
            f"Generate a scene description and difficulty based on the context: {self.context}",
            NextScene
        )
            
        self.scene = self.generator.generate(
            pydantic_model=Scene,
            prompt=str(scene_d),
            context=self.context,
            language=self.language
        )

        print(f"\n{SUCCESS_COLOR}✨ Generated Scene:{Colors.RESET} {ENTITY_COLOR}{self.scene.name}{Colors.RESET}")
        print(f"{INFO_COLOR}📜 Description:{Colors.RESET} {self.scene.description}")


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
            {self.get_actual_context()}
        """
        )
        
        self.turn_order = [char.name for char in self.characters]
        random.shuffle(self.turn_order)
        print(f"{INFO_COLOR}Turn order shuffled{Colors.RESET}")
        
        
    def move_to_next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.turn_order) # type: ignore

    def get_active_character_name(self) -> str:
        return self.turn_order[self.current_turn] # type: ignore

    def get_active_character(self) -> Character: # type: ignore
        for character in self.characters:
            if character.name == self.get_active_character_name():
                return character

    def get_actual_context(self) -> str:
        context_dict = {
            "world_state": {
                "summary_of_past_events": self.context,
                "current_scene": self.scene.model_dump() if self.scene else None,
            },
            "participants": {
                "all_characters": [char.model_dump() for char in self.characters]
            }
        }

        data =  f"""
    <CONTEXT_DATA>
    {json.dumps(context_dict, indent=2, ensure_ascii=False)}
    </CONTEXT_DATA>
    """
        # print(data)
        return data






    def action(self, character: Character, action_text: str, is_NPC = False):
        """
        Executes an action and immediately gets both the narrative and the structured changes.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}performs action:{Colors.RESET} {action_text}")

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

        # The rest of the logic
        self.context += f"\n\n{character.name} tries to perform action {action_text}\n" # type: ignore
        yield EventBuilder.DM_message(narrative) # type: ignore

        if is_NPC: outcome.is_legal = True
        
        if outcome.is_legal:
            for i, change in enumerate(changes, 1):
                self.context += f"<Action outcomes>"
                self.context += f"\n{i}. {change.object_name} -> ({change.changes})"
                if change.object_type == "character":
                    self.update_character(change.object_name, change.changes)
                elif change.object_type == "scene":
                    self.update_scene(change.object_name, change.changes)
                    
                yield EventBuilder.state_update_required(
                    update=f"{change.object_name} был обновлен ({change.changes})",
                    total=len(changes), 
                    current=i
                )
                yield EventBuilder.alert(f"{change.object_name}: {change.changes}")
            print(f"{SUCCESS_COLOR}All changes applied successfully{Colors.RESET}")    
            self.move_to_next_turn()
            self.context += f"</Action outcomes>"
            yield from self.after_action(outcome)
        else:
            self.context += f"\nNothinig happens...\n"
            yield EventBuilder.alert("Impossible to act...")
        
    def askedDM(self, character: Character, question: str):
        """
        Handles a character asking the DM a question.
        
        :param character: The character asking the question.
        :param question: The question being asked.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}asks:{Colors.RESET} {question}")
        prompt = f"""
        {global_defines.dungeon_master_core_prompt}
        [current task]
        Ответь на запрос игрока, выделяя ключевые слова тегом <span class='keyword'>ключевые слова</span> и выделяя имена тегом <span class='name'>имена</span>. Сейчас ты только отвечаешь игроку, и, значит, твой ответ не должен влиятьь на мир или персонажей. 
        [Контекст]
        {self.get_actual_context()}
        [Запрос] 
        "{question}"
        """
        reply = self.classifier.general_text_llm_request(prompt)
        self.context =  str(self.context) + f"<Chracter's interaction>{character.name} asks DM: {question}</Chracter's interaction>"
        self.context += f"<DM's response>\n{reply}</DM's response>\n"
        yield EventBuilder.DM_message(reply) # type: ignore
        # return reply

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
Создай новую сводку (не более {MAX_CONTEXT_LENGTH} слов), которая сохраняет только самую важную информацию для предстоящей сцены. Обязательно включи в нее:
1.  **Основная цель:** Какова главная цель группы авантюристов в данный момент?
2.  **Основная цель врагов:** Какова главная цель их противников?
3.  **Ключевые отношения:** Какие союзы или конфликты существуют между персонажами?
4.  **Важные детали прошлого:** Упомяни 1-2 самых важных события из прошлого, которые напрямую влияют на текущую мотивацию персонажей.
5.  **Намерение DM:** Если в тексте есть намеки на будущие события или секреты от Мастера, сохрани их.

Не включай в сводку нерелевантные детали или описания уже прошедших действий, если они не влияют на будущее.
</TASK>
"""
        )
        print(f"{Colors.GREEN}context after{self.context} {Colors.RESET}")
        

    def process_interaction(self, character: Character, interaction: str):
        """
        Processes a character's interaction, deciding the outcome of actions and questions.
        """
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
            yield EventBuilder.user_intent_processed("info")
            print(f"{INFO_COLOR}Request for info {Colors.RESET}")
            yield from self.askedDM(character, interaction)
        else:
            yield EventBuilder.user_intent_processed("action")
            print(f"{INFO_COLOR}Request for action {Colors.RESET}")
            yield from self.action(character, interaction)
        self.after_turn()
    
    def get_character_by_name(self, name:str) -> Character:
        for char in self.characters:
            if  char.name == name:
                return char
        return self.characters[0]
    
    def after_action(self, outcome:ActionOutcome):
        print("after action processing")
        prompt = self.prompter.get_turn_analysis_prompt(self, self.game_mode)
        analisys : TurnAnalysisOutcome = self.generator.generate(
            pydantic_model=TurnAnalysisOutcome,
            prompt=prompt,
            language="Russian"
        )
        print(f"\n{HEADER_COLOR}📝 Analyzing turn outcome...{Colors.RESET}")
        # print(f"{DEBUG_COLOR}Raw prompt: {prompt}{Colors.RESET}")
        print(analisys)
        if self.game_mode != analisys.recommended_mode:
            self.game_mode = analisys.recommended_mode
            yield EventBuilder.alert(f'Game mode changed to <span class="keyword">{self.game_mode.name}</span>')
        
    
    def after_turn(self):
        print(f"\n{INFO_COLOR}📝 Processing after-turn effects...{Colors.YELLOW} {len(self.context)} chars of context {Colors.RESET}") # type: ignore
        if len(self.context) > MAX_CONTEXT_LENGTH_CHARS:  # type: ignore
            self.trim_context()
            if self.context: 
                print(f"{SUCCESS_COLOR}✨ Context updated{Colors.RESET}")
        if self.game_mode == GameMode.NARRATIVE:
            self.after_narrative()
        
    def after_narrative(self):
        analisys : NarrativeTurnAnalysis = self.generator.generate(
            pydantic_model=NarrativeTurnAnalysis,
            prompt=self.prompter.get_narrative_analysis_prompt(self)
        )
        print(f"\n{HEADER_COLOR}📝 Analyzing narrative turn outcome...{Colors.RESET}")
        print(f"{DEBUG_COLOR}Raw analysis: {analisys}{Colors.RESET}")
        try:
            for change in analisys.proactive_world_changes:
                if change.change_type == ProactiveChangeType.ADD_OBJECT or \
                    change.change_type == ProactiveChangeType.REMOVE_OBJECT or \
                        change.change_type == ProactiveChangeType.UPDATE_OBJECT:
                            if change.payload.object_type == "character": # type: ignore
                                self.update_character(change.payload.object_name, change.payload.changes) # type: ignore
                            elif change.object_type == "scene": # type: ignore
                                self.update_scene(change.payload.object_name, change.payload.changes) # type: ignore
        except Exception as e:
            yield EventBuilder.error(f"Error occurred during narrative turn analysis: {e}")
            print(f"{ERROR_COLOR}Error occurred during narrative turn analysis: {e}{Colors.RESET}")

    def NPC_turn(self):
        """
        Handles the npc's turn in the fight.
        """
        print(f"\n{HEADER_COLOR}NPC's turn:{Colors.RESET}")
        # Here you can implement enemy actions, AI logic, etc.
        # For now, we will just simulate an enemy action
        NPC_action_prompt = f"""
<ROLE>
Ты — искусственный интеллект, управляющий неигровым персонажем (NPC) в бою.
Твоя задача — выбрать наиболее логичное и эффективное действие для этого NPC на его ходу.
</ROLE>

<CHARACTER_PROFILE>
{self.get_active_character().model_dump_json(indent=2)}
</CHARACTER_PROFILE>

<SITUATION_CONTEXT>
{self.get_actual_context()}
</SITUATION_CONTEXT>

<TASK>
Проанализируй личность персонажа, его цели и текущую боевую обстановку. Выбери его следующее действие.
Твой ответ должен быть **короткой фразой, описывающей действие**, как будто ее говорит игрок.
Не пиши полную историю, только само действие.

Примеры хороших ответов:
- "Атакую Бориса Бритву своим ледяным копьем."
- "Использую способность 'Ледяная стена', чтобы разделить группу."
- "Пытаюсь отступить в тень, чтобы подготовить засаду."

Твой ответ:
"""
        NPC_action = self.classifier.general_text_llm_request(NPC_action_prompt)
        yield from self.action(self.get_active_character(), NPC_action) # type: ignore
        self.after_turn()
        
if __name__ == "__main__":
    load_dotenv()

    # character damage test
    # print(f"{HEADER_COLOR}🎮 Starting new chapter...{Colors.RESET}")
    # chapter = ChapterLogicFight(context = "the journey begins...")
    # chapter.setup_fight()
    # r_ch = chapter.generator.generate(Character, "random character with full hp and no items in inventory", "no context", "Russian")
    # print(r_ch.model_dump_json(indent=2))
    # chapter.characters.append(r_ch)
    # chapter.update_character(r_ch.name, "получил 10 урона и потерял глаз")
    # print(chapter.characters[0].model_dump_json(indent=2))
    
    # scene change test
    # print(f"{HEADER_COLOR}🎮 Starting new chapter...{Colors.RESET}")
    # chapter = ChapterLogicFight(context = "the journey begins...")
    # chapter.setup_fight()
    # r_ch = chapter.generator.generate(Character, "random character with full hp and no items in inventory", "no context", "Russian")
    # print(r_ch.model_dump_json(indent=2))
    # chapter.characters.append(r_ch)
    # hhh = input("enter a question to a DM...    ")
    # print(chapter.process_interaction(chapter.characters[0], hhh)) # type: ignore
    
    
    # enemy turn test
    generator = ObjectGenerator()
    context = "A ground beneeth the grand tree"
    print(f"{HEADER_COLOR}🎮 Starting new chapter (enemy turn test)...{Colors.RESET}")
    chapter = ChapterLogicFight(
        context = context,
        characters = [
            generator.generate(Character, "Борис Бритва with full hp (50 hp) and a single dager (player character)", context, "Russian"),
            generator.generate(Character, "random monster with full hp (50 hp) and some magic spells (enemy NPC)", context, "Russian")
        ]
    )
    chapter.setup_fight()
    def print_game_sate():
        for c in chapter.characters:
            print(c.model_dump_json(indent=2))
        print(chapter.scene.model_dump_json(indent=2)) # type: ignore
        print(chapter.turn_order)
    while True:
        if chapter.get_active_character().is_player:
            user_input = input(f"{ENTITY_COLOR}{chapter.get_active_character_name()} -->{Colors.RESET}  ")
            if user_input == "?": 
                print_game_sate()
                continue
            chapter.process_interaction(chapter.get_active_character(), user_input) # type: ignore
        else:
            dm_action = chapter.NPC_turn()