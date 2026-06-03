import os
import sys
import tempfile
import sqlite3
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode
from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    update_retrieval_metadata,
    log_retrieval_event,
    log_retrieval_events_batch,
)


class TestGetAllEpisodesWithEmbeddings:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_empty_list_when_no_episodes(self):
        self._setup_db()
        try:
            result = get_all_episodes_with_embeddings(self.conn)
            assert result == []
        finally:
            self._teardown_db()

    def test_returns_all_episodes(self):
        self._setup_db()
        try:
            emb1 = np.ones(1024, dtype=np.float32) * 0.5
            emb2 = np.ones(1024, dtype=np.float32) * 0.8
            store_episode(self.conn, "msg1", "resp1", emb1, 1)
            store_episode(self.conn, "msg2", "resp2", emb2, 2)

            episodes = get_all_episodes_with_embeddings(self.conn)
            assert len(episodes) == 2

        finally:
            self._teardown_db()

    def test_episodes_ordered_by_turn_number(self):
        self._setup_db()
        try:
            emb1 = np.ones(1024, dtype=np.float32)
            emb2 = np.ones(1024, dtype=np.float32) * 2
            emb3 = np.ones(1024, dtype=np.float32) * 3
            store_episode(self.conn, "c", "rc", emb3, 3)
            store_episode(self.conn, "a", "ra", emb1, 1)
            store_episode(self.conn, "b", "rb", emb2, 2)

            episodes = get_all_episodes_with_embeddings(self.conn)
            assert episodes[0]["turn_number"] == 1
            assert episodes[1]["turn_number"] == 2
            assert episodes[2]["turn_number"] == 3

        finally:
            self._teardown_db()

    def test_embedding_returned_as_bytes(self):
        self._setup_db()
        try:
            original = np.random.random(1024).astype(np.float32)
            store_episode(self.conn, "test", "test_resp", original, 1)

            episodes = get_all_episodes_with_embeddings(self.conn)
            ep = episodes[0]
            assert isinstance(ep["embedding"], (bytes, bytearray, memoryview))

            recovered = np.frombuffer(ep["embedding"], dtype=np.float32)
            np.testing.assert_array_almost_equal(recovered, original, decimal=5)

        finally:
            self._teardown_db()

    def test_all_fields_present(self):
        self._setup_db()
        try:
            emb = np.ones(1024, dtype=np.float32)
            store_episode(self.conn, "hello", "world", emb, 5)

            episodes = get_all_episodes_with_embeddings(self.conn)
            ep = episodes[0]
            assert "id" in ep
            assert "topic_id" in ep
            assert "user_message" in ep
            assert "assistant_message" in ep
            assert "embedding" in ep
            assert "turn_number" in ep
            assert "created_at" in ep
            assert "last_retrieved_at" in ep
            assert "retrieval_count" in ep
            assert ep["user_message"] == "hello"
            assert ep["assistant_message"] == "world"
            assert ep["turn_number"] == 5

        finally:
            self._teardown_db()


