import sqlite3
import struct
from datetime import datetime, timezone

import numpy as np

from src.db.episode import update_episode_topic
from src.db.topic import store_topic, get_all_topics, update_topic_centroid
from src.embeddings.provider import cosine_similarity


class TopicManager:

    TOPIC_SIMILARITY_THRESHOLD = 0.70

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._topics: dict[str, dict] = {}
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

    def assign(self, episode_id: str, embedding: np.ndarray) -> str:
        embedding = np.asarray(embedding, dtype=np.float32)
        best_topic_id, best_score = self._find_best_match(embedding)

        if best_topic_id is not None and best_score >= self.TOPIC_SIMILARITY_THRESHOLD:
            topic_id = best_topic_id
        else:
            topic_id = self._create_topic(embedding)

        self._update_centroid(topic_id, embedding)
        update_episode_topic(self._conn, episode_id, topic_id)
        return topic_id

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

    def _update_centroid(self, topic_id: str, new_embedding: np.ndarray) -> None:
        topic = self._topics[topic_id]
        old_centroid = topic["centroid"]
        old_count = topic["episode_count"]

        new_centroid = (old_centroid * old_count + new_embedding) / (old_count + 1)
        new_count = old_count + 1

        update_topic_centroid(self._conn, topic_id, new_centroid, new_count)

        topic["centroid"] = new_centroid
        topic["episode_count"] = new_count
        topic["last_updated_at"] = datetime.now(timezone.utc).isoformat()

    @property
    def topic_count(self) -> int:
        return len(self._topics)
