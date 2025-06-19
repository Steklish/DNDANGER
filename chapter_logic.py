import json
import random
from dotenv import load_dotenv
from classifier import Classifier
from generator import ObjectGenerator
from models import *
from server_communication.events import EventBuilder
from utils import *
from global_defines import (
    Colors, 
    ERROR_COLOR, 
    HEADER_COLOR,
    ENTITY_COLOR,
    SUCCESS_COLOR,
    INFO_COLOR,
    MAX_CONTEXT_LENGTH
)
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
    
    def update_character(self, character_name: str, changes_to_make: str):
        """
        Updates a character's attributes based on the provided changes.
        
        :param character_name: The name of the character to update.
        :param changes_to_make: A string describing the changes to apply.
        """
        print(f"\n{ENTITY_COLOR}{character_name}{Colors.RESET} {INFO_COLOR}updates attributes with:{Colors.RESET} {changes_to_make}")
        try:        
            char_name_list = [char.name for char in self.characters]
            
            char_dict = {char.name: char for char in self.characters}
            
            character = char_dict.get(find_closest_match(character_name, char_name_list))

            if character:
                self.characters.remove(character) # type: ignore
            character = self.generator.generate(
                pydantic_model=Character,
                prompt=f"""
                Make following changes to the character:
                {str(character)}
                Changes to make: {changes_to_make}
                
                IMPORTANT: every change has to be reflected in character. If it is a significant modification it can be reflected in character's personality.
                """,
                language=self.language
            )
            self.characters.append(character) # type: ignore
            print(f"{SUCCESS_COLOR}✨ Character updated successfully!{Colors.RESET}")
        except Exception as e:
            print(f"{ERROR_COLOR}❌ Error updating character: {e}{Colors.RESET}")
            return
        

    def setup_fight(self):
        """
        Initializes the fight by generating objects and their actions based on the context.
        """
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
            Try to extract Dungeon Master's intent on the current scene and the context.
            Store which characters are allied with which ones and what can change this alliance. Store their motivations and goals.
            If some info is missing you are allowed to create it. 
            Dont ask additional information.
            in no context provided at all come up with something like "evry memory have faded away and the past seems very blury". 
            Dont generate additional text, only story extract for the current scene.
            Current context:
            {self.context}
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
       
    def get_action_prompt(self, character: Character, action_text: str) -> str:
        return f"""
<ROLE>
{global_defines.dungeon_master_core_prompt} Твоя задача — симулировать исход действия персонажа и вернуть результат в виде СТРОГОГО JSON-объекта.
</ROLE>

<RULES>
1.  **Оценивай логику:** Учитывай силу персонажа, его оружие, броню цели, окружение и любые состояния (например, <span class="condition">ослеплен</span>). Мощный удар топора должен наносить больше урона, чем укол кинжалом. Попасть в бронированного рыцаря сложнее, чем в гоблина.
2.  **Будь беспристрастен:** Не подсуживай ни игрокам, ни врагам. Исход должен быть логичным следствием действия в мире игры. Следи за тем, чтобы действия, которое совершает персонаж было ему позволено с точки зрения правил и логики (например, персонаж не может ударить мечом, если у него нет меча или он спрятан глубуко в сумке). Если игрок пытается совершить действие, которое недопустимо, дйствия не должно иметь эффекта.
3.  **Определяй механику:** Одновременно с созданием описания, ты должен точно определить механические изменения. Если персонаж получает урон, укажи это в `structural_changes`. Если он поджигает стол, это изменение и для персонажа (потратил факел), и для сцены (появился горящий стол) никогда не забывай добавить описание изменения.
</RULES>

<OUTPUT_FORMAT>
Твой ответ ДОЛЖЕН быть JSON-объектом, соответствующим Pydantic-модели `ActionOutcome`.
-   `narrative_description`: Красочное описание для игрока. **ОБЯЗАТЕЛЬНО** используй эти HTML-теги:
    -   `<span class="name">Имя</span>` для имен и названий.
    -   `<span class="damage">описание урона</span>` для любого вреда.
    -   `<span class="heal">описание исцеления</span>` для восстановления здоровья.
    -   `<span class="condition">описание состояния</span>` для наложения эффектов.
-   `structural_changes`: Список объектов, описывающих конкретные изменения (если изменения отсутствуют - оставить пустым).
-   `is_legal` : Является ли действие игрока допустимым с точки зрения правил.
</OUTPUT_FORMAT>

<CONTEXT>
{self.get_actual_context()}
</CONTEXT>

<TASK>
Персонаж <span class="name">{character.name}</span> совершает следующее действие: "{action_text}"

Сгенерируй JSON-объект `ActionOutcome`, описывающий результат.
</TASK>
"""

    # Inside ChapterLogicFight class

    def action(self, character: Character, action_text: str):
        """
        Executes an action and immediately gets both the narrative and the structured changes.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}performs action:{Colors.RESET} {action_text}")

        # Use a generator that can directly output a Pydantic object
        # лол
        # это вообще не та функция, которую я сюда планировал
        outcome: ActionOutcome = self.generator.generate(
            pydantic_model=ActionOutcome,
            prompt=self.get_action_prompt(character, action_text),
            language=self.language
        )

        narrative = outcome.narrative_description
        changes = outcome.structural_changes

        # The rest of the logic
        self.context += f"\n\n{character.name} performs action (DM's response): {narrative}" # type: ignore
        yield EventBuilder.DM_message(narrative) # type: ignore

        if outcome.is_legal:
            for i, change in enumerate(changes, 1):
                if change.object_type == "character":
                    self.update_character(change.object_name, change.changes)
                elif change.object_type == "scene":
                    self.update_scene(change.object_name, change.changes)
                    
                yield EventBuilder.state_update_required(
                    update=f"{change.object_name} был обновлен ({change.changes})",
                    total=len(changes), 
                    current=i
                )
            print(f"{SUCCESS_COLOR}All changes applied successfully{Colors.RESET}")    
            self.move_to_next_turn()
        else:
            yield EventBuilder.alert("Not a legal action reqired")
    
    def apply_changes_after_turn(self, action_description : str, character : Character):
        """
        Applies changes after action was preformed.
        """
        changes : list[ChangesToMake] = self.classifier.generate_list(
            contents=f"""
            Action by character: {character.name}
            
            Outcome description:
            {action_description}
            
            
            Important: if for example a character took their sword and left it in the middle of the road it should be a change for the charactera and a cahnge for the scene as well.
            Example: if a character lightens up a bonfire you shoud come up with something like "LIght up a bonfire" - where object type is scene.
            """,
            pydantic_model=ChangesToMake
        ) # type: ignore

        for change in changes: # type: ignore
            # Apply each change to the character/scene
            if change.object_type == "character":
                self.update_character(
                    character_name=change.object_name,
                    changes_to_make=change.changes
                    )
            elif change.object_type == "scene":
                self.update_scene(change.object_name, change.changes) # type: ignore
        print("ALl the changes applied successfully")
        
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
        self.context =  str(self.context) + f"\n\nPlayer that controlls {character.name} asks: {question}"
        self.context += f"\n\nDM's response: {reply}"
        print(f"{SUCCESS_COLOR}🎲 DM's response:{Colors.RESET} {reply}")
        yield EventBuilder.DM_message(reply) # type: ignore
        # return reply

    def trim_context(self):
        self.context = self.classifier.general_text_llm_request(
            f"""
