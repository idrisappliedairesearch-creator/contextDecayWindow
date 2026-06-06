import sqlite3
from datetime import datetime, timezone
from itertools import combinations

import numpy as np

from src.db.episode import update_episode_topic
from src.db.topic import store_topic, get_all_topics, update_topic_centroid, merge_topics, reassign_episodes
from src.embeddings.provider import cosine_similarity
from src.observability.turn_record import AssignmentResult, ConsolidationResult


class TopicManager:

    TOPIC_SIMILARITY_THRESHOLD = 0.50
    CONSOLIDATION_INTERVAL = 10
    CONSOLIDATION_MERGE_THRESHOLD = 0.60

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._topics: dict[str, dict] = {}
        self._episode_count: int = 0
        self._load_topics()

    def _load_topics(self):
        rows = get_all_topics(self._conn)
        for row in rows:
            centroid = np.frombuffer(row["centroid"], dtype=np.float32)
            self._topics[row["id"]] = {
                "label": row["label"],
                "centroid": centroid,
                "episode_count": row["episode_count"],
                "created_at": row["created_at"],
                "last_updated_at": row["last_updated_at"],
            }
        self._episode_count = self._count_episodes_in_db()

    def _count_episodes_in_db(self) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) FROM episodes")
        row = cursor.fetchone()
        return row[0] if row else 0

    def assign(self, episode_id: str, embedding: np.ndarray) -> AssignmentResult:
        embedding = np.asarray(embedding, dtype=np.float32)
        best_topic_id, best_score = self._find_best_match(embedding)

        is_new = False
        if best_topic_id is not None and best_score >= self.TOPIC_SIMILARITY_THRESHOLD:
            topic_id = best_topic_id
        else:
            topic_id = self._create_topic(embedding)
            is_new = True

        centroid_drift = self._update_centroid(topic_id, embedding, is_new)
        update_episode_topic(self._conn, episode_id, topic_id)
        self._episode_count += 1

        consolidation = None
        if self._episode_count % self.CONSOLIDATION_INTERVAL == 0:
            consolidation = self._run_consolidation_pass()

        topic = self._topics[topic_id]
        return AssignmentResult(
            topic_id=topic_id,
            topic_label=topic["label"],
            is_new_topic=is_new,
            centroid_drift=centroid_drift,
            consolidation=consolidation,
        )

    def _find_best_match(self, embedding: np.ndarray) -> tuple[str | None, float]:
        if not self._topics:
            return None, 0.0

        best_id = None
        best_score = 0.0

        for topic_id, topic in self._topics.items():
            score = cosine_similarity(embedding, topic["centroid"])
            if score > best_score:
                best_score = score
                best_id = topic_id

        return best_id, best_score

    def _create_topic(self, embedding: np.ndarray) -> str:
        topic_num = len(self._topics) + 1
        label = f"topic_{topic_num}"
        created_at = datetime.now(timezone.utc).isoformat()
        topic_id = store_topic(self._conn, label, embedding, created_at)

        self._topics[topic_id] = {
            "label": label,
            "centroid": embedding.copy(),
            "episode_count": 0,
            "created_at": created_at,
            "last_updated_at": created_at,
        }
        return topic_id

    def _update_centroid(self, topic_id: str, new_embedding: np.ndarray, is_new_topic: bool) -> float:
        topic = self._topics[topic_id]
        old_centroid = topic["centroid"]
        old_count = topic["episode_count"]

        new_centroid = (old_centroid * old_count + new_embedding) / (old_count + 1)

        if is_new_topic:
            drift = 0.0
        else:
            drift = float(np.linalg.norm(new_centroid - old_centroid))

        update_topic_centroid(self._conn, topic_id, new_centroid, old_count + 1)

        topic["centroid"] = new_centroid
        topic["episode_count"] = old_count + 1
        topic["last_updated_at"] = datetime.now(timezone.utc).isoformat()

        return drift

    def _run_consolidation_pass(self) -> ConsolidationResult:
        topics_before = len(self._topics)
        merge_log: list[dict] = []

        while True:
            pairs = self._find_merge_pairs()
            if not pairs:
                break
            id_a, id_b, similarity = pairs[0]
            surviving_id, merged_id = self._determine_merge_direction(id_a, id_b)
            merge_info = self._merge_pair(surviving_id, merged_id, similarity)
            merge_log.append(merge_info)

        topics_after = len(self._topics)

        return ConsolidationResult(
            triggered_at_episode=self._episode_count,
            topics_before=topics_before,
            topics_after=topics_after,
            pairs_merged=len(merge_log),
            merge_log=merge_log,
        )

    def _find_merge_pairs(self) -> list[tuple[str, str, float]]:
        topic_ids = list(self._topics.keys())
        pairs = []
        for id_a, id_b in combinations(topic_ids, 2):
            sim = cosine_similarity(
                self._topics[id_a]["centroid"],
                self._topics[id_b]["centroid"],
            )
            if sim >= self.CONSOLIDATION_MERGE_THRESHOLD:
                pairs.append((id_a, id_b, sim))
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs

    def _determine_merge_direction(self, id_a: str, id_b: str) -> tuple[str, str]:
        topic_a = self._topics[id_a]
        topic_b = self._topics[id_b]

        count_a = topic_a["episode_count"]
        count_b = topic_b["episode_count"]

        if count_a > count_b:
            return id_a, id_b
        elif count_b > count_a:
            return id_b, id_a
        else:
            created_a = topic_a["created_at"]
            created_b = topic_b["created_at"]
            if created_a <= created_b:
                return id_a, id_b
            else:
                return id_b, id_a

    def _merge_pair(self, surviving_id: str, merged_id: str, similarity: float) -> dict:
        surviving = self._topics[surviving_id]
        merged = self._topics[merged_id]

        surviving_count = surviving["episode_count"]
        merged_count = merged["episode_count"]
        total_count = surviving_count + merged_count

        new_centroid = (
            surviving["centroid"] * surviving_count + merged["centroid"] * merged_count
        ) / total_count

        reassigned = reassign_episodes(self._conn, merged_id, surviving_id)
        merge_topics(self._conn, surviving_id, merged_id, new_centroid, total_count)

        surviving["centroid"] = new_centroid
        surviving["episode_count"] = total_count
        surviving["last_updated_at"] = datetime.now(timezone.utc).isoformat()
        del self._topics[merged_id]

        return {
            "surviving_label": surviving["label"],
            "merged_label": merged["label"],
            "similarity": similarity,
            "episodes_reassigned": reassigned,
        }

    @property
    def topic_count(self) -> int:
        return len(self._topics)
