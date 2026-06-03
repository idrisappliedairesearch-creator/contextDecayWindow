from abc import ABC, abstractmethod

from src.observability.turn_record import TurnRecord


class BaseRunner(ABC):

    condition: str

    @abstractmethod
    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        """
        Build the context prompt for this turn.
        Returns (constructed_prompt, partially_populated_TurnRecord).
        Generation fields on TurnRecord are left as None — populated by Sprint 008.
        """
        ...

    @abstractmethod
    def on_turn_complete(self, user_message: str, assistant_message: str, turn_number: int) -> None:
        """
        Called after generation completes.
        Updates internal state (history, summary, etc.) for the next turn.
        """
        ...

    @property
    @abstractmethod
    def history_token_estimate(self) -> int:
        """Current estimated token count of maintained history."""
        ...
