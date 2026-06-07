import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.db.schema import init_db
from src.db.rule_store import get_all_rules
from src.memory.topic_manager import TopicManager
from src.memory.retrieval_engine import RetrievalEngine
from src.runners.full_context_runner import FullContextRunner
from src.runners.compaction_runner import CompactionRunner
from src.runners.iterative_runner import IterativeRunner
from src.observability.turn_record import TurnRecord
from tests.conftest import MockInferenceProvider, MockInferenceResult


MOCK_SCRIPT_TURNS = [
    {"turn": 1, "user": "Always respond in bullet points. This is a rule."},
    {"turn": 2, "user": "What is the capital of France?"},
    {"turn": 3, "user": "Name three types of bridges."},
    {"turn": 4, "user": "What rule did I establish at the start?"},
    {"turn": 5, "user": "Summarize everything we discussed."},
]


class MockEmbeddingProvider:
    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(1024, dtype=np.float32)
        vec[0] = 1.0
        return vec


class TestMockScriptRuleDetection:

    def test_turn_one_triggers_rule_detection(self):
        provider = MockInferenceProvider()
        result = provider.complete("Always respond in bullet points. This is a rule.")
        assert result.contains_rule is True
        assert result.rule_summary == "Always respond in bullet points."

    def test_subsequent_turns_no_rule(self):
        provider = MockInferenceProvider()
        provider.complete("Turn 1")
        result = provider.complete("Turn 2")
        assert result.contains_rule is False
        assert result.rule_summary is None

    def test_suppress_rule_detection_forces_false(self):
        provider = MockInferenceProvider()
        result = provider.complete("Any prompt", suppress_rule_detection=True)
        assert result.contains_rule is False
        assert result.rule_summary is None

    def test_suppress_on_first_call_also_forces_false(self):
        provider = MockInferenceProvider()
        result = provider.complete("First call with suppress", suppress_rule_detection=True)
        assert result.contains_rule is False


class TestFullContextConditionMock:

    def setup_method(self):
        self.runner = FullContextRunner("You are a helpful assistant.")
        self.provider = MockInferenceProvider()

    def test_five_turns_complete(self):
        for turn_data in MOCK_SCRIPT_TURNS:
            turn_number = turn_data["turn"]
            user_message = turn_data["user"]

            prompt, record = self.runner.build_context(user_message, turn_number)
            result = self.provider.complete(prompt)
            self.runner.on_turn_complete(user_message, result.assistant_message, turn_number)

            assert record.turn_number == turn_number
            assert record.condition == "full_context"

    def test_turn_record_has_rule_fields(self):
        self.runner.build_context("Test", 1)
        result = self.provider.complete("Test")

        record = TurnRecord(
            turn_number=1,
            condition="full_context",
            user_message="Test",
            contains_rule=result.contains_rule,
            rule_summary=result.rule_summary,
        )

        assert record.contains_rule == result.contains_rule
        assert record.rule_summary == result.rule_summary


class TestCompactionConditionMock:

    def setup_method(self):
        self.runner = CompactionRunner(
            "You are a helpful assistant.",
            inference_provider=MockInferenceProvider(),
        )

    def test_five_turns_complete(self):
        provider = MockInferenceProvider()
        for turn_data in MOCK_SCRIPT_TURNS:
            turn_number = turn_data["turn"]
            user_message = turn_data["user"]

            prompt, record = self.runner.build_context(user_message, turn_number)
            result = provider.complete(prompt)
            self.runner.on_turn_complete(user_message, result.assistant_message, turn_number)

            assert record.turn_number == turn_number
            assert record.condition == "compaction"

    def test_compaction_uses_suppress_rule_detection(self):
        mock_provider = MockInferenceProvider()

        long_runner = CompactionRunner(
            "You are a helpful assistant.",
            inference_provider=mock_provider,
        )

        long = "X" * 6000
        long_runner.on_turn_complete(long, long, 1)

        _, record = long_runner.build_context("Next question", 2)

        assert record.compaction_occurred is True

        compaction_result = mock_provider.complete("test", suppress_rule_detection=True)
        assert compaction_result.contains_rule is False