class TestUpdateRetrievalMetadata:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_updates_last_retrieved_at(self):
        self._setup_db()
        try:
            emb = np.ones(1024, dtype=np.float32)
            eid = store_episode(self.conn, "msg", "resp", emb, 1)

            ts = "2026-06-01T12:00:00+00:00"
            update_retrieval_metadata(self.conn, [eid], ts)

            cursor = self.conn.execute(
                "SELECT last_retrieved_at FROM episodes WHERE id = ?", (eid,)
            )
            row = cursor.fetchone()
            assert row[0] == ts

        finally:
            self._teardown_db()

    def test_increments_retrieval_count(self):
        self._setup_db()
        try:
            emb = np.ones(1024, dtype=np.float32)
            eid = store_episode(self.conn, "msg", "resp", emb, 1)

            ts1 = "2026-06-01T12:00:00+00:00"
            update_retrieval_metadata(self.conn, [eid], ts1)
            ts2 = "2026-06-01T13:00:00+00:00"
            update_retrieval_metadata(self.conn, [eid], ts2)

            cursor = self.conn.execute(
                "SELECT retrieval_count, last_retrieved_at FROM episodes WHERE id = ?",
                (eid,),
            )
            row = cursor.fetchone()
            assert row[0] == 2
            assert row[1] == ts2

        finally:
            self._teardown_db()

    def test_batch_update_multiple_episodes(self):
        self._setup_db()
        try:
            emb1 = np.ones(1024, dtype=np.float32)
            emb2 = np.ones(1024, dtype=np.float32) * 2
            eid1 = store_episode(self.conn, "msg1", "resp1", emb1, 1)
            eid2 = store_episode(self.conn, "msg2", "resp2", emb2, 2)

            ts = "2026-06-01T12:00:00+00:00"
            update_retrieval_metadata(self.conn, [eid1, eid2], ts)

            cursor = self.conn.execute(
                "SELECT id, last_retrieved_at, retrieval_count FROM episodes ORDER BY turn_number"
            )
            rows = cursor.fetchall()
            assert rows[0][1] == ts
            assert rows[0][2] == 1
            assert rows[1][1] == ts
            assert rows[1][2] == 1

        finally:
            self._teardown_db()


class TestLogRetrievalEvent:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_writes_single_event(self):
        self._setup_db()
        try:
            log_retrieval_event(
                self.conn, 1, "ep-001", 0.85, 0.95, "K"
            )

            cursor = self.conn.execute("SELECT COUNT(*) FROM retrieval_events")
            count = cursor.fetchone()[0]
            assert count == 1

            cursor = self.conn.execute(
                "SELECT turn_number, episode_id, similarity_score, decay_score, "
                "retrieval_type, retrieved_at FROM retrieval_events"
            )
            row = cursor.fetchone()
            assert row[0] == 1
            assert row[1] == "ep-001"
            assert row[2] == 0.85
            assert row[3] == 0.95
            assert row[4] == "K"
            assert row[5] is not None

        finally:
            self._teardown_db()

    def test_event_id_is_uuid(self):
        self._setup_db()
        try:
            import uuid as uuid_mod
            log_retrieval_event(
                self.conn, 1, "ep-001", 0.85, 0.95, "KN"
            )

            cursor = self.conn.execute("SELECT id FROM retrieval_events")
            eid = cursor.fetchone()[0]
            uuid_mod.UUID(eid, version=4)

        finally:
            self._teardown_db()


class TestLogRetrievalEventsBatch:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_writes_multiple_events(self):
        self._setup_db()
        try:
            events = [
                {"turn_number": 5, "episode_id": "ep-001", "similarity_score": 0.9, "decay_score": 0.8, "retrieval_type": "KN"},
                {"turn_number": 5, "episode_id": "ep-002", "similarity_score": 0.0, "decay_score": 0.6, "retrieval_type": "N"},
            ]
            log_retrieval_events_batch(self.conn, events)

            cursor = self.conn.execute("SELECT COUNT(*) FROM retrieval_events")
            count = cursor.fetchone()[0]
            assert count == 2

        finally:
            self._teardown_db()

    def test_batch_events_share_retrieved_at(self):
        self._setup_db()
        try:
            events = [
                {"turn_number": 3, "episode_id": "ep-001", "similarity_score": 0.88, "decay_score": 0.99, "retrieval_type": "K"},
                {"turn_number": 3, "episode_id": "ep-002", "similarity_score": 0.0, "decay_score": 0.5, "retrieval_type": "N"},
            ]
            log_retrieval_events_batch(self.conn, events)

            cursor = self.conn.execute(
                "SELECT retrieved_at FROM retrieval_events ORDER BY episode_id"
            )
            rows = cursor.fetchall()
            assert rows[0][0] == rows[1][0]

        finally:
            self._teardown_db()
