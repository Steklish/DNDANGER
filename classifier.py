import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from global_defines import *

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