<ROLE>
Ты — ассистент Мастера Игры. Твоя задача — сжать длинную историю в краткую, но информативную сводку для следующей сцены.
</ROLE>

<FULL_CONTEXT>
{self.context}
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
        

    def process_interaction(self, character: Character, interaction: str):
        """
        Processes a character's interaction, deciding the outcome of actions and questions.
        """
        decision : ClassifyInformationOrActionRequest = self.classifier.generate(
            contents=f"""
            You need to classify players dnd request to DM (master). 
            В `decision` TRUE, если запрос содержит информацию или взаимодействие с мастером подземелья, FALSE, если запрос содержит описание действия от лица персонажа в D&D.
            player's request:
            {interaction}
            """, 
            pydantic_model=ClassifyInformationOrActionRequest
        )  # type: ignore
        interaction += "\n\n"
        interaction += decision.reasoning # type: ignore
        result = None
        if decision.decision: # type: ignore
            yield EventBuilder.user_intent_processed("info")
            print(f"{INFO_COLOR}Request for info {Colors.RESET}")
            yield from self.askedDM(character, interaction)
        else:
            yield EventBuilder.user_intent_processed("action")
            print(f"{INFO_COLOR}Request for action {Colors.RESET}")
            yield from self.action(character, interaction)
    
    def get_character_by_name(self, name:str) -> Character:
        for char in self.characters:
            if  char.name == name:
                return char
        return self.characters[0]
    
    def after_turn(self):
        """
        Actions to perform after each player's turn.
        """
        print(f"\n{INFO_COLOR}📝 Processing after-turn effects...{Colors.RESET}")
        updated_context = self.classifier.general_text_llm_request(
            f"""Update the context based on the latest actions and events in the fight. Remove unimportant detailes and restore important story details 
            Current context:
            {self.context} 
            Context from the last scene:
            {self.last_scene}
            """
        )
        if updated_context: 
            self.context = updated_context
            print(f"{SUCCESS_COLOR}✨ Context updated{Colors.RESET}")

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