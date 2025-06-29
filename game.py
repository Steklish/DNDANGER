import json
from multiprocessing import allow_connection_pickling
from chapter_logic import Chapter
from classifier import Classifier
from generator import ObjectGenerator
from models.game_modes import GameMode
from models.schemas import Character
from server_communication import *
from server_communication.events import EventBuilder
from story_manager import StoryManager
from global_defines import *
import asyncio
MAX_MESSAGE_HISTORY_LENGTH = 100
BUFFER_SIZE_FOR_QUEUE = 100
KEEPALIVE_INTERVAL_SECONDS = 5

class Game:
    """
    State of chapter management
    """

    def __init__(self) -> None:
        """
        Initialize game + scene and game events logic
        """
        self.message_history = []
        self.listeners = []
        self.listener_names = [] # character names
        self.generator = ObjectGenerator()
        self.classifier = Classifier()
        self.context = ""
        self.story_manager = StoryManager("campaigns/campaign.json")
        self.context = self.story_manager.get_current_plot_context()

        # Generate the initial NPC based on the campaign's starting prompt
        self.chapter = Chapter(
            context=self.context,
            story_manager=self.story_manager,
            characters=[],
            game=self
        )
        initial_npc = self.chapter.generate_character(
            self.story_manager.story.initial_character_prompt,
            self.context
        )
        self.chapter.add_character(initial_npc)

        self.chapter.game_mode = GameMode.NARRATIVE

        # Announce the starting location and initial scene description
        # await self.announce(EventBuilder.DM_message(f"Вы находитесь в '{self.story_manager.story.starting_location}'. {self.chapter.scene.description}")) # type: ignore
        # message = {
        #     "message_text": f"Вы находитесь в '{self.story_manager.story.starting_location}'. {self.chapter.scene.description}", # type: ignore
        #     "sender_name": "DM"
        # }
        # self.add_message_to_history(message)
        self.turn_completed_event = asyncio.Event()
        
        
    @classmethod
    async def create(cls):
        """
        Async factory for Game objects.
        """
        self = cls()  # Synchronous __init__
        return self

    async def introduce_scene(self):
        """
        Generates and announces the initial scene introduction.
        """
        prompt = (
            f"The game is starting. The players are in '{self.story_manager.story.starting_location}'. "
            f"The current scene is: {self.chapter.scene.description}. " # type: ignore
            "Write a compelling introduction from the Dungeon Master's perspective to set the mood and describe the initial surroundings. "
            "Emphasize important keywords and names using `<span class='keyword'>keyword</span>` and `<span class='name'>Name</span>` tags."
        )
        introduction = self.classifier.general_text_llm_request(prompt + self.context, "Russian")
        
        message = {
            "message_text": introduction,
            "sender_name": "DM"
        }
        self.add_message_to_history(message)
        await self.announce(EventBuilder.DM_message(introduction))

    async def game_loop(self):
        """
        The main game loop that manages turns and game state based on the current mode.
        """
        await asyncio.sleep(1) # Small delay to let server initialize
        while True:
            if self.chapter.game_mode == GameMode.COMBAT:
                active_char = self.chapter.get_active_character()
                print(f"{INFO_COLOR}It's {active_char.name}'s turn (COMBAT MODE).{Colors.RESET}")

                if active_char.is_player:
                    await self.announce(EventBuilder.lock([active_char.name], game_mode=self.chapter.game_mode.name))
                    try:
                        await asyncio.wait_for(self.turn_completed_event.wait(), timeout=300.0) # 5 min timeout
                    except asyncio.TimeoutError:
                        print(f"{ERROR_COLOR}Player {active_char.name} timed out. Skipping turn.{Colors.RESET}")
                        await self.make_system_announcement(f"Игрок {active_char.name} пропустил свой ход.")
                        self.chapter.move_to_next_turn()
                    finally:
                        self.turn_completed_event.clear()
                else: # NPC's turn in COMBAT
                    await self.announce(EventBuilder.lock_all(self.chapter.game_mode.name))
                    await self.make_system_announcement(f"Ход {active_char.name}...")
                    await self.announce_from_the_game(self.chapter.NPC_turn())
                    self.chapter.move_to_next_turn()
                    await self.announce_from_the_game(self.chapter.after_turn())
                    await asyncio.sleep(1)

            elif self.chapter.game_mode == GameMode.NARRATIVE:
                # In Narrative mode, all players can act. The loop waits for any of them.
                player_names = [p.name for p in self.chapter.characters if p.is_player]
                print(f"{INFO_COLOR}Waiting for player actions (NARRATIVE MODE). Allowed: {player_names}{Colors.RESET}")
                await self.announce(EventBuilder.lock(player_names, game_mode=self.chapter.game_mode.name))
                
                await self.turn_completed_event.wait() # Wait for any player to act
                self.turn_completed_event.clear() # Reset for the next interaction
                print(f"{INFO_COLOR}Narrative action processed. Continuing...{Colors.RESET}")
                await asyncio.sleep(1) # Brief pause after a narrative action
            
            else: # Should not happen
                print(f"{ERROR_COLOR}Unknown game mode: {self.chapter.game_mode}. Defaulting to NARRATIVE.{Colors.RESET}")
                self.chapter.game_mode = GameMode.NARRATIVE
                await asyncio.sleep(5)

    
    async def listen(self, sid : str, listener_char_name : str = "Unknown"):
        """
        Creates a new queue for a listener, adds it to the list,
        and yields messages from it. It also sends a keep-alive signal
         periodically to prevent connection timeouts.
        """
        q = asyncio.Queue(maxsize=BUFFER_SIZE_FOR_QUEUE)
        print(f"{INFO_COLOR}Listener for {listener_char_name} connected. {Colors.RESET}\n Total listeners {len(self.listeners)}")
        
        # Тут был код для блокировки одинаковых имен персонажей, но он херня.
        
        # if listener_char_name in self.listener_names:
        #     self.announce_privately(EventBuilder.reject_connection(sid), q)
        #     print(f"{INFO_COLOR}Connection for {listener_char_name} {Colors.RED} refused. {Colors.RESET}\n Total listeners {len(self.listeners)}")
        #     return
        self.listeners.append(q)
        self.listener_names.append(listener_char_name)
        await self.announce(EventBuilder.player_joined(listener_char_name, self.listener_names))
        try:
            # это чтобы про подключении сразу обновить состояние клиента для того, кто подключился
            await self.announce_privately(EventBuilder.lock([self.chapter.get_active_character_name()], game_mode=self.chapter.game_mode.name), q)
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=KEEPALIVE_INTERVAL_SECONDS)
                    yield msg
                    
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            # If the client disconnects, remove their queue from the list.
            self.listeners.remove(q)
            self.listener_names.remove(listener_char_name)
            print(f"{INFO_COLOR}Listener for {listener_char_name} {Colors.RED} disconnected. {Colors.RESET}\n Total listeners {len(self.listeners)}")
            await self.announce(EventBuilder.player_left(listener_char_name, self.listener_names))
            
    
    
    async def announce_privately(self, msg: dict, q: asyncio.Queue):
        """
        Asynchronously puts a message into a specific listener's asyncio.Queue.
        Handles the case where the queue might be full.

        :param msg: The message dictionary to send (will be JSON serialized).
        :param q: The specific asyncio.Queue of the listener.
        """
        formatted_msg = f"data: {json.dumps(msg)}\n\n"
        try:
            q.put_nowait(formatted_msg)
        except asyncio.QueueFull:
            print(f"Listener queue is full. Discarding the oldest message for this listener.")
            try:
                _ = q.get_nowait()
                q.put_nowait(formatted_msg) # Try putting the new one again
            except asyncio.QueueEmpty:
                # This is a rare race condition but possible. It means another
                # consumer emptied the queue between our check and our get.
                # In this case, we can just put the new message.
                q.put_nowait(formatted_msg)
            except asyncio.QueueFull:
                # This is also very rare. It would mean the queue was full,
                # we couldn't get an item, and it's still full. The client is
                # completely stuck. We'll just drop the new message.
                print(f"Listener queue still full after attempting to discard. Dropping new message: {msg}")
                raise asyncio.QueueFull
            
    async def announce(self, msg: dict):
        """
        Asynchronously broadcasts a message to all active listeners.
        """
        print(f"Broadcasting message to {len(self.listeners)} listeners: {msg}")
        tasks = []
        for q in self.listeners:
            # Create an awaitable task for each private announcement
            task = self.announce_privately(msg, q)
            tasks.append(task)
        
        # asyncio.gather runs all the tasks concurrently.
        if tasks:
            await asyncio.gather(*tasks)
            
                    
    async def handle_interaction_from_player(self, interaction:str, character_name:str):
        # --- Turn Validation ---
        active_char_name = self.chapter.get_active_character_name()
        if self.chapter.game_mode == GameMode.COMBAT and character_name != active_char_name:
            print(f"{ERROR_COLOR}Player {character_name} tried to act out of turn. It's {active_char_name}'s turn.{Colors.RESET}")
            # Optionally, send a private message to the player who tried to act
            # await self.announce_privately(EventBuilder.error("It's not your turn!"), q_for_player)
            return # Stop processing

        message = {
            "message_text": interaction,
            "sender_name": character_name
        }
        self.add_message_to_history(message)
        await self.announce(EventBuilder.player_message(interaction, character_name))
        
        await self.announce(EventBuilder.lock_all(self.chapter.game_mode.name))
        
        event_generator, was_action = await self.chapter.process_interaction(self.chapter.get_character_by_name(character_name), interaction)
        await self.announce_from_the_game(event_generator)     
        
        if was_action and self.chapter.game_mode == GameMode.COMBAT:
            self.chapter.move_to_next_turn()

        await self.announce_from_the_game(self.chapter.after_turn())
        print(f"{DEBUG_COLOR}Player {character_name} interaction processed{Colors.RESET}")
        self.turn_completed_event.set()

    async def make_system_announcement(self, alert_text):
        await self.announce(EventBuilder.alert(alert_text))
        message = {
            "message_text": alert_text,
            "sender_name": "system"
        }
        self.add_message_to_history(message)
        
    async def announce_from_the_game(self, generator):
        async for event in generator:
            print("Event received from the game:")
            print(event)
            
            # Handle specific events that require special processing
            if event.get("event") == "message" and event.get("sender") == "DM":
                message = {
                    "message_text": event["data"],
                    "sender_name": event["sender"]
                }
                self.add_message_to_history(message)
                await self.announce(event) # Also broadcast the message
                
            elif event.get("event") == "alert":
                # Use make_system_announcement to ensure it's also added to history
                await self.make_system_announcement(event["data"])
                
            # Default case: broadcast any other event to all listeners
            else:
                await self.announce(event)

    def add_message_to_history(self, message):
        """
        Adds a message to the message history and ensures the history does not exceed MAX_MESSAGE_HISTORY_LENGTH.
        """
        self.message_history.append(message)
        if len(self.message_history) > MAX_MESSAGE_HISTORY_LENGTH:
            self.message_history.pop(0)

    async def add_player_character(self, character: Character):
        """
        Adds a new player character to the game.
        """
        self.chapter.add_character(character)
        await self.announce(EventBuilder.player_joined(character.name, self.listener_names))

    def update_character(self, character_name: str, updates: dict):
        """
        Updates a character's attributes.
        """
        character = self.chapter.get_character_by_name(character_name)
        if character:
            for key, value in updates.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            return character
        return None

    async def delete_character(self, character_name: str):
        """
        Deletes a character from the game.
        """
        character = self.chapter.get_character_by_name(character_name)
        if character:
            self.chapter.characters.remove(character)
            await self.announce(EventBuilder.player_left(character.name, self.listener_names))
            return True
        return False
