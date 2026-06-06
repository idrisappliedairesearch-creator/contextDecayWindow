import sqlite3
import uuid
from datetime import datetime, timezone

import numpy as np


def store_topic(conn: sqlite3.Connection, label: str, centroid, created_at: str) -> str:
    topic_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO topics (id, label, centroid, episode_count, created_at, last_updated_at)
        VALUES (?, ?, ?, 0, ?, ?)
        """,
        (topic_id, label, centroid.tobytes(), created_at, created_at),
    )
    conn.commit()
    return topic_id


def get_all_topics(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute(
        "SELECT id, label, centroid, episode_count, created_at, last_updated_at "
        "FROM topics"
    )
    rows = cursor.fetchall()
    if not rows:
        return []

    columns = [
        "id", "label", "centroid", "episode_count", "created_at", "last_updated_at"
    ]
    return [dict(zip(columns, row)) for row in rows]


def get_all_topics_with_centroids(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute(
        "SELECT id, label, centroid, episode_count, created_at, last_updated_at "
        "FROM topics"
    )
    rows = cursor.fetchall()
    if not rows:
        return []

    result = []
    for row in rows:
        centroid_bytes = row[2]
        centroid = np.frombuffer(centroid_bytes, dtype=np.float32)
        result.append({
            "id": row[0],
            "label": row[1],
            "centroid": centroid,
            "episode_count": row[3],
            "created_at": row[4],
            "last_updated_at": row[5],
        })
    return result


def update_topic_centroid(
    conn: sqlite3.Connection, topic_id: str, new_centroid, new_episode_count: int
) -> None:
    last_updated_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        UPDATE topics
        SET centroid = ?, episode_count = ?, last_updated_at = ?
        WHERE id = ?
        """,
        (new_centroid.tobytes(), new_episode_count, last_updated_at, topic_id),
    )
    conn.commit()


def reassign_episodes(conn: sqlite3.Connection, from_topic_id: str, to_topic_id: str) -> int:
    cursor = conn.execute(
        """
        UPDATE episodes
        SET topic_id = ?
        WHERE topic_id = ?
        """,
        (to_topic_id, from_topic_id),
    )
    conn.commit()
    return cursor.rowcount


def merge_topics(conn: sqlite3.Connection, surviving_topic_id: str, merged_topic_id: str, new_centroid, new_episode_count: int) -> None:
    last_updated_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        UPDATE topics
        SET centroid = ?, episode_count = ?, last_updated_at = ?
        WHERE id = ?
        """,
        (new_centroid.tobytes(), new_episode_count, last_updated_at, surviving_topic_id),
    )

    conn.execute(
        "DELETE FROM topics WHERE id = ?",
        (merged_topic_id,),
    )
    conn.commit()
