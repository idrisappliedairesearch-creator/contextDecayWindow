import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.runners.compaction_runner import CompactionRunner, COMPACTION_THRESHOLD_TOKENS, COMPACTION_PROMPT_TEMPLATE
from src.memory.context_builder import estimate_tokens


class TestCompactionRunnerPreThreshold:

    def setup_method(self):
        self.runner = CompactionRunner("You are a helpful assistant.")

    def test_prompt_contains_full_history_before_threshold(self):
        self.runner.on_turn_complete("What is 2+2?", "2+2 equals 4.", 1)
        self.runner.on_turn_complete("What is 3+3?", "3+3 equals 6.", 2)

        prompt, record = self.runner.build_context("What is 4+4?", 3)

        assert "What is 2+2?" in prompt
        assert "2+2 equals 4." in prompt
        assert "What is 3+3?" in prompt
        assert "3+3 equals 6." in prompt

    def test_no_compaction_before_threshold(self):
        self.runner.on_turn_complete("Q1", "A1", 1)

        _, record = self.runner.build_context("Q2", 2)

        assert record.compaction_occurred is False
        assert record.compaction_turn is None
        assert record.history_tokens_before_compaction is None

    def test_condition_is_compaction(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.condition == "compaction"

    def test_k_and_n_count_zero(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.k_count == 0
        assert record.n_count == 0

    def test_topic_count_zero(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.topic_count == 0

    def test_summary_none_before_compaction(self):
        self.runner.on_turn_complete("Q1", "A1", 1)
        self.runner.build_context("Q2", 2)
        assert self.runner._summary is None

    def test_history_not_cleared_before_compaction(self):
        self.runner.on_turn_complete("Q1", "A1", 1)
        self.runner.build_context("Q2", 2)
        assert len(self.runner._history) == 1

    def test_compaction_count_zero_before_threshold(self):
        self.runner.on_turn_complete("Q1", "A1", 1)
        self.runner.build_context("Q2", 2)
        assert self.runner._compaction_count == 0

    def test_turn_record_fields_before_compaction(self):
        self.runner.on_turn_complete("Q1", "A1", 1)
        _, record = self.runner.build_context("Q2", 2)
        assert record.compaction_occurred is False
        assert record.compaction_turn is None
        assert record.history_tokens_before_compaction is None


def _long_message(chars: int) -> str:
    return "X" * chars


class TestCompactionRunnerFires:

    def setup_method(self):
        self.runner = CompactionRunner("You are a helpful assistant.")

    def _push_over_threshold(self):
        long = _long_message(6000)
        self.runner.on_turn_complete(long, long, 1)

    def test_compaction_fires_when_threshold_reached(self):
        self._push_over_threshold()
        assert self.runner.history_token_estimate >= COMPACTION_THRESHOLD_TOKENS

        _, record = self.runner.build_context("Next question", 2)

        assert record.compaction_occurred is True

    def test_compaction_turn_recorded(self):
        self._push_over_threshold()
        _, record = self.runner.build_context("Next question", 2)

        assert record.compaction_turn == 2

    def test_history_tokens_before_compaction_recorded(self):
        self._push_over_threshold()
        tokens_before = self.runner.history_token_estimate
        _, record = self.runner.build_context("Next question", 2)

        assert record.history_tokens_before_compaction == tokens_before
        assert record.history_tokens_before_compaction >= COMPACTION_THRESHOLD_TOKENS

    def test_history_cleared_after_compaction(self):
        self._push_over_threshold()
        self.runner.build_context("Next question", 2)

        assert len(self.runner._history) == 0

    def test_summary_set_after_compaction(self):
        self._push_over_threshold()
        self.runner.build_context("Next question", 2)

        assert self.runner._summary is not None

    def test_summary_is_placeholder(self):
        self._push_over_threshold()
        self.runner.build_context("Next question", 2)

        assert self.runner._summary == "[COMPACTION PENDING — inference not yet wired]"

    def test_compaction_count_increments(self):
        self._push_over_threshold()
        assert self.runner._compaction_count == 0
        self.runner.build_context("Next question", 2)
        assert self.runner._compaction_count == 1

    def test_last_compaction_turn_recorded(self):
        self._push_over_threshold()
        self.runner.build_context("Next question", 2)
        assert self.runner._last_compaction_turn == 2

    def test_turn_record_generation_fields_none(self):
        self._push_over_threshold()
        _, record = self.runner.build_context("Next question", 2)
        assert record.tokens_per_second is None
        assert record.time_to_first_token is None
        assert record.output_tokens is None


class TestCompactionRunnerPostCompaction:

    def setup_method(self):
        self.runner = CompactionRunner("You are a helpful assistant.")

    def _fire_compaction(self):
        long = _long_message(6000)
        self.runner.on_turn_complete(long, long, 1)
        self.runner.build_context("Trigger msg", 2)

    def test_post_compaction_prompt_contains_summary(self):
        self._fire_compaction()
        self.runner.on_turn_complete("Post compaction Q", "Post compaction A", 2)

        prompt, _ = self.runner.build_context("New question", 3)

        assert "[COMPACTION PENDING — inference not yet wired]" in prompt
        assert "--- CONVERSATION SUMMARY (prior history) ---" in prompt
        assert "--- END SUMMARY ---" in prompt

    def test_post_compaction_prompt_contains_recent_history(self):
        self._fire_compaction()
        self.runner.on_turn_complete("Post compaction Q", "Post compaction A", 2)

        prompt, record = self.runner.build_context("New question", 3)

        assert "Post compaction Q" in prompt
        assert "Post compaction A" in prompt
        assert "--- RECENT CONVERSATION ---" in prompt
        assert "--- END RECENT ---" in prompt

    def test_no_second_compaction_without_enough_history(self):
        self._fire_compaction()
        self.runner.on_turn_complete("Short Q", "Short A", 2)

        _, record = self.runner.build_context("Another Q", 3)

        assert record.compaction_occurred is False

    def test_total_in_context_reflects_post_compaction_history(self):
        self._fire_compaction()
        self.runner.on_turn_complete("Q", "A", 2)

        _, record = self.runner.build_context("New", 3)

        assert record.total_in_context == 1

    def test_episode_count_reflects_post_compaction_history(self):
        self._fire_compaction()
        self.runner.on_turn_complete("Q1", "A1", 2)
        self.runner.on_turn_complete("Q2", "A2", 3)

        _, record = self.runner.build_context("New", 4)

        assert record.episode_count == 2

    def test_history_token_estimate_includes_summary(self):
        self._fire_compaction()
        est = self.runner.history_token_estimate
        assert est > 0
        assert est == estimate_tokens(self.runner._summary)


class TestCompactionRunnerConstants:

    def test_threshold_constant_defined(self):
        assert COMPACTION_THRESHOLD_TOKENS == 3000

    def test_prompt_template_constant_defined(self):
        assert "CONVERSATION HISTORY:" in COMPACTION_PROMPT_TEMPLATE
        assert "{full_history_text}" in COMPACTION_PROMPT_TEMPLATE
        assert "Provide the summary now." in COMPACTION_PROMPT_TEMPLATE

    def test_prompt_template_not_modified_at_runtime(self):
        runner = CompactionRunner("System")
        original = COMPACTION_PROMPT_TEMPLATE
        long = _long_message(6000)
        runner.on_turn_complete(long, long, 1)
        runner.build_context("trigger", 2)
        assert COMPACTION_PROMPT_TEMPLATE == original


class TestCompactionRunnerOnTurnComplete:

    def setup_method(self):
        self.runner = CompactionRunner("You are a helpful assistant.")

    def test_history_grows(self):
        self.runner.on_turn_complete("Q", "A", 1)
        assert len(self.runner._history) == 1

    def test_entry_data_correct(self):
        self.runner.on_turn_complete("What?", "This.", 5)
        entry = self.runner._history[0]
        assert entry["turn_number"] == 5
        assert entry["user_message"] == "What?"
        assert entry["assistant_message"] == "This."

    def test_after_compaction_history_starts_fresh(self):
        long = _long_message(6000)
        self.runner.on_turn_complete(long, long, 1)
        self.runner.build_context("trigger", 2)

        assert len(self.runner._history) == 0
        self.runner.on_turn_complete("New Q", "New A", 2)
        assert len(self.runner._history) == 1
        assert self.runner._history[0]["user_message"] == "New Q"


class TestCompactionRunnerIntegration:

    def setup_method(self):
        self.runner = CompactionRunner("System prompt.")

    def test_full_turn_sequence(self):
        for i in range(1, 4):
            prompt, record = self.runner.build_context(f"Q{i}", i)
            assert record.compaction_occurred is False
            self.runner.on_turn_complete(f"Q{i}", f"A{i}", i)

        long = _long_message(6000)
        self.runner.on_turn_complete(long, long, 4)

        prompt, record = self.runner.build_context("Q5", 5)
        assert record.compaction_occurred is True
        assert record.compaction_turn == 5
        assert record.history_tokens_before_compaction is not None
        assert len(self.runner._history) == 0
        assert self.runner._summary is not None

        self.runner.on_turn_complete("Q5", "A5", 5)

        prompt, record = self.runner.build_context("Q6", 6)
        assert record.compaction_occurred is False
        assert "[COMPACTION PENDING — inference not yet wired]" in prompt
        assert "Q5" in prompt

    def test_runner_implements_base_interface(self):
        from src.runners.base_runner import BaseRunner
        assert isinstance(self.runner, BaseRunner)
        assert hasattr(self.runner, "condition")
        assert hasattr(self.runner, "build_context")
        assert hasattr(self.runner, "on_turn_complete")
        assert hasattr(self.runner, "history_token_estimate")
