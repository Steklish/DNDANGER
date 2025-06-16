# generator.py

import os
import json
import time
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import google.generativeai as genai
from dotenv import load_dotenv
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

# Import the self-contained schemas from our separate file
# Make sure you have your schemas.py file in a 'models' subfolder or adjust the import.
from models import *

# A Generic Type Variable for our generator's return type
T = TypeVar('T', bound=BaseModel)

class ObjectGenerator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing the Gemini API to return a JSON object.
    """
    def __init__(self):
        """
        Initializes the generator with Google API credentials.
        """
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_DUMB", "gemini-2.0-flash-lite"))

    def _clean_json_response(self, text_response: str) -> str:
        """
        Cleans the raw text response from the model to isolate the JSON object.
        """
        start_index = text_response.find('{')
        if start_index == -1:
            raise ValueError("No JSON object found in the response.")
        
        end_index = text_response.rfind('}')
        if end_index == -1:
            raise ValueError("No JSON object found in the response.")
            
        return text_response[start_index : end_index + 1]

    def generate(self, pydantic_model: Type[T], prompt: Optional[str] = None, context: Optional[str] = None, language: Optional[str] = None) -> T:
        """
        Generates a Pydantic instance by asking the model for a JSON response.

        Args:
            pydantic_model: The Pydantic class to create an instance of.
            prompt: A specific description of the object to generate.
            context: Optional context to guide the generation.
            language: The desired language for the generated text content (e.g., "Russian").

        Returns:
            An instance of the specified Pydantic class.
        """
        schema_json = json.dumps(pydantic_model.model_json_schema(), indent=2)

        if prompt:
            user_request = f"Generate an object based on this description: '{prompt}'."
        else:
            user_request = "Generate a completely new, creative, and random object."

        context_instruction = f"The generated object must fit this theme or context: '{context}'." if context else ""
        
        # --- NEW: Language Instruction ---
        language_instruction = ""
        if language:
            language_instruction = f"CRITICAL: All generated text content (like names, descriptions, effects, etc.) MUST be in the following language: {language}."

        # --- Construct the full prompt with the new language instruction ---
        full_prompt = f"""
        You are a data generation assistant. Your task is to create a JSON object that strictly adheres to the provided JSON schema.

        JSON Schema:
        ```json
        {schema_json}
        ```

        Request:
        {user_request}
        {context_instruction}
        {language_instruction}

        IMPORTANT: Your response MUST be ONLY the valid JSON object that conforms to the schema. Do not include any other text, explanations, or markdown formatting like ```json.
        """
        
        print(f"\n{HEADER_COLOR}📡 Sending request to Gemini{Colors.RESET} for: {ENTITY_COLOR}{pydantic_model.__name__}{Colors.RESET} (Language: {INFO_COLOR}{language or 'Default'}{Colors.RESET})")
        response = self.model.generate_content(full_prompt)

        try:
            cleaned_response = self._clean_json_response(response.text)
            parsed_data = json.loads(cleaned_response)
            return pydantic_model(**parsed_data)

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"{ERROR_COLOR}❌ Error processing Gemini response:{Colors.RESET} {e}")
            print(f"{WARNING_COLOR}Raw Response from API:{Colors.RESET}")
            print(response.text)
            print(f"{Colors.DIM}{'─' * 30}{Colors.RESET}")
            raise ValueError("Failed to generate a valid Pydantic instance from the API's text response.")

# --- Main execution block (Updated with Russian examples and colorful output) ---
if __name__ == "__main__":
    load_dotenv()
    
    generator = ObjectGenerator()
    total_start_time = time.time()
    generation_times = []

    try:
        # --- Example 1: Generate a RANDOM character in RUSSIAN ---
        print(f"\n{HEADER_COLOR}{'=' * 20}{Colors.RESET}")
        print(f"{HEADER_COLOR}[1] Generating a random character in Russian...{Colors.RESET}")
        start_time = time.time()
        random_russian_character = generator.generate(Character, language="Russian")
        generation_time = time.time() - start_time
        generation_times.append(("Random Russian Character", generation_time))
        print(f"\n{SUCCESS_COLOR}✅ Generated Random Russian Character{Colors.RESET} ({TIME_COLOR}took {generation_time:.2f} seconds{Colors.RESET}):")
        print(random_russian_character.model_dump_json(indent=2))

        # --- Example 2: Generate a SPECIFIC item in RUSSIAN ---
        print(f"\n{HEADER_COLOR}{'=' * 20}{Colors.RESET}")
        print(f"{HEADER_COLOR}[2] Generating a specific item in Russian...{Colors.RESET}")
        start_time = time.time()
        item_prompt_ru = "Волшебный меч, который светится синим в присутствии орков"
        item_context_ru = "Выкован гномами в древней, забытой кузнице"
        russian_sword = generator.generate(Item, prompt=item_prompt_ru, context=item_context_ru, language="Russian")
        generation_time = time.time() - start_time
        generation_times.append(("Specific Russian Item", generation_time))
        print(f"\n{SUCCESS_COLOR}✅ Generated Specific Russian Item{Colors.RESET} ({TIME_COLOR}took {generation_time:.2f} seconds{Colors.RESET}):")
        print(russian_sword.model_dump_json(indent=2))
        
        # --- Example 3: Generate a random scene ---
        print(f"\n{HEADER_COLOR}{'=' * 20}{Colors.RESET}")
        print(f"{HEADER_COLOR}[3] Generating a random scene...{Colors.RESET}")
        start_time = time.time()
        random_scene = generator.generate(Scene, language="Russian")
        generation_time = time.time() - start_time
        generation_times.append(("Random Scene in Russian", generation_time))
        print(f"\n{SUCCESS_COLOR}✅ Generated Random Scene in Russian{Colors.RESET} ({TIME_COLOR}took {generation_time:.2f} seconds{Colors.RESET}):")
        print(random_scene.model_dump_json(indent=2))

        # Print performance summary
        total_time = time.time() - total_start_time
        print(f"\n{HEADER_COLOR}{'=' * 20}{Colors.RESET}")
        print(f"{HEADER_COLOR}🕒 Performance Summary:{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 20}{Colors.RESET}")
        for name, duration in generation_times:
            print(f"{INFO_COLOR}▸ {name}:{Colors.RESET} {TIME_COLOR}{duration:.2f} seconds{Colors.RESET}")
        print(f"{HEADER_COLOR}Total execution time:{Colors.RESET} {TIME_COLOR}{total_time:.2f} seconds{Colors.RESET}")
        print(f"{HEADER_COLOR}{'=' * 20}{Colors.RESET}")

    except ValueError as e:
        print(f"\n{ERROR_COLOR}❌ An error occurred during generation:{Colors.RESET} {e}")