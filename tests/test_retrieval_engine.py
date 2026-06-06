import os
import sys
import tempfile
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode, get_episode_by_id
from src.memory.retrieval_engine import (
    RetrievalEngine,
    RetrievalResult,
    DECAY_RATE,
    K_SIMILARITY_THRESHOLD,
)


def _make_unit_vector(dim, index, dtype=np.float32):
    vec = np.zeros(dim, dtype=dtype)
    vec[index] = 1.0
    return vec


class TestConstants:
    def test_decay_rate_defined(self):
        assert DECAY_RATE == 0.1

    def test_k_similarity_threshold_defined(self):
        assert K_SIMILARITY_THRESHOLD == 0.50


class TestComputeDecay:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_null_last_retrieved_at_returns_1_0(self):
        self._setup()
        try:
            score = self.engine._compute_decay(None)
            assert score == 1.0
        finally:
            self._teardown()

    def test_recent_retrieval_gives_high_score(self):
        self._setup()
        try:
            recent = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            score = self.engine._compute_decay(recent)
            assert score > 0.99
        finally:
            self._teardown()

    def test_old_retrieval_gives_low_score(self):
        self._setup()
        try:
            old = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            score = self.engine._compute_decay(old)
            expected = np.exp(-DECAY_RATE * 24)
            assert abs(score - expected) < 0.01
            assert score < 0.5
        finally:
            self._teardown()

    def test_decay_decreases_monotonically(self):
        self._setup()
        try:
            now = datetime.now(timezone.utc)
            scores = []
            for hours_ago in range(0, 11):
                ts = (now - timedelta(hours=hours_ago)).isoformat()
                scores.append(self.engine._compute_decay(ts))
            for i in range(len(scores) - 1):
                assert scores[i] > scores[i + 1], (
                    f"Decay not monotonic: {scores[i]} <= {scores[i+1]} at {i}h vs {i+1}h"
                )
        finally:
            self._teardown()


class TestKRetrieve:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def _store_unit_episodes(self, indices):
        for i, idx in enumerate(indices):
            emb = _make_unit_vector(1024, idx)
            store_episode(self.conn, f"msg{idx}", f"resp{idx}", emb, i + 1)

    def test_returns_matches_above_threshold(self):
        self._setup()
        try:
            query = _make_unit_vector(1024, 0)
            similar = _make_unit_vector(1024, 0) * 0.9 + _make_unit_vector(1024, 1) * 0.1
            dissimilar = _make_unit_vector(1024, 500)

            store_episode(self.conn, "similar", "r", similar, 1)
            store_episode(self.conn, "dissimilar", "r", dissimilar, 2)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            k_ids, k_scores = self.engine._k_retrieve(query, episodes)
            assert len(k_ids) == 1
            assert k_ids[0] == episodes[0]["id"]
            assert k_scores[k_ids[0]] >= K_SIMILARITY_THRESHOLD

        finally:
            self._teardown()

    def test_returns_empty_when_no_matches(self):
        self._setup()
        try:
            query = _make_unit_vector(1024, 0)
            dissimilar = _make_unit_vector(1024, 999)
            store_episode(self.conn, "dissimilar", "r", dissimilar, 1)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            k_ids, k_scores = self.engine._k_retrieve(query, episodes)
            assert k_ids == []
            assert k_scores == {}

        finally:
            self._teardown()

    def test_returns_empty_for_empty_db(self):
        self._setup()
        try:
            query = _make_unit_vector(1024, 0)
            k_ids, k_scores = self.engine._k_retrieve(query, [])
            assert k_ids == []
            assert k_scores == {}
        finally:
            self._teardown()


