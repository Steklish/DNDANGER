from enum import Enum
from turtle import position
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ItemType(str, Enum):
    # Перечисление типов предметов в игре
    WEAPON = "Weapon"          # Оружие
    ARMOR = "Armor"           # Броня
    SHIELD = "Shield"         # Щит
    POTION = "Potion"        # Зелье
    SCROLL = "Scroll"        # Свиток
    WONDROUS_ITEM = "Wondrous Item"  # Чудесный предмет
    GEAR = "Gear"           # Снаряжение
    TRINKET = "Trinket"      # Безделушка
    TREASURE = "Treasure"    # Сокровище
    TOOL = "Tool"           # Инструмент
    QUEST_ITEM = "Quest Item"  # Квестовый предмет

class Rarity(str, Enum):
    # Перечисление редкости предметов
    COMMON = "Common"         # Обычный
    UNCOMMON = "Uncommon"     # Необычный
    RARE = "Rare"            # Редкий
    VERY_RARE = "Very Rare"   # Очень редкий
    LEGENDARY = "Legendary"   # Легендарный
    ARTIFACT = "Artifact"     # Артефакт
    UNIQUE = "Unique"        # Уникальный

class Item(BaseModel):
    # Класс для представления игровых предметов
    name: str = Field(description="Отображаемое название предмета.")
    description: str = Field(description="Описание внешнего вида предмета, его истории и функций.")
    item_type: ItemType = Field(description="Основная категория предмета.")
    weight: float = Field(default=0.0, ge=0, description="Вес предмета в фунтах.")
    value: int = Field(default=0, ge=0, description="Базовая стоимость предмета в золотых монетах.")
    quantity: int = Field(default=1, ge=1, description="Количество предметов в стопке.")
    rarity: Rarity = Field(default=Rarity.COMMON, description="Уровень редкости предмета.")
    is_magical: bool = Field(default=False, description="True, если предмет обладает магическими свойствами.")
    damage: Optional[str] = Field(default=None, description="Для оружия - бросок урона (например, '1d8' или '2d6').")
    damage_type: Optional[str] = Field(default=None, description="Для оружия - тип урона (например, 'Рубящий', 'Огонь').")
    armor_class: Optional[int] = Field(default=None, description="Для брони или щитов - базовый класс брони.")
    effect: Optional[str] = Field(default=None, description="Описание основного эффекта предмета при использовании.")
    properties: List[str] = Field(default_factory=list, description="Список особых свойств предмета.")

class Ability(BaseModel):
    # Класс для представления способностей
    name: str = Field(description="Название способности.")
    description: str = Field(description="Четкое описание действия способности.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Словарь для дополнительных деталей способности.")


class Character(BaseModel):
    """
    Pydantic модель, представляющая персонажа в игре (игрока или NPC).
    """
    name: str = Field(description="Полное имя или титул персонажа.")
    max_hp: int = Field(description="Максимальное количество очков здоровья персонажа.")
    current_hp: int = Field(description="Текущее количество очков здоровья персонажа.")
    is_alive: bool = Field(description="Может ли персонаж совершать действия, жив ли он")
    ac: int = Field(description="Класс брони персонажа, представляющий его защиту.")
    is_player: bool = Field(default=False, description="True, если это игровой персонаж.")
    conditions: List[str] = Field(default_factory=list, description="Набор текущих состояний, влияющих на персонажа.")
    inventory: List[Item] = Field(default_factory=list, description="Список предметов персонажа.")
    abilities: List[Ability] = Field(default_factory=list, description="Список особых способностей персонажа.")
    personality_history: str = Field(description="Подробное описание личности, предыстории и мотивации персонажа.")
    appearance: str = Field(description="Подробное описание внешности персонажа: черты лица, телосложение, волосы, глаза и т.д.")
    clothing_and_cosmetics: str = Field(description="Описание одежды, украшений, макияжа и других косметических деталей персонажа.")
    gender: str = Field(description="Пол персонажа. (Возможные пояснения, если пол не является стандартным или не существует для данного существа)")
    
    # --- Базовые характеристики D&D ---
    strength: int = Field(description="Сила (Strength). Измеряет физическую мощь, атлетизм.")
    dexterity: int = Field(description="Ловкость (Dexterity). Измеряет проворство, рефлексы и равновесие.")
    constitution: int = Field(description="Телосложение (Constitution). Измеряет выносливость, стойкость и жизненную силу.")
    intelligence: int = Field(description="Интеллект (Intelligence). Измеряет остроту ума и способность к логическому мышлению.")
    wisdom: int = Field(description="Мудрость (Wisdom). Отражает здравомыслие, интуицию и гармонию с окружающим миром.")
    charisma: int = Field(description="Харизма (Charisma). Измеряет силу личности, умение убеждать и личное обаяние.")
    
    position_in_scene: str = Field(description="A description of where the character is located within the scene")
    
class SceneObject(BaseModel):
    """
    Pydantic schema for a general object within a scene, like a door, tree, or statue.
    This is for background elements that characters might interact with.
    """
    name: str = Field(description="The short, identifiable name of the object (e.g., 'Large Oak Door', 'Ancient Weeping Willow').")
    description: str = Field(description="A detailed visual and sensory description of the object. What does it look, feel, or smell like?")
    size_description: str = Field(description="A descriptive account of the object's size and scale (e.g., 'roughly 3 feet wide and 7 feet tall', 'towers over the clearing').")
    position_in_scene: str = Field(description="A description of where the object is located within the scene (e.g., 'against the north wall', 'in the center of the room').")
    interactions: List[str] = Field(default_factory=list, description="A list of possible simple interactions with the object (e.g., ['Open', 'Close', 'Lock'], ['Examine', 'Touch']). Empty if not interactive.")

