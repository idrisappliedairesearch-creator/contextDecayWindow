import os
import sys
import tempfile
import sqlite3
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode, get_episode_by_id


class TestInitDb:
    def test_creates_database_file(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = init_db(db_path)
            assert os.path.isfile(db_path)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_creates_all_tables(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = init_db(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            assert "episodes" in tables
            assert "topics" in tables
            assert "retrieval_events" in tables
            assert "rule_store" in tables
            conn.close()
        finally:
            os.unlink(db_path)

    def test_idempotent(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn1 = init_db(db_path)
            conn1.close()
            conn2 = init_db(db_path)
            cursor = conn2.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            assert len(tables) == 4
            conn2.close()
        finally:
            os.unlink(db_path)


class TestStoreEpisode:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_valid_uuid(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "hello", "hi there", embedding, 1
            )
            import uuid
            uuid.UUID(episode_id, version=4)
        finally:
            self._teardown_db()

    def test_writes_row_to_episodes(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "test user msg", "test assistant msg", embedding, 5
            )
            cursor = self.conn.execute("SELECT COUNT(*) FROM episodes")
            count = cursor.fetchone()[0]
            assert count == 1
        finally:
            self._teardown_db()

    def test_sets_defaults(self):
        self._setup_db()
        try:
            embedding = np.zeros(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "user msg", "assistant msg", embedding, 3
            )
            row = get_episode_by_id(self.conn, episode_id)
            assert row["topic_id"] is None
            assert row["last_retrieved_at"] is None
            assert row["retrieval_count"] == 0
        finally:
            self._teardown_db()


class TestGetEpisodeById:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_retrieves_stored_episode(self):
        self._setup_db()
        try:
            embedding = np.ones(1024, dtype=np.float32)
            episode_id = store_episode(
                self.conn, "hello", "world", embedding, 1
            )
            row = get_episode_by_id(self.conn, episode_id)
            assert row is not None
            assert row["id"] == episode_id
            assert row["user_message"] == "hello"
            assert row["assistant_message"] == "world"
            assert row["turn_number"] == 1
            assert row["created_at"] is not None
        finally:
            self._teardown_db()

    def test_returns_none_for_missing_id(self):
        self._setup_db()
        try:
            result = get_episode_by_id(self.conn, "nonexistent-id")
            assert result is None
        finally:
            self._teardown_db()
