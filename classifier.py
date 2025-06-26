import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
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

from models import *

T = TypeVar('T', bound=BaseModel)


class Classifier:
    """
    Uses gemini AI model to generate objects of type [T] (pydantic schema) based on the input text.
    """
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL_DUMB")
        
    def generate(self, contents: str, pydantic_model: Type[T], response_mime_type: str = "application/json"):
        try:
            print(f"{INFO_COLOR}Generating content with model:{Colors.RESET} {ENTITY_COLOR}{self.model}{Colors.RESET}")
            response = self.client.models.generate_content(
                model=self.model, # type: ignore
                contents=contents,
                config={
                    "response_mime_type": response_mime_type,
                    "response_schema": pydantic_model,
                }
            )
            return response.parsed
        except Exception as e:
            print(f"{ERROR_COLOR}Error generating content: {e}{Colors.RESET}")
            raise e
       
    def generate_list(self, contents: str, pydantic_model: Type[T], response_mime_type: str = "application/json"):
        try:
            print(f"{INFO_COLOR}Generating content with model:{Colors.RESET} {ENTITY_COLOR}{self.model}{Colors.RESET}")
            response = self.client.models.generate_content(
                model=self.model, # type: ignore
                contents=contents,
                config={
                    "response_mime_type": response_mime_type,
                    "response_schema": list[pydantic_model],
                }
            )
            return response.parsed
        except Exception as e:
            print(f"{ERROR_COLOR}Error generating content: {e}{Colors.RESET}")
            raise e
        
        
        
    def general_text_llm_request(
        self,
        contents: str,
        language: str = "Russian",
        response_mime_type: str = "text/plain"
    ) -> str:
        """
        Makes a clear text request to the LLM, ensuring a non-empty string response.

        Args:
            contents: The primary prompt or content for the LLM.
            language: The desired language for the response (e.g., "Russian", "English").
            response_mime_type: The expected MIME type for the response.

        Returns:
            The response text as a string.

        Raises:
            ValueError: If the LLM returns an empty or null response.
            Exception: Propagates exceptions from the underlying API call.
        """
        full_prompt = (
            f"Задание: Ответь на следующий запрос на {language} языке.\n"
            "---\n"
            f"{contents}"
        )

        try:
            print(f"{INFO_COLOR}Making text request to model: {ENTITY_COLOR}{self.model}{Colors.RESET}")
            response = self.client.models.generate_content(
                model=self.model,  # type: ignore
                contents=full_prompt,
                config={
                    "response_mime_type": response_mime_type,
                }
            )
            
            if response.text:
                return response.text
            else:
                # If the response or its text is empty, it's a failure case.
                raise ValueError("LLM returned an empty response.")
                
        except Exception as e:
            print(f"{ERROR_COLOR}Error during general text LLM request: {e}{Colors.RESET}")
            # Re-raise the exception to be handled by the caller.
            raise
        
        
