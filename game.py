import json
import queue

from h11 import Event
from sympy import im
from wasabi import msg
from chapter_logic import ChapterLogicFight
from generator import ObjectGenerator
from models.schemas import Character
from server_communication import *
from server_communication.events import EventBuilder

MAX_MESSAGE_HISTORY_LENGTH = 100
BUFFER_SIZE_FOR_QUEUE = 100
KEEPALIVE_INTERVAL_SECONDS = 20

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
        self.generator = ObjectGenerator()
        self.context = "A ground beneeth the grand tree"
        self.chapter = ChapterLogicFight(
            context = self.context,
            characters = [
                self.generator.generate(Character, "Борис Квадробер with full hp (50 hp) (player character) кот, которого ведьма превратила в человека (ведьма была его хозяйкой, от которой он позже сбежал), на нем него только тряпка вокруг члена и ничего больше. Среднее телосложение, черные кошачьи ушки. Нижние ноги скорее кошачь, чем человеческие. Густая шерсть по всему телу. Усы на лице. Хвост черный. У него гетерохромя с ожним глазом зеленым, а вторым синим. У него острые зубы и когти. Класс персонажа - плут(способности соответствующие). Любит рыбу и не любит молоко. Отзывается на кличку 'Барсик' - сокрощенно от 'Борис'.", self.context, "Russian"),
                self.generator.generate(Character, "Яша Лава with full hp (50 hp) (player character)", self.context, "Russian"),
                # self.generator.generate(Character, "random monster with full hp (50 hp) and some magic spells (enemy NPC)", self.context, "Russian")
            ]
        )
        self.chapter.setup_fight()
        
    def listen(self):
        """
        Creates a new queue for a listener, adds it to the list,
        and yields messages from it. It also sends a keep-alive signal
        periodically to prevent connection timeouts.
        """
        q = queue.Queue(maxsize=BUFFER_SIZE_FOR_QUEUE)
        self.listeners.append(q)
        try:
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
    
    
    def announce(self, msg):
        """
        Puts a message into all active listener queues.
        """
        # We need to format the message for SSE
        formatted_msg = f"data: {json.dumps(msg)}\n\n"
        for q in self.listeners:
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
                    
    def handle_interaction_from_player(self, interaction:str, character_name:str):
        message = {
            "message_text": interaction,
            "sender_name": character_name
        }
        self.add_message_to_history(message)
        # sending an event of message being recevied by server
        self.announce(EventBuilder.player_message(interaction, character_name))
        
        self.announce(EventBuilder.lock_all())
        
        for event  in self.chapter.process_interaction(self.chapter.get_character_by_name(character_name), interaction):
            print("Event recieved from the game:")
            print(event)
            # if "event" in event and event["event"] == "message":
            self.announce(event)
            if event["event"] == "message" and event["sender"] == "DM":
                message = {
                    "message_text": event["data"],
                    "sender_name": event["sender"]
                }
                self.add_message_to_history(message)     
        
        self.announce(EventBuilder.lock([self.chapter.get_active_character_name()]))
            
    

    def add_message_to_history(self, message):
        """
        Adds a message to the message history and ensures the history does not exceed MAX_MESSAGE_HISTORY_LENGTH.
        """
        self.message_history.append(message)
        if len(self.message_history) > MAX_MESSAGE_HISTORY_LENGTH:
            self.message_history.pop(0)