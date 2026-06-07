import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode
from src.db.topic import store_topic, get_all_topics, get_all_topics_with_centroids, reassign_episodes, merge_topics
from src.memory.topic_manager import TopicManager
from src.observability.turn_record import AssignmentResult, ConsolidationResult


def _make_embedding(value: float = 1.0) -> np.ndarray:
    return np.full(1024, value, dtype=np.float32)


def _create_two_topics_with_similarity(conn, target_sim, count_a=5, count_b=5):
    """Create two topics with a given cosine similarity between their centroids.

    cos_sim = overlap / (overlap + unique), so overlap = target_sim * unique / (1 - target_sim).
    """
    tm = TopicManager(conn)
    dim = 1024
    unique = 100
    overlap = int(target_sim * unique / (1 - target_sim))

    c1 = np.zeros(dim, dtype=np.float32)
    c1[:overlap + unique] = 1.0

    c2 = np.zeros(dim, dtype=np.float32)
    c2[:overlap] = 1.0
    c2[overlap + unique:overlap + unique * 2] = 1.0

    created_at = "2026-01-01T00:00:00+00:00"
    t1 = store_topic(conn, "topic_1", c1, created_at)
    t2 = store_topic(conn, "topic_2", c2, created_at)
    tm._topics[t1] = {"label": "topic_1", "centroid": c1, "episode_count": count_a, "created_at": created_at, "last_updated_at": created_at}
    tm._topics[t2] = {"label": "topic_2", "centroid": c2, "episode_count": count_b, "created_at": created_at, "last_updated_at": created_at}
    tm._episode_count = count_a + count_b
    return tm, t1, t2


def _create_three_topics_high_sim(conn):
    """Create three topics all with high pairwise similarity (~0.7)."""
    tm = TopicManager(conn)
    dim = 1024
    created_at = "2026-01-01T00:00:00+00:00"

    unique = 100
    overlap = int(0.70 * unique / (1 - 0.70))

    c1 = np.zeros(dim, dtype=np.float32)
    c1[:overlap + unique] = 1.0

    c2 = np.zeros(dim, dtype=np.float32)
    c2[:overlap] = 1.0
    c2[overlap + unique:overlap + unique * 2] = 1.0

    c3 = np.zeros(dim, dtype=np.float32)
    c3[:overlap] = 1.0
    c3[overlap + unique * 2:overlap + unique * 3] = 1.0

    t1 = store_topic(conn, "topic_1", c1, created_at)
    t2 = store_topic(conn, "topic_2", c2, created_at)
    t3 = store_topic(conn, "topic_3", c3, created_at)

    for i, (tid, c) in enumerate([(t1, c1), (t2, c2), (t3, c3)]):
        tm._topics[tid] = {"label": f"topic_{i+1}", "centroid": c, "episode_count": 4, "created_at": created_at, "last_updated_at": created_at}

    tm._episode_count = 12
    return tm, [t1, t2, t3]