class TestNRetrieve:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_all_episodes(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            store_episode(self.conn, "m1", "r1", emb, 1)
            store_episode(self.conn, "m2", "r2", emb, 2)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            n_ids, n_scores = self.engine._n_retrieve(episodes)
            assert len(n_ids) == 2

        finally:
            self._teardown()

    def test_null_last_retrieved_at_gets_decay_1_0(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            eid = store_episode(self.conn, "m1", "r1", emb, 1)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            n_ids, n_scores = self.engine._n_retrieve(episodes)
            assert n_scores[eid] == 1.0

        finally:
            self._teardown()

    def test_sorted_by_decay_descending(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            store_episode(self.conn, "fresh", "r", emb, 1)

            self.conn.execute(
                "UPDATE episodes SET last_retrieved_at = ?",
                ((datetime.now(timezone.utc) - timedelta(hours=10)).isoformat(),),
            )
            self.conn.commit()
            store_episode(self.conn, "stale", "r", emb, 2)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            n_ids, n_scores = self.engine._n_retrieve(episodes)

            stale_id = episodes[0]["id"]
            fresh_id = episodes[1]["id"]
            assert n_scores[fresh_id] > n_scores[stale_id]
            assert n_ids[0] == fresh_id

        finally:
            self._teardown()


class TestDeduplicateAndSort:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_filters_to_included_ids(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            eid1 = store_episode(self.conn, "m1", "r1", emb, 1)
            eid2 = store_episode(self.conn, "m2", "r2", emb, 2)
            store_episode(self.conn, "m3", "r3", emb, 3)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            result = self.engine._deduplicate_and_sort(episodes, {eid1, eid2})
            assert len(result) == 2
            ids = [e["id"] for e in result]
            assert eid1 in ids
            assert eid2 in ids

        finally:
            self._teardown()

    def test_sorted_by_turn_number_ascending(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            eid3 = store_episode(self.conn, "m3", "r3", emb, 3)
            eid1 = store_episode(self.conn, "m1", "r1", emb, 1)
            eid2 = store_episode(self.conn, "m2", "r2", emb, 2)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            result = self.engine._deduplicate_and_sort(
                episodes, {eid1, eid2, eid3}
            )
            assert result[0]["turn_number"] == 1
            assert result[1]["turn_number"] == 2
            assert result[2]["turn_number"] == 3

        finally:
            self._teardown()

    def test_deduplication_episode_in_both_sets(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            eid1 = store_episode(self.conn, "m1", "r1", emb, 1)

            all_eps = self.conn.execute(
                "SELECT id, topic_id, user_message, assistant_message, "
                "embedding, turn_number, created_at, last_retrieved_at, "
                "retrieval_count FROM episodes ORDER BY turn_number ASC"
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "embedding", "turn_number", "created_at", "last_retrieved_at",
                "retrieval_count",
            ]
            episodes = []
            for row in all_eps:
                ep = dict(zip(columns, row))
                ep["embedding"] = np.frombuffer(ep["embedding"], dtype=np.float32)
                episodes.append(ep)

            included = {eid1}
            result = self.engine._deduplicate_and_sort(episodes, included)
            assert len(result) == 1
            assert result[0]["id"] == eid1

        finally:
            self._teardown()


class TestRetrievalResult:
    def test_default_values(self):
        result = RetrievalResult()
        assert result.episodes == []
        assert result.k_episode_ids == []
        assert result.k_scores == {}
        assert result.n_episode_ids == []
        assert result.n_scores == {}
        assert result.constructed_prompt == ""
        assert result.estimated_tokens == 0
        assert result.k_count == 0
        assert result.n_count == 0
        assert result.total_episodes_in_context == 0

    def test_populated_values(self):
        result = RetrievalResult(
            episodes=[{"id": "a"}],
            k_episode_ids=["a"],
            k_scores={"a": 0.9},
            n_episode_ids=["a", "b"],
            n_scores={"a": 0.95, "b": 0.8},
            constructed_prompt="prompt text",
            estimated_tokens=50,
            k_count=1,
            n_count=2,
            total_episodes_in_context=2,
        )
        assert result.k_count == 1
        assert result.n_count == 2
        assert result.total_episodes_in_context == 2
        assert result.estimated_tokens == 50
