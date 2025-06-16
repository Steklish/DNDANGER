import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
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
        self.model = os.getenv("GEMINI_MODEL_DUMB", "gemini-2.0-flash")
        
    def generate(self, contents: str, pydantic_model: Type[T], response_mime_type: str = "application/json"):
        try:
            print(f"{INFO_COLOR}🤖 Generating content with model:{Colors.RESET} {ENTITY_COLOR}{self.model}{Colors.RESET}")
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config={
                    "response_mime_type": response_mime_type,
                    "response_schema": pydantic_model,
                }
            )
            print(f"{SUCCESS_COLOR}✅ Content generated successfully{Colors.RESET}")
            return response.parsed
        except Exception as e:
            print(f"{ERROR_COLOR}❌ Error generating content:{Colors.RESET} {e}")
            return None
        
    def general_text_llm_request(self, contents: str, response_mime_type: str = "text/plain"):
        """
        General method to make a text request to the LLM.
        """
        try:
            print(f"{INFO_COLOR}🤖 Making text request to model:{Colors.RESET} {ENTITY_COLOR}{self.model}{Colors.RESET}")
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config={
                    "response_mime_type": response_mime_type,
                }
            )
            print(f"{SUCCESS_COLOR}✅ Response received{Colors.RESET}")
            return response.text
        except Exception as e:
            print(f"{ERROR_COLOR}❌ Error in text request:{Colors.RESET} {e}")
            return None
        
        
if __name__ == "__main__":
    load_dotenv()
    
    classifier = Classifier()
    print(f"\n{HEADER_COLOR}Test 1: Item Request{Colors.RESET}")
    a = classifier.generate(
        "Привет, я хочу купить меч и броню. Меч должен быть острым и легким, а броня - прочной и удобной.", 
        ClassifyInformationOrActionRequest)
    print(f"{INFO_COLOR}Result:{Colors.RESET}")
    print(a)
    
    print(f"\n{HEADER_COLOR}Test 2: Spell Question{Colors.RESET}")
    a = classifier.generate(
        "Как работает файрбол?", 
        ClassifyInformationOrActionRequest)
    print(f"{INFO_COLOR}Result:{Colors.RESET}")
    print(a)
