import json
import queue
from chapter_logic import ChapterLogicFight
from generator import ObjectGenerator
from models.schemas import Character
from server_communication import *
from server_communication.events import EventBuilder
from global_defines import *
import uuid
MAX_MESSAGE_HISTORY_LENGTH = 100
BUFFER_SIZE_FOR_QUEUE = 100
KEEPALIVE_INTERVAL_SECONDS = 2

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
        self.context = "Litelly hell"
        self.chapter = ChapterLogicFight(
            context = self.context,
            characters = [
                self.generator.generate(Character, "Антон сын другого Антона, который тоже сын Антона, вор, который не хочет воровать,только если это очень нужно команде и/или ему. у него средний рост, тощее телосложение. Всего имеет 40 hp. (игрок)", self.context, "Russian"),
                self.generator.generate(Character, "Яша Лава - ЛАвовый голем with full hp (50 hp) random inventory (non-player character)", self.context, "Russian"),
                # self.generator.generate(Character, "Яша Лужа - Водяной голем with full hp (50 hp) random inventory (non-player character)", self.context, "Russian"),
                self.generator.generate(Character, "ДЕД - боевой дворф with full hp (50 hp) random inventory (player character)", self.context, "Russian"),
                # self.generator.generate(Character, "Аполониус - боевой опёздол with full hp (50 hp) random inventory (player character)", self.context, "Russian"),
                # self.generator.generate(Character, "random monster with full hp (50 hp) and some magic spells (enemy NPC)", self.context, "Russian")
            ]
        )
        self.chapter.setup_fight()
        self.announce(EventBuilder.DM_message(self.chapter.scene.description)) # type: ignore
        message = {
            "message_text": self.chapter.scene.description, # type: ignore
            "sender_name": "DM"
        }
        self.add_message_to_history(message)
        self.allow_current_character_turn()
        # self.make_system_announcement(f"TST start message")
        
    def listen(self, sid : str, listener_char_name : str = "Unknown"):
        """
        Creates a new queue for a listener, adds it to the list,
        and yields messages from it. It also sends a keep-alive signal
        periodically to prevent connection timeouts.
        """
        q = queue.Queue(maxsize=BUFFER_SIZE_FOR_QUEUE)
        print(f"{INFO_COLOR}Listener for {listener_char_name} connected. {Colors.RESET}\n Total listeners {len(self.listeners)}")
        if listener_char_name in self.listener_names:
            self.announce_privately(EventBuilder.reject_connection(sid), q)
            print(f"{INFO_COLOR}Connection for {listener_char_name} {Colors.RED} refused. {Colors.RESET}\n Total listeners {len(self.listeners)}")
            return
        self.listeners.append(q)
        self.listener_names.append(listener_char_name)
        self.announce(EventBuilder.player_joined(listener_char_name, self.listener_names))
        try:
            self.announce_privately(EventBuilder.lock([self.chapter.get_active_character_name()]), q)
            while True:
                try:
                    msg = q.get(timeout=KEEPALIVE_INTERVAL_SECONDS)
                    yield msg
                    
                except queue.Empty:
                    # If the queue is empty after the timeout, it means no new
                    # messages arrived. We send a keep-alive signal.
                    # An SSE comment (line starting with ':') is a standard
                    # way to do this without triggering the client's 'message' event.
                    yield ": keepalive\n\n"
        finally:
            # If the client disconnects, remove their queue from the list.
            self.listeners.remove(q)
            self.listener_names.remove(listener_char_name)
            print(f"{INFO_COLOR}Listener for {listener_char_name} {Colors.RED} disconnected. {Colors.RESET}\n Total listeners {len(self.listeners)}")
            self.announce(EventBuilder.player_left(listener_char_name, self.listener_names))
    
    def announce_privately(self, msg, q : queue.Queue):
        """
        Puts a message into an active listener queue.
        \n
        EventBuilder structures hanler 
        """
        formatted_msg = f"data: {json.dumps(msg)}\n\n"
        try:
                # Try to put the message into the queue without blocking.
            q.put(formatted_msg, block=False)
        except queue.Full:
            # If full, remove the oldest message and put the new one.
            try:
                q.get(block=False)
            except queue.Empty:
                pass  # Should not happen, but just in case
            try:
                q.put(formatted_msg, block=False)
            except queue.Full:
                # If still full, drop the message and log
                print(f"Listener queue still full after discarding oldest. Dropping message: {msg}")
                
    def announce(self, msg):
        """
        Puts a message into all active listener queues.
        \n
        EventBuilder structures hanler 
        """
        # We need to format the message for SSE
        for q in self.listeners:
            self.announce_privately(msg, q)
            
                    
    def handle_interaction_from_player(self, interaction:str, character_name:str):
        message = {
            "message_text": interaction,
            "sender_name": character_name
        }
        self.add_message_to_history(message)
        # sending an event of message being recevied by server
        self.announce(EventBuilder.player_message(interaction, character_name))
        
        self.announce(EventBuilder.lock_all())
        
        player_to_game_interactions = self.chapter.process_interaction(self.chapter.get_character_by_name(character_name), interaction)
        self.announce_from_the_game(player_to_game_interactions)     
        self.allow_current_character_turn()

    def make_system_announcement(self, alert_text):
        self.announce(EventBuilder.alert(alert_text))
        message = {
            "message_text": alert_text,
            "sender_name": "system"
        }
        self.add_message_to_history(message)
        
    def announce_from_the_game(self, generator):
        for event  in generator:
            print("Event recieved from the game:")
            print(event)
            if event["event"] == "message" and event["sender"] == "DM":
                message = {
                    "message_text": event["data"],
                    "sender_name": event["sender"]
                }
                self.add_message_to_history(message)
            if event["event"] == "alert":
                self.make_system_announcement(event["data"])
            else:
                self.announce(event)

    def add_message_to_history(self, message):
        """
        Adds a message to the message history and ensures the history does not exceed MAX_MESSAGE_HISTORY_LENGTH.
        """
        self.message_history.append(message)
        if len(self.message_history) > MAX_MESSAGE_HISTORY_LENGTH:
            self.message_history.pop(0)
            
    def allow_current_character_turn(self):
        cur_character = self.chapter.get_active_character()
        if cur_character.is_alive and cur_character.is_player:
            pass
        elif not cur_character.is_alive:
            self.make_system_announcement(f"Player {cur_character.name} is unable to take turns...")
            self.chapter.move_to_next_turn()
        elif not cur_character.is_player:
            NPC_interaction = self.chapter.NPC_turn()
            self.announce_from_the_game(NPC_interaction)
        self.announce(EventBuilder.lock([self.chapter.get_active_character_name()]))