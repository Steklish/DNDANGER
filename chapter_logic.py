from dotenv import load_dotenv
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
    INFO_COLOR
)
import global_defines
from models import *



class ChapterLogicFight:
    """Fight logic for a chapter in a game, handling character interactions and actions."""
    
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

    
    def __init__(self, context: str, characters: List[Character] = [], language: str = "Russian"):
        self.context = context
        self.last_scene = context
        self.characters = characters        
        self.generator = ObjectGenerator()
        self.scene = None
        self.classifier = Classifier()
        self.language = language
        

    def setup_fight(self):
        """
        Initializes the fight by generating objects and their actions based on the context.
        """
        print(f"\n{HEADER_COLOR}🎲 Generating Scene...{Colors.RESET}")
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

        self.context = self.classifier.general_text_llm_request(
        """
        based on the global context, extract only the details that matter for the next scene. If no characters provided, dont make them up. If some info is missing you are allowed to create it. Dont ask additional information.
        in no context provided at all come up with something like "evry memory have faded away and the past seems very blury"
        """
        )
        
        print(f"\n{HEADER_COLOR}Current Scene:{Colors.RESET}")
        print(f"{INFO_COLOR}{str(self.scene)}{Colors.RESET}")
        print(f"\n{HEADER_COLOR}Current Context:{Colors.RESET}")
        print(f"{INFO_COLOR}{str(self.context)}{Colors.RESET}")
        

    def get_actual_context(self) -> str:
        return f"""
    <story and situation>
    {self.context}
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
        
        Ты Мастер D&D. Определи исход действия. Используй HTML-теги: 
        тег для урона <span class="damage">урон</span>, 
        тег для исцеления <span class="heal">исцеление</span>, 
        тег для состояния <span class="condition">состояние</span>, 
        тег для имени <span class="name">Имя</span>.
        НЕ используй MarkDown теги
        Следи за тем, чтобы действия были логически обоснованы, особенно если действующее лицо - это игрок.

        Контекст:
        {self.get_actual_context()}
        Действие для {character.name}: {action}
        """
        reply = self.classifier.general_text_llm_request(prompt)
        self.apply_changes_after_turn(reply, character) # type: ignore
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
            else:
                self.context += str(change) # type: ignore
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
        self.context =  str(self.context) + f"\n\n{character.name} asks: {question}"
        self.context += f"\n\nDM's response: {reply}"
        print(f"{SUCCESS_COLOR}🎲 DM's response:{Colors.RESET} {reply}")
        return reply

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
    print(f"{HEADER_COLOR}🎮 Starting new chapter...{Colors.RESET}")
    chapter = ChapterLogicFight(context = "the journey begins...")
    chapter.setup_fight()
    r_ch = chapter.generator.generate(Character, "random character with full hp and no items in inventory", "no context", "Russian")
    print(r_ch.model_dump_json(indent=2))
    chapter.characters.append(r_ch)
    print(chapter.scene.model_dump_json(indent=2)) # type: ignore
    # chapter.update_scene(chapter.scene.name, "заставь все гореть в пожаре") # type: ignore
    # print(chapter.scene.model_dump_json(indent=2)) # type: ignore
    hhh = input("enter a question to a DM...    ")
    print(chapter.process_interaction(chapter.characters[0], hhh)) # type: ignore