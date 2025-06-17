import random
from dotenv import load_dotenv
from numpy import character
from pyparsing import Char
from sympy import true
from classifier import Classifier
from generator import ObjectGenerator
from models import *
from utils import *
from global_defines import (
    Colors, 
    ERROR_COLOR, 
    WARNING_COLOR, 
    HEADER_COLOR,
    ENTITY_COLOR,
    SUCCESS_COLOR,
    TIME_COLOR,
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
        
        print(f"\n{HEADER_COLOR}Current Scene:{Colors.RESET}")
        print(f"{INFO_COLOR}{str(self.scene)}{Colors.RESET}")
        print(f"\n{HEADER_COLOR}Current Context:{Colors.RESET}")
        print(f"{INFO_COLOR}{str(self.context)}{Colors.RESET}")
        
    def move_to_next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.turn_order) # type: ignore

    def get_active_character_name(self) -> str:
        return self.turn_order[self.current_turn] # type: ignore

    def get_active_character(self) -> Character: # type: ignore
        for character in self.characters:
            if character.name == self.get_active_character_name():
                return character

    def get_actual_context(self) -> str:
        return f"""
    <story and situation>
    {self.context}
    <characters>
    {str(self.characters)}
    <scene>
    {str(self.scene)}
    """

    def action(self, character: Character, action: str):
        """
        Executes an action for a character in the fight.
        
        :param character: The character performing the action.
        :param action: The action to be performed.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}performs action:{Colors.RESET} {action}")
        prompt = f"""
        {global_defines.dungeon_master_core_prompt}
        
        Твоя главная задача — определять и красочно описывать исход действий, заявленных игроком. Ты должен быть беспристрастным симулятором правил и одновременно творческим рассказчиком, который делает мир живым.
        
        Прежде чем писать ответ, ты должен внутренне симулировать исход действия, основываясь на логике правил D&D. Хотя у тебя нет реальных "листов персонажей", ты должен действовать так, как будто они есть.

        *   **Оценивай Источник Действия:**
            *   **Оружие/Заклинание:** Двуручный топор наносит больше урона, чем кинжал. Огненный шар поражает область, а не одну цель.
            *   **Предполагаемые Характеристики:** Персонаж-воин, вероятно, силен и хорошо владеет мечом. Персонаж-маг, скорее всего, слаб в рукопашном бою, но силен в магии.

        *   **Оценивай Цель:**
            *   **Броня и Защита:** Попасть по рыцарю в полных латах сложнее, чем по гоблину в лохмотьях. Урон по бронированной цели должен быть ниже.
            *   **Уязвимости/Сопротивления:** Демон может иметь сопротивление к огню (получает меньше урона), а ледяной элементаль будет уязвим к нему (получает больше урона).

        *   **Учитывай Окружение:**
            *   **Преимущество/Помеха:** Атака из укрытия или по <span class="condition">ослепленному</span> врагу должна быть успешнее. Бой в темноте или на скользкой поверхности — менее успешным.
        *   **Учитывай Состояние Персонажа:**
        
        При создании описания исхода **обязательно** используй следующие HTML-теги для выделения ключевых элементов повествования.

        *   `<strong><span class="name">Имя</span></strong>`: Используй для всех имен собственных: персонажей, монстров, божеств, названий мест (города, таверны) и т.д.
            *   *Пример:* `<span class="name">Горк</span>`, `<span class="name">Элара</span>`, `<span class="name">Вотердип</span>`.

        *   `<strong><span class="damage">текст урона</span></strong>`: Используй для **любого** описания получения вреда, боли или потери жизненных сил.
            *   *Пример:* Меч орка <span class="damage">глубоко вонзается тебе в плечо</span>. Ты чувствуешь, как <span class="damage">огненный шар опаляет твою кожу</span>.

        *   `<strong><span class="heal">текст исцеления</span></strong>`: Используй для **любого** описания восстановления здоровья, заживления ран или магического исцеления.
            *   *Пример:* Теплое сияние <span class="heal">разливается по твоему телу, затягивая рану</span>. Глоток зелья <span class="heal">придает тебе новых сил</span>.

        *   `<strong><span class="condition">текст состояния</span></strong>`: Используй для описания наложения или получения специальных эффектов и состояний.
            *   *Пример:* От яда паука твои ноги <span class="condition">становятся ватными</span>. Ужасающий рык вгоняет тебя в <span class="condition">состояние паники</span>. Яркая вспышка <span class="condition">ослепляет тебя на мгновение</span>.

        #### **5. Примеры Работы**

        **Пример 1: Атака**
        *   **Запрос Игрока:** "Мой варвар <span class="name">Крэг</span> бьет гоблина своей секирой."
        *   **Ответ ИИ (Успех):**
            > <span class="name">Крэг</span> издает боевой клич и обрушивает свою огромную секиру на врага. <span class="name">Гоблин</span> пытается поднять свой маленький щит, но он разлетается в щепки от мощи удара. Лезвие глубоко <span class="damage">вгрызается в плечо монстра, нанося 11 единиц рубящего урона</span>. <span class="name">Гоблин</span> вопит и отшатывается назад, хватаясь за раненую руку.

        **Пример 2: Проваленная атака из-за брони**
        *   **Запрос Игрока:** "Мой плут <span class="name">Финн</span> пытается ударить рыцаря кинжалом."
        *   **Ответ ИИ (Провал):**
            > <span class="name">Финн</span> молниеносно выскакивает из тени и наносит укол в спину закованному в сталь рыцарю. Однако острие кинжала лишь со скрежетом скользит по толстым латам. Твоя атака не смогла пробить его защиту. Рыцарь медленно разворачивается, его взгляд сквозь прорезь шлема устремлен прямо на тебя.

        **Пример 3: Исцеление**
        *   **Запрос Игрока:** "Жрица <span class="name">Алианна</span> кастует "Исцеление ран" на <span class="name">Гимли</span>."
        *   **Ответ ИИ:**
            > <span class="name">Алианна</span> кладет руки на грудь раненого <span class="name">Гимли</span> и шепчет слова молитвы. Ее ладони окутывает божественное сияние, которое перетекает в тело гнома. Ты видишь, как его раны начинают закрываться. Теплое сияние <span class="heal">восстанавливает ему 9 очков здоровья</span>, и он перестает хрипеть, его дыхание выравнивается.

        Контекст:
        {self.get_actual_context()}
        Действие для {character.name}: {action}
        """
        reply = self.classifier.general_text_llm_request(prompt)
        self.context += f"\n\n{character.name} performs action (DM's response): {reply}" # type: ignore
        self.apply_changes_after_turn(reply, character) # type: ignore
        chapter.move_to_next_turn()
        return reply
    
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
                self.update_scene(change.object_name, change.changes)
            self.context += f"""
            SYSTEM LOG [
                {change}
                was applied
            ]
            """ # type: ignore
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
        Ответь на вопрос, выделяя ключевые слова тегом <span class='keyword'>ключевые слова</span> и выделяя имена тегом <span class='name'>имена</span> . НЕ используй MarkDown теги.
        Контекст:
        {self.get_actual_context()}
        Вопрос: "{question}"
        """
        reply = self.classifier.general_text_llm_request(prompt)
        self.context =  str(self.context) + f"\n\nPlayer that controlls {character.name} asks: {question}"
        self.context += f"\n\nDM's response: {reply}"
        print(f"{SUCCESS_COLOR}🎲 DM's response:{Colors.RESET} {reply}")
        return reply

    def trim_context(self):
        self.context = self.classifier.general_text_llm_request(
            f"""
                Make this actions log about {MAX_CONTEXT_LENGTH} words long.
                Dont miss important details even if they are not directly related to the current scene or if they are in the past. Try to not miss DM's intent. If the context is short enough, just return it as is.
            """
        )
        

    def process_interaction(self, character: Character, interaction: str):
        """
        Processes a character's interaction, deciding the outcome of actions and questions.
        """
        decision : ClassifyInformationOrActionRequest = self.classifier.generate(
            contents=f"""
            context:
            {self.context}
            \nplayer's character:
            {str(character)}
            player's request:
            {interaction}
            """, 
            pydantic_model=ClassifyInformationOrActionRequest
        )  # type: ignore
        interaction += "\n\n"
        interaction += decision.reasoning # type: ignore
        result = None
        if decision.decision: # type: ignore
            print(f"{INFO_COLOR}Request for info {Colors.RESET}")
            result = self.askedDM(character, interaction)
        else:
            print(f"{INFO_COLOR}Request for action {Colors.RESET}")
            result = self.action(character, interaction)
        return result
    
    def start_turn_loop(self):
        """
        Starts the turn loop for the fight, allowing characters to take actions.
        """
        print(f"\n{HEADER_COLOR}⚔️ Starting fight in scene:{Colors.RESET} {ENTITY_COLOR}{self.scene.name if self.scene else 'Unknown Scene'}{Colors.RESET}")
        
        for character in self.characters:
            print(f"\n{HEADER_COLOR}👤 {character.name}'s turn:{Colors.RESET}")
    
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

    def enemy_turn(self):
        """
        Handles the enemy's turn in the fight.
        """
        print(f"\n{HEADER_COLOR}👹 Enemy's turn:{Colors.RESET}")
        # Here you can implement enemy actions, AI logic, etc.
        # For now, we will just simulate an enemy action
        NPC_action = self.classifier.general_text_llm_request(
            f"""
            {global_defines.dungeon_master_core_prompt}
            Сейчас ты выступаешь в роли персонажа, который контролируется мастером (враг или неигровой персонаж). 
            Пожалуйста, опиши его действия.
            ПЕРСОНАЖ:
            {self.get_active_character().model_dump_json(indent=2)}
            SCENE CONTEXT:
            {self.get_actual_context()}
            
            пример ответа:
            <имя персонажа> замахивается мечом, крича "За короля!" и наносит удар по противнику <имя противника>.
            """
        )
        
        self.action(self.get_active_character(), NPC_action) # type: ignore
        
        
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
    context = "Ice cave in a frozen mountain, where a group of adventurers is trapped by a powerful ice elemental."
    print(f"{HEADER_COLOR}🎮 Starting new chapter (enemy turn test)...{Colors.RESET}")
    chapter = ChapterLogicFight(
        context = context,
        characters = [
            generator.generate(Character, "random character with full hp and a single dager (player character)", context, "Russian"),
            generator.generate(Character, "random monster with full hp and some magic spells (enemy NPC)", context, "Russian")
        ]
    )
    chapter.setup_fight()
    def print_game_sate():
        for c in chapter.characters:
            print(c.model_dump_json(indent=2))
        print(chapter.scene.model_dump_json(indent=2)) # type: ignore
        print(chapter.turn_order)
    while true:
        if chapter.get_active_character().is_player:
            user_input = input(f"{ENTITY_COLOR}{chapter.get_active_character_name()} -->{Colors.RESET}  ")
            if user_input == "?": 
                print_game_sate()
                continue
            chapter.process_interaction(chapter.characters[0], user_input) # type: ignore
        else:
            dm_action = chapter.enemy_turn()