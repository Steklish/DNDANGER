from dotenv import load_dotenv
from classifier import Classifier
from generator import ObjectGenerator
from models import *
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
        """based on the global context, extract only the details that matter for the next scene. If no characters provided, dont make them up. If some info is missing you are allowed to create it. Dont ask additional information.
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
        
        Ты Мастер D&D. Определи исход действия. Твой ответ ДОЛЖЕН быть валидным JSON.
        КЛЮЧЕВОЕ ПРАВИЛО: Ты ОБЯЗАН вернуть массив "effects", даже если он пустой ([]).
        В "description" используй HTML-теги: <span class="damage">урон</span>, <span class="heal">исцеление</span>, <span class="condition">состояние</span>, <span class="name">Имя</span>.

        Контекст:
        
        Действие для {character.name}: {action}
        """
        
        
    def askedDM(self, character: Character, question: str):
        """
        Handles a character asking the DM a question.
        
        :param character: The character asking the question.
        :param question: The question being asked.
        """
        print(f"\n{ENTITY_COLOR}{character.name}{Colors.RESET} {INFO_COLOR}asks:{Colors.RESET} {question}")
        prompt = f"""
        {global_defines.dungeon_master_core_prompt}
        Ответь на вопрос, выделяя <span class='keyword'>ключевые слова</span>.
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
        decision = self.classifier.generate(
            contents=f"""
            context:
            {self.context}
            \nplayer's character:
            {str(character)}
            player's request:
            {interaction}
            """, 
            pydantic_model=ClassifyInformationOrActionRequest
        )
        
        interaction += decision["reasoning"] # type: ignore
        
        if decision["decision"]: # type: ignore
            self.askedDM(character, interaction)
        else:
            self.action(character, interaction)

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
    
    print(f"{HEADER_COLOR}🎮 Starting new chapter...{Colors.RESET}")
    chapter = ChapterLogicFight(context = "the journey begins...")
    chapter.setup_fight()