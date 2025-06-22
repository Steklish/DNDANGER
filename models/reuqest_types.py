from enum import Enum
from typing import List, Union
from pydantic import BaseModel, Field


class ClassifyInformationOrActionRequest(BaseModel):
    """
    TRUE, если запрос содержит информацию или взаимодействие с мастером подземелья,
    \nFALSE, если запрос содержит описание действия от лица персонажа в D&D.
    \n reasoning: Пояснение, почему пользователь запрашивает информацию или взаимодействует с мастером подземелья в D&D, либо описание действия от лица персонажа в D&D.
    \n decision: true/false
    
    """
    reasoning: str = Field(description="Пояснение, почему пользователь запрашивает информацию или взаимодействует с мастером подземелья в D&D, либо описание действия от лица персонажа в D&D.")
    decision: bool = Field(description="True, если пользователь запрашивает кикую-либо информацию, либо взаимодействует с мастером подземелья в D&D, что не влияет на игру и персонажа напрямую, например, просит напимнить ему, сколько стоил меч, который он видел в магалине несколько минут назад, иначе False, если запрос содержит описание действия от лица персонажа в D&D.")


class FightStateClassificationRequest(BaseModel):
    """
    ACTIVE - если бой продолжается,
    \nFINISHED - если бой завершен по любой причине.
    """
    reasoning: str = Field(description="Краткое пояснение о состоянии боя в D&D.")
    decision: str = Field(description="""
                          ACTIVE - если бой продолжается,
                          FINISHED - если бой завершен по любой причине. Причиной для завершения боя может быть смерть персонажа, победа над противником, бегство от противника, капитуляция одной из сторон, переговоры, или любое другое событие, которое приводит к окончанию боя.""")
    
class NextScene(BaseModel):
    """
    Модель для хранения информации о следующей сцене в D&D.
    \n scene_description: Описание следующей сцены в D&D.
    \n scene_difficulty: Сложность следующей сцены в D&D, от 0 до 20.
    """
    scene_description: str = Field(description="Описание следующей сцены в D&D.")
    scene_difficulty: int = Field(default=0, ge=0, description="Сложность следующей сцены в D&D, от 0 до 20.")

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
    
class GameMode(str, Enum):
    """Enumeration for the two primary game modes."""
    COMBAT = "COMBAT"
    NARRATIVE = "NARRATIVE"

class TurnAnalysisOutcome(BaseModel):
    """
    An analysis of the game state after a turn, recommending the
    appropriate mode for the subsequent turn.
    """
    recommended_mode: GameMode = Field(
        ...,
        description="The recommended game mode for the next turn (COMBAT or NARRATIVE)."
    )
    analysis_summary: str = Field(
        ...,
        description="A brief, clear justification for the recommended mode, analyzing the last action and current situation."
    )
    

class ProactiveChangeType(str, Enum):
    """
    Enumerates the types of proactive changes the world or story can undergo.
    """
    ADD_OBJECT = "ADD_OBJECT"
    REMOVE_OBJECT = "REMOVE_OBJECT"
    UPDATE_OBJECT = "UPDATE_OBJECT"
    CHANGE_SCENE = "CHANGE_SCENE"

class ProactiveChange(BaseModel):
    """
    Represents a single, proactive change to the game world, story, or its characters,
    triggered as a consequence of the player's actions or to advance the plot.
    """
    change_type: ProactiveChangeType = Field(
        ...,
        description="The type of change to be made."
    )
    description: str = Field(
        ...,
        description="A human-readable narrative summary of the change. E.g., 'The guard captain arrives, alerted by the noise.' or 'The magical barrier flickers and dies.'"
    )
    payload: Union[ChangesToMake, NextScene, str] = Field(
        ...,
        description="The detailed data for the change. For ADD/REMOVE/UPDATE, this is a ChangesToMake object or a simple name string. For CHANGE_SCENE, this is a NextScene object."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "change_type": "UPDATE_OBJECT",
                "description": "The old wooden bridge creaks ominously under the character's weight, looking like it might collapse.",
                "payload": {
                    "object_type": "scene",
                    "object_name": "Old Wooden Bridge",
                    "changes": "Update scene description to mention that the bridge is now unstable and dangerous."
                }
            }
        }

class NPCTurn(BaseModel):
    """
    Represents a complete turn for a single NPC, including their action and its outcome.
    """
    npc_name: str = Field(
        ...,
        description="The name of the NPC who is taking the action."
    )
    action_outcome: ActionOutcome = Field(
        ...,
        description="The full outcome of the NPC's action, structured identically to a player's action outcome."
    )

class NarrativeTurnAnalysis(BaseModel):
    """
    Analyzes the aftermath of a player's action in Narrative mode, determining
    consequential NPC actions and world changes.
    """
    reasoning: str = Field(
        ...,
        description="A brief summary explaining why the NPCs and world are reacting (or not reacting) to the player's last action."
    )
    npc_actions: List[NPCTurn] = Field(
        default_factory=list,
        description="A list of actions that NPCs take in direct response to the player's turn. Leave empty if no NPCs react."
    )
    proactive_world_changes: List[ProactiveChange] = Field(
        default_factory=list,
        description="A list of changes to the story or environment. Used for plot progression or delayed consequences. Leave empty if the world state is static."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "reasoning": "The player successfully intimidated the merchant. The merchant is now scared and will offer a discount, while his bodyguard becomes alert.",
                "npc_actions": [
                    {
                        "npc_name": "Balor the Merchant",
                        "action_outcome": {
                            "narrative_description": "Балор бледнеет и торопливо говорит: 'Хорошо, хорошо, не надо горячиться! Для вас... специальная цена! Скидка! Только не причиняйте вреда!'",
                            "structural_changes": [],
                            "is_legal": True
                        }
                    }
                ],
                "proactive_world_changes": [
                    {
                        "change_type": "UPDATE_OBJECT",
                        "description": "The merchant's bodyguard, previously relaxed, now stands straighter and places a hand on the hilt of his sword.",
                        "payload": {
                           "object_type": "character",
                           "object_name": "Bodyguard",
                           "changes": "Update character's state from 'relaxed' to 'alert and hostile'."
                        }
                    }
                ]
            }
        }