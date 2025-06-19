from enum import Enum
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