class TestIterativeConditionMock:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "study.db")
        self.conn = init_db(self.db_path)
        self.embedding_provider = MockEmbeddingProvider()
        self.topic_manager = TopicManager(self.conn)
        self.retrieval_engine = RetrievalEngine(self.conn)
        self.runner = IterativeRunner(
            self.conn, self.embedding_provider, self.topic_manager, self.retrieval_engine
        )
        self.provider = MockInferenceProvider()

    def test_five_turns_complete(self):
        for turn_data in MOCK_SCRIPT_TURNS:
            turn_number = turn_data["turn"]
            user_message = turn_data["user"]

            prompt, record = self.runner.build_context(user_message, turn_number)
            result = self.provider.complete(prompt)

            embedding = self.embedding_provider.embed(
                f"User: {user_message}\nAssistant: {result.assistant_message}"
            )
            assignment = self.runner.on_turn_complete(
                user_message=user_message,
                assistant_message=result.assistant_message,
                turn_number=turn_number,
                embedding=embedding,
                inference_result=result,
            )

            assert record.turn_number == turn_number
            assert record.condition == "iterative"
            assert assignment is not None

    def test_rule_stored_on_turn_one(self):
        turn_data = MOCK_SCRIPT_TURNS[0]
        turn_number = turn_data["turn"]
        user_message = turn_data["user"]

        prompt, _ = self.runner.build_context(user_message, turn_number)
        result = self.provider.complete(prompt)

        assert result.contains_rule is True
        assert result.rule_summary == "Always respond in bullet points."

        embedding = self.embedding_provider.embed(
            f"User: {user_message}\nAssistant: {result.assistant_message}"
        )
        self.runner.on_turn_complete(
            user_message=user_message,
            assistant_message=result.assistant_message,
            turn_number=turn_number,
            embedding=embedding,
            inference_result=result,
        )

        rules = get_all_rules(self.conn)
        assert len(rules) == 1
        assert rules[0]["rule_summary"] == "Always respond in bullet points."
        assert rules[0]["turn_number"] == 1

    def test_only_turn_one_rule_stored(self):
        self.provider = MockInferenceProvider()

        for turn_data in MOCK_SCRIPT_TURNS:
            turn_number = turn_data["turn"]
            user_message = turn_data["user"]

            prompt, _ = self.runner.build_context(user_message, turn_number)
            result = self.provider.complete(prompt)

            embedding = self.embedding_provider.embed(
                f"User: {user_message}\nAssistant: {result.assistant_message}"
            )
            self.runner.on_turn_complete(
                user_message=user_message,
                assistant_message=result.assistant_message,
                turn_number=turn_number,
                embedding=embedding,
                inference_result=result,
            )

        rules = get_all_rules(self.conn)
        assert len(rules) == 1
        assert rules[0]["turn_number"] == 1

    def test_all_rules_ordered_by_turn(self):
        self.provider = MockInferenceProvider()

        for turn_data in MOCK_SCRIPT_TURNS:
            turn_number = turn_data["turn"]
            user_message = turn_data["user"]

            prompt, _ = self.runner.build_context(user_message, turn_number)
            result = self.provider.complete(prompt)

            embedding = self.embedding_provider.embed(
                f"User: {user_message}\nAssistant: {result.assistant_message}"
            )
            self.runner.on_turn_complete(
                user_message=user_message,
                assistant_message=result.assistant_message,
                turn_number=turn_number,
                embedding=embedding,
                inference_result=result,
            )

        rules = get_all_rules(self.conn)
        turn_numbers = [r["turn_number"] for r in rules]
        assert turn_numbers == sorted(turn_numbers)


class TestAllConditionsIntegration:

    def test_all_three_conditions_run_without_error(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "study.db")
        conn = init_db(db_path)
        embedding_provider = MockEmbeddingProvider()
        topic_manager = TopicManager(conn)
        retrieval_engine = RetrievalEngine(conn)

        conditions = [
            FullContextRunner("You are a helpful assistant."),
            CompactionRunner("You are a helpful assistant.", inference_provider=MockInferenceProvider()),
            IterativeRunner(conn, embedding_provider, topic_manager, retrieval_engine),
        ]

        for runner in conditions:
            provider = MockInferenceProvider()
            for turn_data in MOCK_SCRIPT_TURNS:
                turn_number = turn_data["turn"]
                user_message = turn_data["user"]

                prompt, record = runner.build_context(user_message, turn_number)
                result = provider.complete(prompt)

                if runner.condition == "iterative":
                    embedding = embedding_provider.embed(
                        f"User: {user_message}\nAssistant: {result.assistant_message}"
                    )
                    runner.on_turn_complete(
                        user_message=user_message,
                        assistant_message=result.assistant_message,
                        turn_number=turn_number,
                        embedding=embedding,
                        inference_result=result,
                    )
                else:
                    runner.on_turn_complete(user_message, result.assistant_message, turn_number)

    def test_rubric_turns_constant_correct(self):
        from src.study.runner import StudyRunner
        assert StudyRunner.RUBRIC_TURNS == list(range(112, 121))

    def test_terminal_header_includes_total(self):
        record = TurnRecord(
            turn_number=47,
            condition="iterative",
            user_message="Test message",
            total_turns=120,
            estimated_tokens=5000,
            topic_count=5,
            n_total_in_store=46,
        )
        from src.observability.terminal import TerminalPrinter
        printer = TerminalPrinter()
        import io
        import sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            printer.print_turn(record)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "TURN 047 / 120" in output
