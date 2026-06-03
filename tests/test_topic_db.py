import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.topic import store_topic, get_all_topics, update_topic_centroid


class TestStoreTopic:
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
            centroid = np.zeros(1024, dtype=np.float32)
            topic_id = store_topic(self.conn, "test_label", centroid, "2026-01-01T00:00:00+00:00")
            import uuid
            uuid.UUID(topic_id, version=4)
        finally:
            self._teardown_db()

    def test_writes_row_to_topics(self):
        self._setup_db()
        try:
            centroid = np.ones(1024, dtype=np.float32)
            store_topic(self.conn, "test_label", centroid, "2026-01-01T00:00:00+00:00")
            cursor = self.conn.execute("SELECT COUNT(*) FROM topics")
            count = cursor.fetchone()[0]
            assert count == 1
        finally:
            self._teardown_db()

    def test_sets_episode_count_to_zero(self):
        self._setup_db()
        try:
            centroid = np.zeros(1024, dtype=np.float32)
            topic_id = store_topic(self.conn, "test_label", centroid, "2026-01-01T00:00:00+00:00")
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            assert topic["episode_count"] == 0
        finally:
            self._teardown_db()

    def test_stores_label(self):
        self._setup_db()
        try:
            centroid = np.zeros(1024, dtype=np.float32)
            topic_id = store_topic(self.conn, "my_topic", centroid, "2026-01-01T00:00:00+00:00")
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            assert topic["label"] == "my_topic"
        finally:
            self._teardown_db()

    def test_sets_last_updated_at_equal_to_created_at(self):
        self._setup_db()
        try:
            centroid = np.zeros(1024, dtype=np.float32)
            created = "2026-01-01T00:00:00+00:00"
            topic_id = store_topic(self.conn, "test_label", centroid, created)
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            assert topic["created_at"] == created
            assert topic["last_updated_at"] == created
        finally:
            self._teardown_db()


class TestGetAllTopics:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_empty_list_when_no_topics(self):
        self._setup_db()
        try:
            result = get_all_topics(self.conn)
            assert result == []
        finally:
            self._teardown_db()

    def test_returns_all_topics(self):
        self._setup_db()
        try:
            centroid1 = np.ones(1024, dtype=np.float32)
            centroid2 = np.zeros(1024, dtype=np.float32)
            store_topic(self.conn, "label1", centroid1, "2026-01-01T00:00:00+00:00")
            store_topic(self.conn, "label2", centroid2, "2026-01-01T00:00:00+00:00")
            topics = get_all_topics(self.conn)
            assert len(topics) == 2
        finally:
            self._teardown_db()

    def test_returns_correct_fields(self):
        self._setup_db()
        try:
            centroid = np.full(1024, 0.5, dtype=np.float32)
            store_topic(self.conn, "test_label", centroid, "2026-01-01T00:00:00+00:00")
            topics = get_all_topics(self.conn)
            assert len(topics) == 1
            topic = topics[0]
            assert "id" in topic
            assert "label" in topic
            assert "centroid" in topic
            assert "episode_count" in topic
            assert "created_at" in topic
            assert "last_updated_at" in topic
            assert topic["label"] == "test_label"
        finally:
            self._teardown_db()

    def test_centroid_returned_as_bytes(self):
        self._setup_db()
        try:
            centroid = np.ones(1024, dtype=np.float32)
            store_topic(self.conn, "test_label", centroid, "2026-01-01T00:00:00+00:00")
            topics = get_all_topics(self.conn)
            topic = topics[0]
            assert isinstance(topic["centroid"], bytes)
            recovered = np.frombuffer(topic["centroid"], dtype=np.float32)
            assert recovered.shape == (1024,)
            assert np.allclose(recovered, centroid)
        finally:
            self._teardown_db()


class TestUpdateTopicCentroid:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_updates_centroid(self):
        self._setup_db()
        try:
            old_centroid = np.zeros(1024, dtype=np.float32)
            topic_id = store_topic(self.conn, "test", old_centroid, "2026-01-01T00:00:00+00:00")
            new_centroid = np.ones(1024, dtype=np.float32)
            update_topic_centroid(self.conn, topic_id, new_centroid, 5)
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            recovered = np.frombuffer(topic["centroid"], dtype=np.float32)
            assert np.allclose(recovered, new_centroid)
        finally:
            self._teardown_db()

    def test_updates_episode_count(self):
        self._setup_db()
        try:
            centroid = np.zeros(1024, dtype=np.float32)
            topic_id = store_topic(self.conn, "test", centroid, "2026-01-01T00:00:00+00:00")
            new_centroid = np.ones(1024, dtype=np.float32)
            update_topic_centroid(self.conn, topic_id, new_centroid, 7)
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            assert topic["episode_count"] == 7
        finally:
            self._teardown_db()

    def test_updates_last_updated_at(self):
        self._setup_db()
        try:
            centroid = np.zeros(1024, dtype=np.float32)
            topic_id = store_topic(self.conn, "test", centroid, "2026-01-01T00:00:00+00:00")
            new_centroid = np.ones(1024, dtype=np.float32)
            update_topic_centroid(self.conn, topic_id, new_centroid, 1)
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            assert topic["last_updated_at"] is not None
            assert topic["last_updated_at"] != "2026-01-01T00:00:00+00:00"
        finally:
            self._teardown_db()
