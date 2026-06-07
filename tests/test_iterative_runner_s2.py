import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.db.schema import init_db
from src.db.rule_store import get_all_rules
from src.memory.topic_manager import TopicManager
from src.memory.retrieval_engine import RetrievalEngine
from src.runners.iterative_runner import IterativeRunner
from src.inference.provider import InferenceResult
from tests.conftest import MockInferenceResult


class MockEmbeddingProvider:
    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(1024, dtype=np.float32)
        vec[0] = 1.0
        return vec


class TestIterativeRunnerRuleStoreIntegration:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.conn = init_db(self.db_path)
        self.embedding_provider = MockEmbeddingProvider()
        self.topic_manager = TopicManager(self.conn)
        self.retrieval_engine = RetrievalEngine(self.conn)
        self.runner = IterativeRunner(
            self.conn, self.embedding_provider, self.topic_manager, self.retrieval_engine
        )

    def test_store_rule_called_when_contains_rule_true(self):
        embedding = self.embedding_provider.embed("User: Rule message\nAssistant: Acknowledged")
        inference_result = MockInferenceResult(
            assistant_message="Acknowledged",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=1,
            contains_rule=True,
            rule_summary="Always respond in bullet points.",
        )

        result = self.runner.on_turn_complete(
            "Always respond in bullet points.",
            "Acknowledged",
            1,
            embedding,
            inference_result,
        )

        assert result is not None
        rules = get_all_rules(self.conn)
        assert len(rules) == 1
        assert rules[0]["rule_summary"] == "Always respond in bullet points."
        assert rules[0]["turn_number"] == 1

    def test_store_rule_not_called_when_contains_rule_false(self):
        embedding = self.embedding_provider.embed("User: Normal message\nAssistant: Response")
        inference_result = MockInferenceResult(
            assistant_message="Response",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=1,
            contains_rule=False,
            rule_summary=None,
        )

        self.runner.on_turn_complete(
            "Normal message",
            "Response",
            2,
            embedding,
            inference_result,
        )

        rules = get_all_rules(self.conn)
        assert len(rules) == 0

    def test_store_rule_not_called_when_no_inference_result(self):
        embedding = self.embedding_provider.embed("User: Normal message\nAssistant: Response")

        result = self.runner.on_turn_complete(
            "Normal message",
            "Response",
            3,
            embedding,
            None,
        )

        assert result is not None
        rules = get_all_rules(self.conn)
        assert len(rules) == 0

    def test_multiple_rules_stored_correctly(self):
        for i, (user_msg, rule_summary) in enumerate([
            ("Always respond in bullet points.", "Always respond in bullet points."),
            ("Use formal tone.", "Use formal tone in all responses."),
        ], start=1):
            embedding = self.embedding_provider.embed(f"User: {user_msg}\nAssistant: OK")
            inference_result = MockInferenceResult(
                assistant_message="OK",
                tokens_per_second=50.0,
                time_to_first_token=0.02,
                output_tokens=1,
                contains_rule=True,
                rule_summary=rule_summary,
            )
            self.runner.on_turn_complete(
                user_msg,
                "OK",
                i,
                embedding,
                inference_result,
            )

        rules = get_all_rules(self.conn)
        assert len(rules) == 2
        assert rules[0]["turn_number"] == 1
        assert rules[1]["turn_number"] == 2
        assert rules[0]["rule_summary"] == "Always respond in bullet points."
        assert rules[1]["rule_summary"] == "Use formal tone in all responses."

    def test_mixed_rule_and_non_rule_turns(self):
        turns = [
            ("Always respond in bullet points.", True, "Always respond in bullet points."),
            ("What is 2+2?", False, None),
            ("Use markdown headings.", True, "Use markdown headings in responses."),
            ("Tell me a joke.", False, None),
        ]

        for i, (user_msg, contains_rule, rule_summary) in enumerate(turns, start=1):
            embedding = self.embedding_provider.embed(f"User: {user_msg}\nAssistant: OK")
            inference_result = MockInferenceResult(
                assistant_message="OK",
                tokens_per_second=50.0,
                time_to_first_token=0.02,
                output_tokens=1,
                contains_rule=contains_rule,
                rule_summary=rule_summary,
            )
            self.runner.on_turn_complete(
                user_msg,
                "OK",
                i,
                embedding,
                inference_result,
            )

        rules = get_all_rules(self.conn)
        assert len(rules) == 2
        assert rules[0]["turn_number"] == 1
        assert rules[1]["turn_number"] == 3

    def test_rule_not_stored_when_contains_rule_true_but_no_summary(self):
        embedding = self.embedding_provider.embed("User: Rule message\nAssistant: OK")
        inference_result = MockInferenceResult(
            assistant_message="OK",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=1,
            contains_rule=True,
            rule_summary=None,
        )

        self.runner.on_turn_complete(
            "Rule message",
            "OK",
            1,
            embedding,
            inference_result,
        )

        rules = get_all_rules(self.conn)
        assert len(rules) == 0

    def test_rule_episode_id_matches_stored_episode(self):
        from src.db.episode import get_episode_by_id

        embedding = self.embedding_provider.embed("User: Rule message\nAssistant: OK")
        inference_result = MockInferenceResult(
            assistant_message="OK",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=1,
            contains_rule=True,
            rule_summary="Test rule.",
        )

        self.runner.on_turn_complete(
            "Rule message",
            "OK",
            1,
            embedding,
            inference_result,
        )

        rules = get_all_rules(self.conn)
        assert len(rules) == 1
        episode_id = rules[0]["episode_id"]
        episode = get_episode_by_id(self.conn, episode_id)
        assert episode is not None
        assert episode["user_message"] == "Rule message"
