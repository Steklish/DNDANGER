import json
from math import e
from multiprocessing import allow_connection_pickling
from re import A
from traceback import print_tb
from chapter_logic import ChapterLogicFight
from generator import ObjectGenerator
from models.reuqest_types import GameMode
from models.schemas import Character
from server_communication import *
from server_communication.events import EventBuilder
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
        self.context = "Чаща леса. Полночь"
        self.chapter = ChapterLogicFight(
            context = self.context,
            characters = [
                self.generator.generate(Character, "Энт с HP по 30, урон корнями и виноградными плетями. (NPC)", self.context, "Russian"),
                # self.generator.generate(Character, "Призрак (какой-нибудь) с HP по 30, урон корнями и виноградными плетями. (NPC)", self.context, "Russian"),
                # self.generator.generate(Character, "странник из света (CR 1, кастует простые иллюзии, ослепление) ➤ Угрозы умеренные, но запоминающиеся. (enemy NPC)", self.context, "Russian"),
                # self.generator.generate(Character, "Яша Лава - ЛАвовый голем with full hp (10 hp) random inventory (non-player character)", self.context, "Russian"),
                # self.generator.generate(Character, "Яша Лужа - Водяной голем with full hp (50 hp) random inventory (non-player character)", self.context, "Russian"),
                self.generator.generate(Character, "Игорь - боевой дворф with full hp (50 hp) random inventory (player character)", self.context, "Russian"),
                self.generator.generate(Character, "Олег - маг с кучей заклинаний with full hp (50 hp) random inventory (player character)", self.context, "Russian"),
            ]
        )
        self.chapter.game_mode = GameMode.NARRATIVE
        self.announce(EventBuilder.DM_message(self.chapter.scene.description)) # type: ignore
        message = {
            "message_text": self.chapter.scene.description, # type: ignore
            "sender_name": "DM"
        }
        self.add_message_to_history(message)
        
        
    @classmethod
    async def create(cls):
        """
        Async factory for Game objects.
        """
        self = cls()  # Synchronous __init__
        return self
    
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
        message = {
            "message_text": interaction,
            "sender_name": character_name
        }
        self.add_message_to_history(message)
        await self.announce(EventBuilder.player_message(interaction, character_name))
        
        await self.announce(EventBuilder.lock_all(self.chapter.game_mode.name))
        
        player_to_game_interactions = self.chapter.process_interaction(self.chapter.get_character_by_name(character_name), interaction)
        await self.announce_from_the_game(player_to_game_interactions)     
        print(f"{DEBUG_COLOR}Player {character_name} interaction processed{Colors.RESET}")
        await self.allow_current_character_turn()

    async def make_system_announcement(self, alert_text):
        await self.announce(EventBuilder.alert(alert_text))
        message = {
            "message_text": alert_text,
            "sender_name": "system"
        }
        self.add_message_to_history(message)
        
    async def announce_from_the_game(self, generator):
        async for event  in generator:
            print("Event recieved from the game:")
            print(event)
            if event["event"] == "message" and (event["sender"] == "DM"):
                message = {
                    "message_text": event["data"],
                    "sender_name": event["sender"]
                }
                self.add_message_to_history(message)
            if event["event"] == "alert":
                await self.make_system_announcement(event["data"])
            # elif event["event"] == "end_of_turn":
            #     print("End of turn event received, allowing next character turn...")
            #     await self.allow_current_character_turn()
            else:
                await self.announce(event)

    def add_message_to_history(self, message):
        """
        Adds a message to the message history and ensures the history does not exceed MAX_MESSAGE_HISTORY_LENGTH.
        """
        self.message_history.append(message)
        if len(self.message_history) > MAX_MESSAGE_HISTORY_LENGTH:
            self.message_history.pop(0)
            
    async def allow_current_character_turn(self):
        print("allowing some turn...")
        print(f"Current game mode: {self.chapter.game_mode}, current character: {self.chapter.get_active_character_name()}")
        # Loop until a living player is found or all NPCs/Dead are skipped
        if self.chapter.game_mode == GameMode.COMBAT:
            cur_character = self.chapter.get_active_character()
            if cur_character.is_alive and cur_character.is_player:
                print("Allowing player turn")
                await self.announce(EventBuilder.lock([cur_character.name], game_mode=self.chapter.game_mode.name))
                return
            elif not cur_character.is_alive:
                await self.make_system_announcement(f"Player {cur_character.name} is unable to take turns...")
                self.chapter.move_to_next_turn()
                await self.allow_current_character_turn()
            elif not cur_character.is_player:
                print("Allowing NPC turn")
                NPC_interaction = self.chapter.NPC_turn()
                await self.announce_from_the_game(NPC_interaction)
                self.chapter.move_to_next_turn()
            await self.announce(EventBuilder.lock([self.chapter.get_active_character_name()], game_mode=self.chapter.game_mode.name))
        else:
            print("Allowing narrative turn (allowing everyone to play)")
            allowed_players = [char.name for char in self.chapter.characters if char.is_alive]
            event = EventBuilder.lock(allowed_players, game_mode=GameMode.NARRATIVE.name)
            await self.announce(event)
            
                