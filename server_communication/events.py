from typing import List


class EventBuilder:
    @staticmethod
    def keepalive(data):
        """Create a keepalive event message.

        Args:
            data: Any data to be included in the keepalive message.

        Returns:
            dict: A keepalive event containing the provided data.
        """
        return {"data": data}

    @staticmethod
    def lock(allowed_players: List[str]):
        """Create a lock/unlock event message to control player turns.

        Args:
            allowed_players (List[str]): List of player names who are allowed to take actions.

        Returns:
            dict: A lock event containing the list of allowed players.
        """
        return {
            "event": "lock",
            "allowed_players": allowed_players
        }

    @staticmethod
    def player_message(data: str, sender: str):
        """Create a player message event.

        Args:
            data (str): The message content to be sent.
            sender (str): The name of the player sending the message.

        Returns:
            dict: A player message event containing the message data and sender information.
        """
        return {
            "event": "player_message",
            "data": data,
            "sender": sender
        }

    @staticmethod
    def state_update_required(event: str, total: int, current: int):
        """Create a state update event message.

        Args:
            event (str): The type of state update event.
            total (int): The total value for the state.
            current (int): The current value for the state.

        Returns:
            dict: A state update event containing the event type and state values.
        """
        return {
            "event": event,
            "total": total,
            "current": current
        }