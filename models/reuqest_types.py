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
    changes: str = Field(description="Описание изменений, которые нужно внести в объект. Все изменения, которые поисаны в запросе обязяны быть записаны в этом поле. Изменения должны быть в формате инструкций для выполнения")
