from src.memory.context_builder import build_prompt, estimate_tokens
from src.observability.turn_record import TurnRecord
from src.runners.base_runner import BaseRunner


class FullContextRunner(BaseRunner):

    condition = "full_context"

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self._history: list[dict] = []

    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        episodes = [
            {
                "turn_number": entry["turn_number"],
                "user_message": entry["user_message"],
                "assistant_message": entry["assistant_message"],
            }
            for entry in self._history
        ]

        prompt = build_prompt(episodes, self.system_prompt)

        prompt += f"\n\nUser: {user_message}"

        record = TurnRecord(
            turn_number=turn_number,
            condition=self.condition,
            user_message=user_message,
            k_count=0,
            n_count=0,
            total_in_context=len(self._history),
            topic_count=0,
            episode_count=len(self._history),
            estimated_tokens=estimate_tokens(prompt),
            constructed_prompt=prompt,
        )

        return (prompt, record)

    def on_turn_complete(self, user_message: str, assistant_message: str, turn_number: int) -> None:
        self._history.append({
            "turn_number": turn_number,
            "user_message": user_message,
            "assistant_message": assistant_message,
        })

    @property
    def history_token_estimate(self) -> int:
        if not self._history:
            return 0

        history_text = ""
        for entry in self._history:
            history_text += f"[Turn {entry['turn_number']}]\nUser: {entry['user_message']}\nAssistant: {entry['assistant_message']}\n"

        return estimate_tokens(history_text)
