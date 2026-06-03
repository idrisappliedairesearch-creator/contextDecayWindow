import sqlite3
import uuid
from datetime import datetime, timezone


def store_episode(
    conn: sqlite3.Connection,
    user_message: str,
    assistant_message: str,
    embedding,
    turn_number: int,
) -> str:
    episode_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO episodes (
            id, topic_id, user_message, assistant_message,
            embedding, turn_number, created_at,
            last_retrieved_at, retrieval_count
        ) VALUES (?, NULL, ?, ?, ?, ?, ?, NULL, 0)
        """,
        (
            episode_id,
            user_message,
            assistant_message,
            embedding.tobytes(),
            turn_number,
            created_at,
        ),
    )
    conn.commit()
    return episode_id


def get_episode_by_id(conn: sqlite3.Connection, episode_id: str):
    cursor = conn.execute(
        "SELECT id, topic_id, user_message, assistant_message, "
        "embedding, turn_number, created_at, last_retrieved_at, "
        "retrieval_count FROM episodes WHERE id = ?",
        (episode_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [
        "id", "topic_id", "user_message", "assistant_message",
        "embedding", "turn_number", "created_at", "last_retrieved_at",
        "retrieval_count",
    ]
    return dict(zip(columns, row))
