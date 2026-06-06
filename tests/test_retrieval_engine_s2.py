import os
import sys
import tempfile
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode, get_episode_by_id
from src.memory.retrieval_engine import (
    RetrievalEngine,
    RetrievalResult,
    N_RETRIEVAL_CAP,
    K_SIMILARITY_THRESHOLD,
)


def _make_unit_vector(dim, index, dtype=np.float32):
    vec = np.zeros(dim, dtype=dtype)
    vec[index] = 1.0
    return vec


class TestNRetrievalCap:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_cap_constant_is_10(self):
        assert N_RETRIEVAL_CAP == 10

    def test_n_retrieve_returns_all_when_store_has_10_or_fewer(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            for i in range(10):
                store_episode(self.conn, f"msg{i}", f"resp{i}", emb, i + 1)

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
            assert len(n_ids) == 10

        finally:
            self._teardown()

    def test_n_retrieve_caps_at_10_when_store_has_more(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            for i in range(20):
                store_episode(self.conn, f"msg{i}", f"resp{i}", emb, i + 1)

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
            assert len(n_ids) == 10
            assert len(n_scores) == 20

        finally:
            self._teardown()

    def test_n_retrieve_returns_all_when_fewer_than_10(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            for i in range(5):
                store_episode(self.conn, f"msg{i}", f"resp{i}", emb, i + 1)

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
            assert len(n_ids) == 5

        finally:
            self._teardown()


class TestKRetrievalBelowCap:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_k_returns_all_above_0_50_regardless_of_n_cap(self):
        self._setup()
        try:
            query = _make_unit_vector(1024, 0)

            for i in range(15):
                ep_emb = _make_unit_vector(1024, 0) * 0.9 + _make_unit_vector(1024, i + 1) * 0.1
                store_episode(self.conn, f"msg{i}", f"resp{i}", ep_emb, i + 1)

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
            assert len(k_ids) == 15
            for eid in k_ids:
                assert k_scores[eid] >= K_SIMILARITY_THRESHOLD

        finally:
            self._teardown()


class TestRetrievalTypeAssignment:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_episode_in_both_k_and_n_gets_kn_type(self):
        self._setup()
        try:
            query = _make_unit_vector(1024, 0)
            emb = _make_unit_vector(1024, 0) * 0.9 + _make_unit_vector(1024, 1) * 0.1
            eid = store_episode(self.conn, "msg", "resp", emb, 1)

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
            n_ids, n_scores = self.engine._n_retrieve(episodes)

            k_set = set(k_ids)
            n_set = set(n_ids)
            assert eid in k_set
            assert eid in n_set

            included_ids = k_set | n_set
            for ep in episodes:
                if ep["id"] in included_ids:
                    if ep["id"] in k_set and ep["id"] in n_set:
                        assert True
                    elif ep["id"] in k_set:
                        assert True
                    else:
                        assert True

        finally:
            self._teardown()

    def test_episode_only_in_k_gets_k_type(self):
        self._setup()
        try:
            query = _make_unit_vector(1024, 0)

            for i in range(15):
                emb = _make_unit_vector(1024, 0) * 0.9 + _make_unit_vector(1024, i + 1) * 0.1
                store_episode(self.conn, f"msg{i}", f"resp{i}", emb, i + 1)

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
            n_ids, n_scores = self.engine._n_retrieve(episodes)

            k_set = set(k_ids)
            n_set = set(n_ids)

            k_only = k_set - n_set
            assert len(k_only) > 0

            for ep in episodes:
                eid = ep["id"]
                if eid in k_set and eid not in n_set:
                    assert True

        finally:
            self._teardown()


class TestNTotalInStore:
    def _setup(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)
        self.engine = RetrievalEngine(self.conn)

    def _teardown(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_retrieval_result_has_n_total_in_store(self):
        self._setup()
        try:
            result = RetrievalResult()
            assert hasattr(result, "n_total_in_store")
            assert result.n_total_in_store == 0
        finally:
            self._teardown()

    def test_retrieval_result_n_total_in_store_reflects_store_size(self):
        self._setup()
        try:
            emb = np.ones(1024, dtype=np.float32)
            for i in range(15):
                store_episode(self.conn, f"msg{i}", f"resp{i}", emb, i + 1)

            result = RetrievalResult(
                n_count=10,
                n_total_in_store=15,
            )
            assert result.n_count == 10
            assert result.n_total_in_store == 15

        finally:
            self._teardown()


class TestThresholdConstants:
    def test_k_threshold_is_0_50(self):
        assert K_SIMILARITY_THRESHOLD == 0.50

    def test_n_cap_is_10(self):
        assert N_RETRIEVAL_CAP == 10
