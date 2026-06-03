import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode
from src.db.topic import get_all_topics
from src.memory.topic_manager import TopicManager


def _make_embedding(value: float = 1.0) -> np.ndarray:
    return np.full(1024, value, dtype=np.float32)


class TestTopicManagerEmptyDb:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_starts_with_no_topics(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            assert tm.topic_count == 0
        finally:
            self._teardown_db()

    def test_first_episode_creates_topic_1(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            embedding = _make_embedding(1.0)
            episode_id = store_episode(self.conn, "hello", "hi", embedding, 1)
            topic_id = tm.assign(episode_id, embedding)
            assert tm.topic_count == 1
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id)
            assert topic["label"] == "topic_1"
        finally:
            self._teardown_db()

    def test_first_assignment_writes_topic_id_to_episode(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            embedding = _make_embedding(1.0)
            episode_id = store_episode(self.conn, "hello", "hi", embedding, 1)
            tm.assign(episode_id, embedding)
            cursor = self.conn.execute("SELECT topic_id FROM episodes WHERE id = ?", (episode_id,))
            row = cursor.fetchone()
            assert row[0] is not None
        finally:
            self._teardown_db()


class TestTopicManagerAssignment:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_similar_embedding_assigned_to_existing_topic(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb1 = _make_embedding(1.0)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)
            emb2 = np.full(1024, 1.1, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            topic_id2 = tm.assign(episode_id2, emb2)
            assert tm.topic_count == 1
            topic = tm._topics[topic_id2]
            assert topic["label"] == "topic_1"
        finally:
            self._teardown_db()

    def test_dissimilar_embedding_creates_new_topic(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb1 = np.full(1024, 1.0, dtype=np.float32)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)
            emb2 = np.full(1024, 0.0, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            tm.assign(episode_id2, emb2)
            assert tm.topic_count == 2
        finally:
            self._teardown_db()

    def test_second_dissimilar_topic_labelled_topic_2(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb1 = np.full(1024, 1.0, dtype=np.float32)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)
            emb2 = np.full(1024, 0.0, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            topic_id2 = tm.assign(episode_id2, emb2)
            topics = get_all_topics(self.conn)
            topic = next(t for t in topics if t["id"] == topic_id2)
            assert topic["label"] == "topic_2"
        finally:
            self._teardown_db()

    def test_threshold_constant_used(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            assert tm.TOPIC_SIMILARITY_THRESHOLD == 0.70
        finally:
            self._teardown_db()


class TestCentroidUpdate:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_centroid_running_average_correct(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb1 = np.full(1024, 2.0, dtype=np.float32)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)
            emb2 = np.full(1024, 4.0, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            topic_id = tm.assign(episode_id2, emb2)
            expected_centroid = (emb1 * 1 + emb2) / 2
            topic = tm._topics[topic_id]
            assert np.allclose(topic["centroid"], expected_centroid)
        finally:
            self._teardown_db()

    def test_episode_count_increments(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb, 1)
            tm.assign(episode_id1, emb)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb, 2)
            topic_id = tm.assign(episode_id2, emb)
            topic = tm._topics[topic_id]
            assert topic["episode_count"] == 2
        finally:
            self._teardown_db()

    def test_db_episode_count_matches_memory(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb, 1)
            tm.assign(episode_id1, emb)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb, 2)
            topic_id = tm.assign(episode_id2, emb)
            db_topics = get_all_topics(self.conn)
            db_topic = next(t for t in db_topics if t["id"] == topic_id)
            mem_topic = tm._topics[topic_id]
            assert db_topic["episode_count"] == mem_topic["episode_count"] == 2
        finally:
            self._teardown_db()

    def test_db_centroid_matches_memory(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb1 = np.full(1024, 1.0, dtype=np.float32)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)
            emb2 = np.full(1024, 3.0, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            topic_id = tm.assign(episode_id2, emb2)
            db_topics = get_all_topics(self.conn)
            db_topic = next(t for t in db_topics if t["id"] == topic_id)
            db_centroid = np.frombuffer(db_topic["centroid"], dtype=np.float32)
            mem_centroid = tm._topics[topic_id]["centroid"]
            assert np.allclose(db_centroid, mem_centroid)
        finally:
            self._teardown_db()


class TestStartupFromExistingDb:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_loads_existing_topics_on_init(self):
        self._setup_db()
        try:
            from src.db.topic import store_topic
            centroid = np.ones(1024, dtype=np.float32)
            store_topic(self.conn, "topic_1", centroid, "2026-01-01T00:00:00+00:00")
            tm = TopicManager(self.conn)
            assert tm.topic_count == 1
            assert len(tm._topics) == 1
        finally:
            self._teardown_db()

    def test_centroid_loaded_as_numpy_array(self):
        self._setup_db()
        try:
            from src.db.topic import store_topic
            centroid = np.full(1024, 2.5, dtype=np.float32)
            store_topic(self.conn, "topic_1", centroid, "2026-01-01T00:00:00+00:00")
            tm = TopicManager(self.conn)
            topic_id = list(tm._topics.keys())[0]
            loaded_centroid = tm._topics[topic_id]["centroid"]
            assert isinstance(loaded_centroid, np.ndarray)
            assert loaded_centroid.shape == (1024,)
            assert np.allclose(loaded_centroid, centroid)
        finally:
            self._teardown_db()

    def test_continues_assigning_after_reload(self):
        self._setup_db()
        try:
            from src.db.topic import store_topic
            centroid = np.full(1024, 1.0, dtype=np.float32)
            store_topic(self.conn, "topic_1", centroid, "2026-01-01T00:00:00+00:00")
            tm = TopicManager(self.conn)
            emb = np.full(1024, 1.1, dtype=np.float32)
            episode_id = store_episode(self.conn, "msg", "reply", emb, 10)
            topic_id = tm.assign(episode_id, emb)
            assert tm.topic_count == 1
            topic = tm._topics[topic_id]
            assert topic["label"] == "topic_1"
            assert topic["episode_count"] == 1
        finally:
            self._teardown_db()
