from typing import TYPE_CHECKING

from server_communication.events import EventBuilder
if TYPE_CHECKING:
    from game import Game
    
import mimetypes
import os
import time
import queue
import threading
from dotenv import load_dotenv
from google import genai
from google.genai import types
from global_defines import *

PROMPT_PREVIEW_LENGTH = 10

class ImageGenerator:
    def __init__(self, game : 'Game'):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash-preview-image-generation"
        self.image_dir = os.path.join("static", "images")
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir, exist_ok=True)
        
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.game = game


    async def _worker(self):
        while not self.stop_event.is_set():
            try:
                # Wait for a task, with a timeout to allow checking the stop_event
                prompt, file_name = self.task_queue.get(timeout=1)
                await self._perform_generation(prompt, file_name)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"{ERROR_COLOR}Error in image generation worker: {e}{Colors.RESET}")

    async def _perform_generation(self, prompt: str, file_name: str, type : str = "CHARACTER"):
        """
        Generates an image based on the given prompt and saves it to a file.
        """
        print(f"{INFO_COLOR}(IMAGEN){Colors.RESET} Starting generation for prompt: {prompt[:PROMPT_PREVIEW_LENGTH] + '...' if len(prompt) > PROMPT_PREVIEW_LENGTH else prompt}")
        start_time = time.monotonic()
        prompt += "Generate an imge in a dark fantasy highly realistic style. Use square proportions for the image."
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                response_mime_type="text/plain",
            )

            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents, # type: ignore
                config=generate_content_config,
            ):
                if (
                    chunk.candidates and chunk.candidates[0].content and
                    chunk.candidates[0].content.parts
                ):
                    for part in chunk.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            inline_data = part.inline_data
                            data_buffer = inline_data.data
                            file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png" # type: ignore
                            image_path = os.path.join(self.image_dir, f"{file_name}{file_extension}")
                            
                            with open(image_path, "wb") as f:
                                f.write(data_buffer) # type: ignore
                            
                            end_time = time.monotonic()
                            print(f"{TIME_COLOR}Image generation took {end_time - start_time:.2f} seconds.{Colors.RESET}")
                            print(f"{SUCCESS_COLOR}File saved to: {image_path}{Colors.RESET}")
                            if type == "SCENE":
                                await self.game.announce(EventBuilder.scene_change("scene_changed", f"{file_name}{file_extension}"))            
                            return
            
            print(f"{WARNING_COLOR}Image generation finished but no image data was returned.{Colors.RESET}")

        except Exception as e:
            print(f"{ERROR_COLOR}An exception occurred during image generation: {e}{Colors.RESET}")

    def submit_generation_task(self, prompt: str, file_name: str):
        """
        Submits a task to the generation queue. Does not block.
        """
        print(f"{INFO_COLOR}(IMAGEN){Colors.RESET} Submitting task for prompt: {prompt[:PROMPT_PREVIEW_LENGTH] + '...' if len(prompt) > PROMPT_PREVIEW_LENGTH else prompt}")
        self.task_queue.put((prompt, file_name))

    def start(self):
        """Starts the worker thread."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            print(f"{SUCCESS_COLOR}(IMAGEN) Worker thread started.{Colors.RESET}")

    def stop(self, wait_for_completion=True):
        """Stops the worker thread."""
        print(f"{INFO_COLOR}(IMAGEN) Stopping worker thread...{Colors.RESET}")
        if wait_for_completion:
            print("(Waiting for queue to empty)")
            self.task_queue.join() # Wait for all tasks to be processed
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join() # Wait for the thread to terminate
        print(f"{SUCCESS_COLOR}(IMAGEN) Worker thread stopped.{Colors.RESET}")
