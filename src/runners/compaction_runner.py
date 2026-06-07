from src.memory.context_builder import build_prompt, estimate_tokens
from src.observability.turn_record import TurnRecord
from src.runners.base_runner import BaseRunner
from src.inference.provider import InferenceProvider

COMPACTION_THRESHOLD_TOKENS = 3000

COMPACTION_PROMPT_TEMPLATE = (
    "You are summarizing a conversation history. Your summary will replace the full "
    "history and must preserve every key fact, decision, name, number, measurement, "
    "and behavioral rule that was established. Be precise — do not paraphrase "
    "specific values. Omit only conversational filler.\n\n"
    "CONVERSATION HISTORY:\n"
    "{full_history_text}\n\n"
    "Provide the summary now."
)


class CompactionRunner(BaseRunner):

    condition = "compaction"

    def __init__(self, system_prompt: str, inference_provider: InferenceProvider = None):
        self.system_prompt = system_prompt
        self._inference_provider = inference_provider
        self._history: list[dict] = []
        self._summary: str | None = None
        self._compaction_count: int = 0
        self._last_compaction_turn: int | None = None

    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        compaction_fired = False
        compaction_turn = None
        history_tokens_before = None

        if self.history_token_estimate >= COMPACTION_THRESHOLD_TOKENS:
            compaction_fired = True
            compaction_turn = turn_number
            history_tokens_before = self.history_token_estimate

            history_text = self._build_history_text()
            self._summary = self._run_compaction(history_text)
            self._history = []
            self._compaction_count += 1
            self._last_compaction_turn = turn_number

        parts = [self.system_prompt, ""]

        if self._summary is not None:
            parts.append("--- CONVERSATION SUMMARY (prior history) ---")
            parts.append(self._summary)
            parts.append("--- END SUMMARY ---")
            parts.append("")

        if self._history:
            parts.append("--- RECENT CONVERSATION ---")
            for entry in self._history:
                parts.append(f"[Turn {entry['turn_number']}]")
                parts.append(f"User: {entry['user_message']}")
                parts.append(f"Assistant: {entry['assistant_message']}")
            parts.append("--- END RECENT ---")
            parts.append("")

        parts.append(f"User: {user_message}")

        prompt = "\n".join(parts)

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
            compaction_occurred=compaction_fired,
            compaction_turn=compaction_turn,
            history_tokens_before_compaction=history_tokens_before,
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
        total = 0

        if self._summary is not None:
            total += estimate_tokens(self._summary)

        for entry in self._history:
            text = f"[Turn {entry['turn_number']}]\nUser: {entry['user_message']}\nAssistant: {entry['assistant_message']}\n"
            total += estimate_tokens(text)

        return total

    def _build_history_text(self) -> str:
        parts = []
        for entry in self._history:
            parts.append(f"[Turn {entry['turn_number']}]")
            parts.append(f"User: {entry['user_message']}")
            parts.append(f"Assistant: {entry['assistant_message']}")
        return "\n".join(parts)

    def _run_compaction(self, history_text: str) -> str:
        """Real model call — replaces Sprint 006 placeholder."""
        prompt = COMPACTION_PROMPT_TEMPLATE.format(full_history_text=history_text)
        result = self._inference_provider.complete(prompt, suppress_rule_detection=True)
        return result.assistant_message
