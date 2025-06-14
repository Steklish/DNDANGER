# schemas.py (Обновленный класс Character)

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Set, Dict, Any, Optional

# --- Перечисления и другие классы (Item, Ability) остаются без изменений ---
# (Они включены здесь для полноты файла)

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

# --- МОДИФИЦИРОВАННЫЙ КЛАСС ПЕРСОНАЖА ---

class Character(BaseModel):
    """
    Pydantic модель, представляющая персонажа в игре (игрока или NPC).
    """
    name: str = Field(description="Полное имя или титул персонажа.")
    max_hp: int = Field(description="Максимальное количество очков здоровья персонажа.")
    current_hp: int = Field(description="Текущее количество очков здоровья персонажа.")
    ac: int = Field(description="Класс брони персонажа, представляющий его защиту.")
    is_player: bool = Field(default=False, description="True, если это игровой персонаж.")
    
    conditions: Set[str] = Field(default_factory=set, description="Набор текущих состояний, влияющих на персонажа.")
    
    # === ЭТО ИЗМЕНЕННАЯ СТРОКА ===
    inventory: List[Item] = Field(default_factory=list, description="Список предметов персонажа.")
    
    abilities: List[Ability] = Field(default_factory=list, description="Список особых способностей персонажа.")
    
    personality_history: str = Field(description="Подробное описание личности, предыстории и мотивации персонажа.")