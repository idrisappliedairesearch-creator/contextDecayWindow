import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.runners.full_context_runner import FullContextRunner


class TestFullContextRunnerBuildContext:

    def setup_method(self):
        self.runner = FullContextRunner("You are a helpful assistant.")

    def test_empty_history_returns_system_prompt(self):
        prompt, record = self.runner.build_context("Hello", 1)
        assert "You are a helpful assistant." in prompt
        assert "User: Hello" in prompt

    def test_prompt_contains_all_prior_turns(self):
        self.runner.on_turn_complete("What is 2+2?", "2+2 equals 4.", 1)
        self.runner.on_turn_complete("What is 3+3?", "3+3 equals 6.", 2)

        prompt, record = self.runner.build_context("What is 4+4?", 3)

        assert "What is 2+2?" in prompt
        assert "2+2 equals 4." in prompt
        assert "What is 3+3?" in prompt
        assert "3+3 equals 6." in prompt
        assert "User: What is 4+4?" in prompt

    def test_prompt_grows_each_turn(self):
        prompt1, record1 = self.runner.build_context("First message", 1)
        self.runner.on_turn_complete("First message", "First response", 1)

        prompt2, record2 = self.runner.build_context("Second message", 2)

        assert len(prompt2) > len(prompt1)
        assert record2.estimated_tokens > record1.estimated_tokens

    def test_token_estimate_increases_monotonically(self):
        token_estimates = []

        for i in range(1, 6):
            prompt, record = self.runner.build_context(f"Message turn {i}", i)
            token_estimates.append(record.estimated_tokens)
            self.runner.on_turn_complete(f"Message turn {i}", f"Response turn {i}", i)

        for i in range(1, len(token_estimates)):
            assert token_estimates[i] > token_estimates[i - 1]

    def test_turn_record_k_count_zero(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.k_count == 0

    def test_turn_record_n_count_zero(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.n_count == 0

    def test_turn_record_total_in_context_matches_history(self):
        self.runner.on_turn_complete("Q1", "A1", 1)
        self.runner.on_turn_complete("Q2", "A2", 2)

        _, record = self.runner.build_context("Q3", 3)
        assert record.total_in_context == 2

    def test_turn_record_topic_count_zero(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.topic_count == 0

    def test_turn_record_episode_count_matches_history(self):
        self.runner.on_turn_complete("Q1", "A1", 1)
        self.runner.on_turn_complete("Q2", "A2", 2)

        _, record = self.runner.build_context("Q3", 3)
        assert record.episode_count == 2

    def test_turn_record_condition_is_full_context(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.condition == "full_context"

    def test_turn_record_estimated_tokens_populated(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.estimated_tokens > 0
        assert isinstance(record.estimated_tokens, int)

    def test_turn_record_generation_fields_none(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.tokens_per_second is None
        assert record.time_to_first_token is None
        assert record.output_tokens is None
        assert record.assistant_message is None

    def test_compaction_fields_not_set(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.compaction_occurred is False
        assert record.compaction_turn is None
        assert record.history_tokens_before_compaction is None


class TestFullContextRunnerOnTurnComplete:

    def setup_method(self):
        self.runner = FullContextRunner("You are a helpful assistant.")

    def test_history_grows_after_turn(self):
        assert len(self.runner._history) == 0
        self.runner.on_turn_complete("Q", "A", 1)
        assert len(self.runner._history) == 1

    def test_history_entry_contains_correct_data(self):
        self.runner.on_turn_complete("What is X?", "X is Y.", 5)
        entry = self.runner._history[0]
        assert entry["turn_number"] == 5
        assert entry["user_message"] == "What is X?"
        assert entry["assistant_message"] == "X is Y."

    def test_multiple_turns_accumulate(self):
        for i in range(1, 4):
            self.runner.on_turn_complete(f"Q{i}", f"A{i}", i)
        assert len(self.runner._history) == 3


class TestFullContextRunnerHistoryTokenEstimate:

    def setup_method(self):
        self.runner = FullContextRunner("You are a helpful assistant.")

    def test_empty_history_returns_zero(self):
        assert self.runner.history_token_estimate == 0

    def test_increases_with_each_turn(self):
        estimates = []
        for i in range(1, 6):
            self.runner.on_turn_complete(f"Question number {i}?", f"Answer to question {i}.", i)
            estimates.append(self.runner.history_token_estimate)

        for i in range(1, len(estimates)):
            assert estimates[i] > estimates[i - 1]

    def test_positive_for_non_empty_history(self):
        self.runner.on_turn_complete("Hello", "Hi there!", 1)
        assert self.runner.history_token_estimate > 0
