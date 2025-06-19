from typing import List


class EventBuilder:

    @staticmethod
    def user_intent_processed(decision:str):
        """
        decision (действие/информация)
        \n сообщает, какой тип запроса обрабатывается
        """
        return {
            "event": "decision",
            "decision": decision
        }


    @staticmethod
    def lock(allowed_players: List[str]):
        """Создает событие блокировки/разблокировки для контроля очередности ходов игроков.

        Args:
            allowed_players (List[str]): Список имен игроков, которым разрешено выполнять действия.

        Returns:
            dict: Событие блокировки, содержащее список разрешенных игроков.
        """
        return {
            "event": "lock",
            "allowed_players": allowed_players
        }
        
    @staticmethod
    def lock_all():
        """
        Создает блокировку.

        Returns:
            dict: Событие блокировки, содержащее список разрешенных игроков.
        """
        return {
            "event": "lock",
            "allowed_players": []
        }

    @staticmethod
    def player_message(data: str, sender: str):
        """Создает событие сообщения от игрока.

        Args:
            data (str): Содержимое отправляемого сообщения.
            sender (str): Имя игрока, отправляющего сообщение.

        Returns:
            dict: Событие сообщения от игрока, содержащее данные сообщения и информацию об отправителе.
        """
        return {
            "event": "message",
            "data": data,
            "sender": sender
        }

    @staticmethod
    def DM_message(data: str):
        """Создает событие сообщения от DM (Мастера).

        Args:
            data (str): Содержимое отправляемого сообщения.

        Returns:
            dict: Событие сообщения от DM, содержащее данные сообщения и информацию об отправителе.
        """
        return {
            "event": "message",
            "data": data,
            "sender": "DM"
        }


    @staticmethod
    def state_update_required(update: str, total: int, current: int):
        """Создает событие-сообщение об обновлении состояния.

        Args:

            total (int): Общее значение для состояния.
            current (int): Текущее значение для состояния.

        Returns:
            dict: Событие обновления состояния, содержащее тип события и значения состояния.
        """
        return {
            "event": "update",
            "object" : update,
            "total": total,
            "current": current
        }
        
    @staticmethod
    def alert(data: str):
        """Создает событие сообщения от сервера.

        Args:
            data (str): Содержимое отправляемого сообщения.
        """
        return {
            "event": "alert",
            "data": data,
            "sender": "server"
        }