class TestConsolidationTriggerTiming:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_consolidation_fires_at_episode_10(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            for i in range(10):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)
            assert result.consolidation is not None
            assert isinstance(result.consolidation, ConsolidationResult)
            assert result.consolidation.triggered_at_episode == 10
        finally:
            self._teardown_db()

    def test_consolidation_fires_at_episode_20(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            last_result = None
            for i in range(20):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                last_result = tm.assign(episode_id, emb)
            assert last_result.consolidation is not None
            assert last_result.consolidation.triggered_at_episode == 20
        finally:
            self._teardown_db()

    def test_consolidation_fires_at_episode_30(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            last_result = None
            for i in range(30):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                last_result = tm.assign(episode_id, emb)
            assert last_result.consolidation is not None
            assert last_result.consolidation.triggered_at_episode == 30
        finally:
            self._teardown_db()

    def test_consolidation_does_not_fire_at_episode_9(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            for i in range(9):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)
            assert result.consolidation is None
        finally:
            self._teardown_db()

    def test_consolidation_does_not_fire_at_episode_11(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            last_result = None
            for i in range(11):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                last_result = tm.assign(episode_id, emb)
            assert last_result.consolidation is None
        finally:
            self._teardown_db()

    def test_consolidation_does_not_fire_at_episode_15(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            last_result = None
            for i in range(15):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                last_result = tm.assign(episode_id, emb)
            assert last_result.consolidation is None
        finally:
            self._teardown_db()


class TestMergeLogic:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_pairs_above_0_60_are_merged(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)
            assert tm.topic_count == 2

            consolidation = tm._run_consolidation_pass()
            assert consolidation.pairs_merged >= 1
            assert consolidation.topics_after < consolidation.topics_before
        finally:
            self._teardown_db()

    def test_pairs_below_0_60_are_not_merged(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.50)
            assert tm.topic_count == 2

            consolidation = tm._run_consolidation_pass()
            assert consolidation.pairs_merged == 0
            assert consolidation.topics_after == consolidation.topics_before
        finally:
            self._teardown_db()

    def test_surviving_topic_centroid_is_weighted_average(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)

            topic_a = tm._topics[t1]
            topic_b = tm._topics[t2]
            count_a = topic_a["episode_count"]
            count_b = topic_b["episode_count"]
            expected_centroid = (topic_a["centroid"] * count_a + topic_b["centroid"] * count_b) / (count_a + count_b)

            consolidation = tm._run_consolidation_pass()
            assert consolidation.pairs_merged >= 1

            surviving_topic = list(tm._topics.values())[0]
            assert np.allclose(surviving_topic["centroid"], expected_centroid)
        finally:
            self._teardown_db()

    def test_surviving_topic_episode_count_updated(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70, count_a=3, count_b=7)

            consolidation = tm._run_consolidation_pass()
            surviving_topic = list(tm._topics.values())[0]
            assert surviving_topic["episode_count"] == 10
        finally:
            self._teardown_db()

    def test_merged_topic_deleted_from_db(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)
            topic_ids_before = list(tm._topics.keys())
            consolidation = tm._run_consolidation_pass()

            db_topics = get_all_topics(self.conn)
            assert len(db_topics) == len(tm._topics)
            for tid in topic_ids_before:
                if tid not in tm._topics:
                    db_match = [t for t in db_topics if t["id"] == tid]
                    assert len(db_match) == 0
        finally:
            self._teardown_db()

    def test_merged_topic_deleted_from_memory(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)
            topic_ids_before = list(tm._topics.keys())
            consolidation = tm._run_consolidation_pass()

            assert len(tm._topics) == consolidation.topics_after
            assert consolidation.topics_after < consolidation.topics_before
        finally:
            self._teardown_db()


class TestEpisodeReassignment:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def _create_two_similar_topics(self):
        tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)
        ep_ids = []
        for i in range(5):
            ep_id = store_episode(self.conn, f"msg1_{i}", f"r{i}", tm._topics[t1]["centroid"], i + 1)
            self.conn.execute("UPDATE episodes SET topic_id = ? WHERE id = ?", (t1, ep_id))
            self.conn.commit()
            ep_ids.append(ep_id)
        for i in range(5):
            ep_id = store_episode(self.conn, f"msg2_{i}", f"r{i}", tm._topics[t2]["centroid"], i + 6)
            self.conn.execute("UPDATE episodes SET topic_id = ? WHERE id = ?", (t2, ep_id))
            self.conn.commit()
            ep_ids.append(ep_id)
        return tm, t1, t2, ep_ids

    def test_episodes_reassigned_from_merged_to_surviving(self):
        self._setup_db()
        try:
            tm, t1, t2, ep_ids = self._create_two_similar_topics()
            consolidation = tm._run_consolidation_pass()
            surviving_id = list(tm._topics.keys())[0]

            for ep_id in ep_ids:
                cursor = self.conn.execute("SELECT topic_id FROM episodes WHERE id = ?", (ep_id,))
                row = cursor.fetchone()
                assert row[0] == surviving_id
        finally:
            self._teardown_db()

    def test_no_orphaned_episodes_after_merge(self):
        self._setup_db()
        try:
            tm, t1, t2, ep_ids = self._create_two_similar_topics()
            tm._run_consolidation_pass()

            surviving_ids = list(tm._topics.keys())
            cursor = self.conn.execute(
                "SELECT DISTINCT topic_id FROM episodes WHERE topic_id IS NOT NULL"
            )
            ep_topic_ids = set(row[0] for row in cursor.fetchall())
            for tid in ep_topic_ids:
                assert tid in surviving_ids, f"Episode references deleted topic {tid}"
        finally:
            self._teardown_db()


class TestIterationToCompletion:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_iterates_until_no_pairs_remain(self):
        self._setup_db()
        try:
            tm, topic_ids = _create_three_topics_high_sim(self.conn)
            assert tm.topic_count == 3
            consolidation = tm._run_consolidation_pass()
            assert consolidation.pairs_merged >= 2
            assert consolidation.topics_after == 1
        finally:
            self._teardown_db()


class TestConsolidationResult:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_consolidation_result_populated(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)

            consolidation = tm._run_consolidation_pass()
            assert isinstance(consolidation, ConsolidationResult)
            assert consolidation.triggered_at_episode == 10
            assert consolidation.topics_before == 2
            assert consolidation.topics_after == 1
            assert consolidation.pairs_merged == 1
            assert len(consolidation.merge_log) == 1
            entry = consolidation.merge_log[0]
            assert "surviving_label" in entry
            assert "merged_label" in entry
            assert "similarity" in entry
            assert "episodes_reassigned" in entry
        finally:
            self._teardown_db()

    def test_assignment_result_consolidation_none_on_non_consolidation_turn(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)
            episode_id = store_episode(self.conn, "msg", "reply", emb, 1)
            result = tm.assign(episode_id, emb)
            assert result.consolidation is None
        finally:
            self._teardown_db()


class TestReassignEpisodesDb:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_reassign_episodes_returns_count(self):
        self._setup_db()
        try:
            centroid = np.zeros(1024, dtype=np.float32)
            topic_a = store_topic(self.conn, "topic_a", centroid, "2026-01-01T00:00:00+00:00")
            topic_b = store_topic(self.conn, "topic_b", centroid, "2026-01-01T00:00:00+00:00")

            for i in range(3):
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", centroid, i + 1)
                self.conn.execute(
                    "UPDATE episodes SET topic_id = ? WHERE id = ?", (topic_a, episode_id)
                )
                self.conn.commit()

            count = reassign_episodes(self.conn, topic_a, topic_b)
            assert count == 3

            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE topic_id = ?", (topic_a,)
            )
            assert cursor.fetchone()[0] == 0

            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE topic_id = ?", (topic_b,)
            )
            assert cursor.fetchone()[0] == 3
        finally:
            self._teardown_db()


class TestMergeTopicsDb:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_merge_topics_updates_surviving_and_deletes_merged(self):
        self._setup_db()
        try:
            c1 = np.full(1024, 1.0, dtype=np.float32)
            c2 = np.full(1024, 2.0, dtype=np.float32)
            surviving_id = store_topic(self.conn, "topic_a", c1, "2026-01-01T00:00:00+00:00")
            merged_id = store_topic(self.conn, "topic_b", c2, "2026-01-01T00:00:00+00:00")

            new_centroid = np.full(1024, 1.5, dtype=np.float32)
            merge_topics(self.conn, surviving_id, merged_id, new_centroid, 10)

            topics = get_all_topics(self.conn)
            assert len(topics) == 1
            topic = topics[0]
            assert topic["id"] == surviving_id
            recovered = np.frombuffer(topic["centroid"], dtype=np.float32)
            assert np.allclose(recovered, new_centroid)
            assert topic["episode_count"] == 10
        finally:
            self._teardown_db()


class TestGetAllTopicsWithCentroids:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_returns_centroids_as_numpy_arrays(self):
        self._setup_db()
        try:
            centroid = np.full(1024, 3.0, dtype=np.float32)
            store_topic(self.conn, "test", centroid, "2026-01-01T00:00:00+00:00")

            topics = get_all_topics_with_centroids(self.conn)
            assert len(topics) == 1
            topic = topics[0]
            assert isinstance(topic["centroid"], np.ndarray)
            assert np.allclose(topic["centroid"], centroid)
        finally:
            self._teardown_db()

    def test_returns_empty_list_when_no_topics(self):
        self._setup_db()
        try:
            result = get_all_topics_with_centroids(self.conn)
            assert result == []
        finally:
            self._teardown_db()


class TestMergeDirection:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_smaller_topic_merged_into_larger(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70, count_a=7, count_b=3)

            consolidation = tm._run_consolidation_pass()
            surviving_id = list(tm._topics.keys())[0]
            assert surviving_id == t1
            assert tm._topics[surviving_id]["episode_count"] == 10
        finally:
            self._teardown_db()


class TestEpisodeCountPersistence:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_episode_count_initialized_from_db(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)

            for i in range(7):
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                tm.assign(episode_id, emb)

            assert tm._episode_count == 7

            new_tm = TopicManager(self.conn)
            assert new_tm._episode_count == 7
        finally:
            self._teardown_db()

    def test_episode_count_survives_reload_consolidation_correct(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)

            for i in range(10):
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)

            assert result.consolidation is not None
            assert tm._episode_count == 10

            new_tm = TopicManager(self.conn)
            assert new_tm._episode_count == 10

            for i in range(10):
                episode_id = store_episode(self.conn, f"msg_reloaded_{i}", f"reply{i}", emb, i + 11)
                result = new_tm.assign(episode_id, emb)

            assert result.consolidation is not None
            assert result.consolidation.triggered_at_episode == 20
        finally:
            self._teardown_db()


class TestInMemoryMatchesDbAfterConsolidation:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_memory_and_db_consistent_after_consolidation(self):
        self._setup_db()
        try:
            tm, t1, t2 = _create_two_topics_with_similarity(self.conn, 0.70)

            tm._run_consolidation_pass()

            db_topics = get_all_topics(self.conn)
            mem_ids = set(tm._topics.keys())
            db_ids = set(t["id"] for t in db_topics)
            assert mem_ids == db_ids

            for tid in mem_ids:
                mem_topic = tm._topics[tid]
                db_topic = next(t for t in db_topics if t["id"] == tid)
                db_centroid = np.frombuffer(db_topic["centroid"], dtype=np.float32)
                assert np.allclose(mem_topic["centroid"], db_centroid)
                assert mem_topic["episode_count"] == db_topic["episode_count"]
        finally:
            self._teardown_db()
