import asyncio
from typing import TYPE_CHECKING, Optional

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
    def __init__(self, game: 'Game', main_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash-preview-image-generation"
        self.image_dir = os.path.join("static", "images")
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir, exist_ok=True)
        
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.game = game
        self.main_loop = main_loop

    def _async_worker_entry(self):
        """The entry point for the new thread. It creates and runs the asyncio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_worker())

    async def _async_worker(self):
        """The main async logic for the worker. It waits for tasks and runs them."""
        print(f"{SUCCESS_COLOR}(IMAGEN) Async worker started.{Colors.RESET}")
        while not self.stop_event.is_set():
            try:
                prompt, file_name, generation_type = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: self.task_queue.get(timeout=1)
                )
                asyncio.create_task(self._perform_generation(prompt, file_name, generation_type))
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue
            except Exception as e:
                print(f"{ERROR_COLOR}Error in async worker loop: {e}{Colors.RESET}")

    async def _perform_generation(self, prompt: str, file_name: str, request_type : str = "CHARACTER"):
        """Generates an image and schedules the announcement on the main event loop."""
        print(f"{INFO_COLOR}(IMAGEN){Colors.RESET} Starting generation for: {file_name}")
        start_time = time.monotonic()
        full_prompt = f"""
Epic 1970s dark fantasy paperback book cover art depicting {prompt}.
The style is a haunting synthesis of Zdzisław Beksiński's dystopian surrealism and the heroic fantasy of Darrell K. Sweet.
Rendered as a highly detailed oil painting with a gritty, weathered texture.
The scene is bathed in dramatic chiaroscuro lighting, casting deep, ominous shadows and creating a palpable gothic atmosphere.
A dark, desaturated color palette dominates, punctuated by a single, eerie light source.
The composition is theatrical and dynamic, rich with intricate, macabre details.

4k, ultra-detailed, masterpiece. --no text, labels, writing, signatures, watermarks
"""
        
        try:
            # The SDK call is synchronous, so we run it in a thread to avoid blocking our worker's loop
            response_chunks = await asyncio.to_thread(
                self.client.models.generate_content_stream,
                model=self.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    response_mime_type="text/plain",
                ),
            )

            image_saved = False
            for chunk in response_chunks:
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".png" # type: ignore
                            image_path = os.path.join(self.image_dir, f"{file_name}{file_extension}")
                            
                            with open(image_path, "wb") as f:
                                f.write(part.inline_data.data)
                            
                            end_time = time.monotonic()
                            print(f"{TIME_COLOR}Image generation for '{file_name}' took {end_time - start_time:.2f}s.{Colors.RESET}")
                            print(f"{SUCCESS_COLOR}File saved to: {image_path}{Colors.RESET}")
                            
                            # This is the crucial part: calling back to the main thread
                            if self.main_loop and self.main_loop.is_running():
                                if  request_type == "SCENE":
                                    event = EventBuilder.scene_change("info",f"{file_name}{file_extension}")
                                    asyncio.run_coroutine_threadsafe(self.game.announce(event), self.main_loop)
                            
                            image_saved = True
                            break
                if image_saved:
                    break
            
            if not image_saved:
                print(f"{WARNING_COLOR}Image generation for '{file_name}' finished with no image data.{Colors.RESET}")

        except Exception as e:
            print(f"{ERROR_COLOR}Exception during image generation for '{file_name}': {e}{Colors.RESET}")

    def submit_generation_task(self, prompt: str, file_name: str, generation_type: str = "CHARACTER"):
        """Submits a task to the generation queue. Does not block."""
        print(f"{INFO_COLOR}(IMAGEN){Colors.RESET} Submitting task for: {file_name}")
        self.task_queue.put((prompt, file_name, generation_type))

    def start(self):
        """Starts the worker thread."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            if self.main_loop is None:
                try:
                    self.main_loop = asyncio.get_running_loop()
                except RuntimeError:
                    print(f"{ERROR_COLOR}(IMAGEN) Could not get running event loop. Call start() from an async context.{Colors.RESET}")
                    return

            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._async_worker_entry, daemon=True)
            self.worker_thread.start()

    def stop(self, wait_for_completion=True):
        """Stops the worker thread."""
        print(f"{INFO_COLOR}(IMAGEN) Stopping worker thread...{Colors.RESET}")
        if wait_for_completion:
            print("(Waiting for queue to empty)")
            self.task_queue.join()
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join()
        print(f"{SUCCESS_COLOR}(IMAGEN) Worker thread stopped.{Colors.RESET}")
