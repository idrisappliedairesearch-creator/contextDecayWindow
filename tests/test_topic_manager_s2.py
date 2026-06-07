import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode
from src.db.topic import get_all_topics
from src.memory.topic_manager import TopicManager
from src.observability.turn_record import AssignmentResult


def _make_embedding(value: float = 1.0) -> np.ndarray:
    return np.full(1024, value, dtype=np.float32)


class TestTopicThresholdAt0_50:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_threshold_is_0_50(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            assert tm.TOPIC_SIMILARITY_THRESHOLD == 0.50
        finally:
            self._teardown_db()

    def test_embedding_at_0_6_similar_assigned_to_existing_topic(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb1 = _make_embedding(1.0)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)

            emb2 = np.full(1024, 1.1, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            result2 = tm.assign(episode_id2, emb2)

            assert tm.topic_count == 1
            topic = tm._topics[result2.topic_id]
            assert topic["label"] == "topic_1"
            assert result2.is_new_topic is False
        finally:
            self._teardown_db()

    def test_embedding_below_0_50_creates_new_topic(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            emb1 = np.array([1.0] + [0.0] * 1023, dtype=np.float32)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)

            emb2 = np.array([0.0] + [1.0] * 1023, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            result2 = tm.assign(episode_id2, emb2)

            assert tm.topic_count == 2
            assert result2.is_new_topic is True
        finally:
            self._teardown_db()

    def test_similar_embeddings_consolidate_at_0_50(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            emb1 = _make_embedding(1.0)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)

            emb2 = _make_embedding(1.05)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            result2 = tm.assign(episode_id2, emb2)

            assert tm.topic_count == 1
            assert result2.is_new_topic is False
            assert result2.topic_label == "topic_1"
        finally:
            self._teardown_db()

    def test_dissimilar_embeddings_still_create_separate_topics(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            emb1 = np.array([1.0] + [0.0] * 1023, dtype=np.float32)
            episode_id1 = store_episode(self.conn, "msg1", "reply1", emb1, 1)
            tm.assign(episode_id1, emb1)

            emb2 = np.array([0.0, 1.0] + [0.0] * 1022, dtype=np.float32)
            episode_id2 = store_episode(self.conn, "msg2", "reply2", emb2, 2)
            result2 = tm.assign(episode_id2, emb2)

            assert tm.topic_count == 2
            assert result2.is_new_topic is True
        finally:
            self._teardown_db()

    def test_new_topic_created_when_no_existing_topics(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)
            episode_id = store_episode(self.conn, "msg", "reply", emb, 1)
            result = tm.assign(episode_id, emb)
            assert result.is_new_topic is True
            assert result.topic_label == "topic_1"
        finally:
            self._teardown_db()

    def test_assignment_result_at_new_threshold(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)
            episode_id = store_episode(self.conn, "msg", "reply", emb, 1)
            result = tm.assign(episode_id, emb)
            assert isinstance(result, AssignmentResult)
            assert result.centroid_drift == 0.0
            assert result.topic_id is not None
        finally:
            self._teardown_db()
