import os
import sys
import tempfile
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.db.schema import init_db
from src.memory.topic_manager import TopicManager
from src.memory.retrieval_engine import RetrievalEngine
from src.runners.iterative_runner import IterativeRunner
from tests.conftest import MockInferenceProvider, MockInferenceResult


class MockEmbeddingProvider:
    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(1024, dtype=np.float32)
        vec[0] = 1.0
        return vec


class TestIterativeRunnerInit:

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

    def test_condition_is_iterative(self):
        assert self.runner.condition == "iterative"

    def test_history_token_estimate_returns_zero(self):
        assert self.runner.history_token_estimate == 0


class TestIterativeRunnerBuildContextEmptyDb:

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

    def test_build_context_returns_prompt_and_record(self):
        prompt, record = self.runner.build_context("Hello", 1)
        assert isinstance(prompt, str)
        assert record.turn_number == 1
        assert record.condition == "iterative"

    def test_record_has_zero_retrieval_counts(self):
        _, record = self.runner.build_context("Hello", 1)
        assert record.k_count == 0
        assert record.n_count == 0
        assert record.total_in_context == 0

    def test_record_contains_user_message(self):
        _, record = self.runner.build_context("Test message", 1)
        assert record.user_message == "Test message"


class TestIterativeRunnerOnTurnComplete:

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

    def test_stores_episode_and_assigns_topic(self):
        embedding = self.embedding_provider.embed("User: Hello\nAssistant: Hi")
        result = self.runner.on_turn_complete("Hello", "Hi", 1, embedding)
        assert result is not None
        assert hasattr(result, "topic_id")
        assert hasattr(result, "topic_label")
        assert hasattr(result, "is_new_topic")
        assert hasattr(result, "centroid_drift")

    def test_first_episode_creates_new_topic(self):
        embedding = self.embedding_provider.embed("User: Hello\nAssistant: Hi")
        result = self.runner.on_turn_complete("Hello", "Hi", 1, embedding)
        assert result.is_new_topic is True

    def test_returns_assignment_result(self):
        embedding = self.embedding_provider.embed("User: Q\nAssistant: A")
        result = self.runner.on_turn_complete("Q", "A", 1, embedding)
        assert isinstance(result.topic_id, str)
        assert len(result.topic_id) > 0
        assert isinstance(result.topic_label, str)
        assert isinstance(result.centroid_drift, float)

    def test_topic_count_increments(self):
        embedding = self.embedding_provider.embed("User: Q\nAssistant: A")
        self.runner.on_turn_complete("Q", "A", 1, embedding)
        assert self.runner._topic_manager.topic_count >= 1


class TestIterativeRunnerIntegration:

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

    def test_full_turn_sequence(self):
        for i in range(1, 4):
            prompt, record = self.runner.build_context(f"Question {i}", i)
            assert record.turn_number == i
            assert record.condition == "iterative"

            embedding = self.embedding_provider.embed(f"User: Question {i}\nAssistant: Answer {i}")
            assignment = self.runner.on_turn_complete(f"Question {i}", f"Answer {i}", i, embedding)
            assert assignment is not None

    def test_implements_base_interface(self):
        from src.runners.base_runner import BaseRunner
        assert isinstance(self.runner, BaseRunner)
        assert hasattr(self.runner, "condition")
        assert hasattr(self.runner, "build_context")
        assert hasattr(self.runner, "on_turn_complete")
        assert hasattr(self.runner, "history_token_estimate")