if __name__ == "__main__":
    load_dotenv()
    
	# list of changes test
    classifier = Classifier()
    print(f"\n{HEADER_COLOR}Test x: char change Request{Colors.RESET}")
    a = classifier.generate_list(
        """
        {
  "name": "Громобой Ярослав",
  "max_hp": 75,
  "current_hp": 42,
  "ac": 16,
  "is_player": true,
  "conditions": [
    "Ослаблен",
    "Ошеломлен"
  ],
  "inventory": [
    {
      "name": "Большой двуручный меч 'Кровожад'",
      "description": "Огромный меч, выкованный в древние времена. Покрыт рунами, которые, как говорят, усиливают кровожадность владельца.",
      "item_type": "Weapon",
      "weight": 8.5,
      "value": 1500,
      "quantity": 1,
      "rarity": "Rare",
      "is_magical": true,
      "damage": "2d6 + 3",
      "damage_type": "Рубящий",
      "armor_class": null,
      "effect": "При попадании цель должна пройти спасбросок Силы или упасть на землю.",
      "properties": []
    },
    {
      "name": "Зелье исцеления",
      "description": "Небольшая бутылочка с красной жидкостью, способной исцелять раны.",
      "item_type": "Potion",
      "weight": 0.1,
      "value": 50,
      "quantity": 3,
      "rarity": "Common",
      "is_magical": true,
      "damage": null,
      "damage_type": null,
      "armor_class": null,
      "effect": "Восстанавливает 2d4+2 очка здоровья.",
      "properties": []
    },
    {
      "name": "Кожаный доспех",
      "description": "Простой кожаный доспех, обеспечивающий базовую защиту.",
      "item_type": "Armor",
      "weight": 5.0,
      "value": 100,
      "quantity": 1,
      "rarity": "Common",
      "is_magical": false,
      "damage": null,
      "damage_type": null,
      "armor_class": 11,
      "effect": null,
      "properties": []
    }
  ],
  "abilities": [
    {
      "name": "Удар берсерка",
      "description": "Яростная атака, наносящая огромный урон, но снижающая защиту.",
      "details": {
        "duration": "1 раунд",
        "damage_bonus": "+5",
        "ac_penalty": "-2"
      }
    },
    {
      "name": "Клич воина",
      "description": "Крик, вселяющий храбрость в союзников и вселяющий страх в врагов.",
      "details": {
        "range": "30 футов",
        "effect": "Союзники получают преимущество на броски против страха на 1 раунд."
      }
    }
  ],
  "personality_history": "Ярослав – грозный воин, известный своей силой и гневом на поле боя. Он всегда готов защищать слабых и сражаться за правое дело, хотя иногда его гнев затмевает разум. В прошлом потерял семью в результате нападения гоблинов, что закалило его характер."
}

{
  "name": "Заброшенная Хижина Лесника",
  "description": "Старая хижина, окутанная полумраком. Солнечный свет едва проникает сквозь пыльные окна, освещая танцующие в воздухе частицы пыли. Слышен тихий скрип половиц и слабое дуновение ветра, доносящее запах сырости и прелых листьев. В воздухе висит еле уловимый аромат старого дерева и заплесневелой еды.",
  "size_description": "Небольшая однокомнатная хижина, примерно 4 на 5 метров, с низким потолком.",
  "objects": [
    {
      "name": "Большая Дубвая Дверь",
      "description": "Массивная дубовая дверь, потемневшая от времени и покрытая трещинами. На двери видна резная эмблема медведя. Ручка сделана из кованого железа, ржавая и холодная на ощупь. Дверь выглядит очень тя
      "size_description": "Примерно 2 метра в высоту и 1 метр в ширину.",
      "position_in_scene": "У входа в хижину, в северной стене.",
      "interactions": [
        "Открыть",
        "Закрыть",
        "Осмотреть"
      ]
    },
    {
      "name": "Старый Деревянный Стол",
      "description": "Круглый стол, сделанный из грубо обработанного дерева. На поверхности стола видны следы от ножей и пятна от пролитой жидкости. Стол стоит на трех кривых ножках, заметно шатается.",
      "size_description": "Около метра в диаметре.",
      "position_in_scene": "В центре комнаты.",
      "interactions": [
        "Осмотреть",
        "Потрогать"
      ]
    },
    {
      "name": "Камин",
      "description": "Большой каменный камин, в котором давно не разводили огонь. Сажа покрывает внутренние стены. У основания камина куча пепла и несколько обгоревших поленьев. Над камином висит ржавый крюк.",
      "size_description": "Примерно 1.5 метра в высоту и 1 метр в ширину.",
      "position_in_scene": "У западной стены.",
      "interactions": [
        "Осмотреть"
      ]
    }
  ]
}

Ярослав получил 10 урона и теперь заражен болезнью, которая снижает его максимальное здоровье на 10 единиц. Хижина Лесника была атакована гоблинами, которые подорвали несущуб стену и теперь от хижины осталать только входная дверь и часть стены.
        """, 
        ChangesToMake)
    print(f"{INFO_COLOR}Result:{Colors.RESET}")
    for i in a: # type: ignore
        print(i.model_dump_json(indent=2))
    
    print(f"\n{HEADER_COLOR}Test 2: Spell Question{Colors.RESET}")
    a = classifier.generate(
        "Как работает файрбол?", 
        ClassifyInformationOrActionRequest)
    print(f"{INFO_COLOR}Result:{Colors.RESET}")
    print(a)
