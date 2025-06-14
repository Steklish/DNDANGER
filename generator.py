# generator.py

import os
import json
import time  # Add time module for performance measurements
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import google.generativeai as genai
from dotenv import load_dotenv

# Import the self-contained schemas from our separate file
# Make sure you have your schemas.py file in a 'models' subfolder or adjust the import.
from models.schemas import Character, Item

# A Generic Type Variable for our generator's return type
T = TypeVar('T', bound=BaseModel)

class GeminiGenerator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing the Gemini API to return a JSON object.
    """
    def __init__(self, api_key: str, model_name: str):
        """
        Initializes the generator with Google API credentials.
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

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
        
        print(f"\n--- Sending request to Gemini for: {pydantic_model.__name__} (Language: {language or 'Default'}) ---")
        response = self.model.generate_content(full_prompt)

        try:
            cleaned_response = self._clean_json_response(response.text)
            parsed_data = json.loads(cleaned_response)
            return pydantic_model(**parsed_data)

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"Error processing Gemini response: {e}")
            print("--- Raw Response from API ---")
            print(response.text)
            print("-----------------------------")
            raise ValueError("Failed to generate a valid Pydantic instance from the API's text response.")

# --- Main execution block (Updated with Russian examples) ---
if __name__ == "__main__":
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_DUMB", "gemini-1.5-flash-latest")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")

    generator = GeminiGenerator(api_key=api_key, model_name=model_name)
    total_start_time = time.time()
    generation_times = []

    try:
        # --- Example 1: Generate a RANDOM character in RUSSIAN ---
        print("\n==================\n[1] Generating a random character in Russian...")
        start_time = time.time()
        random_russian_character = generator.generate(Character, language="Russian")
        generation_time = time.time() - start_time
        generation_times.append(("Random Russian Character", generation_time))
        print(f"\n✅ Generated Random Russian Character (took {generation_time:.2f} seconds):")
        # IMPORTANT: Use ensure_ascii=False to print Cyrillic characters correctly.
        print(random_russian_character.model_dump_json(indent=2))

        # --- Example 2: Generate a SPECIFIC item in RUSSIAN ---
        print("\n==================\n[2] Generating a specific item in Russian...")
        start_time = time.time()
        item_prompt_ru = "Волшебный меч, который светится синим в присутствии орков"
        item_context_ru = "Выкован гномами в древней, забытой кузнице"
        russian_sword = generator.generate(Item, prompt=item_prompt_ru, context=item_context_ru, language="Russian")
        generation_time = time.time() - start_time
        generation_times.append(("Specific Russian Item", generation_time))
        print(f"\n✅ Generated Specific Russian Item (took {generation_time:.2f} seconds):")
        print(russian_sword.model_dump_json(indent=2))
        
        # --- Example 3: Generate a default (English) character for comparison ---
        print("\n==================\n[3] Generating a random character in English (default)...")
        start_time = time.time()
        random_character = generator.generate(Character)
        generation_time = time.time() - start_time
        generation_times.append(("Random English Character", generation_time))
        print(f"\n✅ Generated Random English Character (took {generation_time:.2f} seconds):")
        print(random_character.model_dump_json(indent=2))

        # Print performance summary
        total_time = time.time() - total_start_time
        print("\n==================")
        print("🕒 Performance Summary:")
        print("------------------")
        for name, duration in generation_times:
            print(f"- {name}: {duration:.2f} seconds")
        print(f"Total execution time: {total_time:.2f} seconds")
        print("==================")

    except ValueError as e:
        print(f"\nAn error occurred during generation: {e}")