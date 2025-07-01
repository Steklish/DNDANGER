from enum import Enum
from typing import List, Union
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from .game_modes import GameMode
from .schemas import ChangesToMake, ActionOutcome

class GameModeDecision(BaseModel):
    new_mode: GameMode = Field(description="The recommended game mode ('NARRATIVE' or 'COMBAT').")
    reasoning: str = Field(description="A brief explanation for why the mode is being changed.")

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
    ADD_CHARACTER = "ADD_CHARACTER"
    REMOVE_CHARACTER = "REMOVE_CHARACTER"
    UPDATE_CHARACTER = "UPDATE_CHARACTER"
    
    ADD_OBJECT = "ADD_OBJECT"
    REMOVE_OBJECT = "REMOVE_OBJECT"
    UPDATE_OBJECT = "UPDATE_OBJECT"
    
    CHANGE_SCENE = "CHANGE_SCENE"
    UPDATE_SCENE = "UPDATE_SCENE"

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
        
class TurnList(BaseModel):
    turn_list: List[str] = Field(
        description="List of the names of characters participating in the scene. In logical order (in order they should act in a turn based game) based on provided context"
    )
    reasoning: str = Field(
        description="A brief explanation of the order of characters in the turn list. Should be based on the context provided."
    )
    

class StoryProgressionCheck(BaseModel):
    conditions_met: bool = Field(description="Set to true if the player's actions have met the completion conditions, otherwise false.")
    reasoning: str = Field(description="A brief explanation of why the conditions were or were not met, based on the provided context.")