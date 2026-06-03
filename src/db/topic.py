import sqlite3
import uuid
from datetime import datetime, timezone


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