class Scene(BaseModel):
    """
    Pydantic schema for describing a game environment or location.
    """
    name: str = Field(description="A short, evocative title for the scene (e.g., 'The Abandoned Library', 'Goblin Ambush Site').")
    description: str = Field(description="A detailed overview of the scene, including lighting, atmosphere, sounds, and smells. This sets the mood.")
    size_description: str = Field(description="A description of the scene's overall dimensions and scale (e.g., 'a cramped 15x15 foot stone chamber', 'a vast, open field stretching to the horizon').")
    objects: List[SceneObject] = Field(default_factory=list, description="A list of all the notable objects present in the scene, each as a full SceneObject.")
    difficulty: int = Field(default=0, description="A rating of how challenging the scene is intended to be.")

class ScenePrompt(BaseModel):
    """
    Used to guide the generation of a new scene.
    """
    scene_name: str = Field(description="A short, evocative title for the scene (e.g., 'The Abandoned Library', 'Goblin Ambush Site').")
    scene_description: str = Field(description="A detailed overview of the scene, including lighting, atmosphere, sounds, and smells. This sets the mood.")
    difficulty: int = Field(default=0, description="A rating of how challenging the scene is intended to be.")

class DMQuestionAnswer(BaseModel):
    """
    Pydantic schema for the Dungeon Master's response to a player's question.
    """
    question_asked: str = Field(description="The original question the player asked.")
    answer: str = Field(description="The Dungeon Master's direct and informative answer to the question. This should be clear and concise.")
    extra_details: Optional[str] = Field(default=None, description="Any additional context, observations, or lore the DM chooses to provide. This can be used to add flavor or hint at other things.")
    
class GameState(BaseModel):
    """
    Represents the complete state of the game at any given moment.
    """
    current_scene: Scene = Field(description="The current scene where the action is taking place.")
    party: List[Character] = Field(description="A list of all characters in the player's party.")
    non_player_characters: List[Character] = Field(default_factory=list, description="A list of all non-player characters (NPCs) currently in the scene.")
    game_time: str = Field(default="Day 1, 09:00", description="The current in-game time.")
    turn_order: List[str] = Field(default_factory=list, description="An ordered list of character names indicating the turn order for combat or other sequential actions.")
    game_log: List[str] = Field(default_factory=list, description="A log of all major events and actions that have occurred.")
    current_story_arc: Optional[str] = Field(default=None, description="A brief description of the current overarching story or quest.")
    
class PlayerAction(BaseModel):
    """
    Represents a player's intended action.
    """
    character_name: str = Field(description="The name of the character performing the action.")
    action_description: str = Field(description="A clear and concise description of what the character wants to do.")
    
class DMQuestion(BaseModel):
    """
    Represents a player's question to the DM.
    """
    character_name: str = Field(description="The name of the character asking the question.")
    question: str = Field(description="The specific question the character is asking the DM.")
    
class StoryArc(BaseModel):
    """
    Pydantic schema for a story arc.
    """
    title: str = Field(description="The title of the story arc.")
    description: str = Field(description="A detailed description of the story arc.")
    scenes: List[Scene] = Field(default_factory=list, description="A list of all scenes in the story arc.")
    
class GameMode(BaseModel):
    """
    Pydantic schema for a game mode.
    """
    name: str = Field(description="The name of the game mode.")
    description: str = Field(description="A detailed description of the game mode.")
    
class RequestType(str, Enum):
    """
    The type of request the user is making.
    """
    ACTION = "action"
    QUESTION = "question"
    
class UserRequest(BaseModel):
    """
    The request the user is making.
    """
    request_type: RequestType = Field(description="The type of request the user is making.")
    text: str = Field(description="The text of the request.")
    
class StoryArcIdentifier(BaseModel):
    """
    Identifier for a story arc.
    """
    title: str = Field(description="The title of the story arc.")
    description: str = Field(description="A detailed description of the story arc.")

class ChangesToMake(BaseModel):
    """
    Represents changes to be made to an object. 
    """
    object_type: str = Field(description="Тип объекта, который нужно изменить. Варианты: 'character', 'scene'. Important: if for example a character took their sword and left it in the middle of the road it should be a change for the charactera and a cahnge for the scene as well.")
    object_name: str = Field(description="Имя объекта, который нужно изменить. Если тип объекта 'character', то это имя персонажа. Если тип объекта 'scene', то это название сцены.")
    changes: str = Field(description="Описание изменений, которые нужно внести в объект. Все изменения, которые поисаны в запросе обязяны быть записаны в этом поле. Изменения должны быть в формате инструкций для выполнения. Все изменения, которые возможно измерить числом должны быть описаны числом. Если информации для того, тчобы оценить числовое значение недостаточно, оченить проблизительно и записать числом.")

class ActionOutcome(BaseModel):
    """The result of a character's action, including the narrative and its mechanical effects."""
    narrative_description: str = Field(description="The rich, narrative description of the action's outcome, written for the player. Must use the required HTML tags for damage, healing, etc.")
    structural_changes: List[ChangesToMake] = Field(description="A list of specific, mechanical changes to characters or the scene resulting from the action.")
    is_legal: bool = Field(description="Whether the action performed was permissible within the rules or context of the game")
    turn_wasted: bool = Field(default=True, description="Indicates if the action consumed the character's turn. Asking a question typically does not, while attacking does.")