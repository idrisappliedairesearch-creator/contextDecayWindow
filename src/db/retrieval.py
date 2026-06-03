import sqlite3
import uuid
from datetime import datetime, timezone


def get_all_episodes_with_embeddings(conn: sqlite3.Connection) -> list:
    cursor = conn.execute(
        "SELECT id, topic_id, user_message, assistant_message, "
        "embedding, turn_number, created_at, last_retrieved_at, "
        "retrieval_count FROM episodes ORDER BY turn_number ASC"
    )
    columns = [
        "id", "topic_id", "user_message", "assistant_message",
        "embedding", "turn_number", "created_at", "last_retrieved_at",
        "retrieval_count",
    ]
    episodes = []
    for row in cursor.fetchall():
        ep = dict(zip(columns, row))
        ep["embedding"] = ep["embedding"]
        episodes.append(ep)
    return episodes


def update_retrieval_metadata(
    conn: sqlite3.Connection,
    episode_ids: list,
    retrieved_at: str,
) -> None:
    for episode_id in episode_ids:
        conn.execute(
            "UPDATE episodes SET last_retrieved_at = ?, retrieval_count = retrieval_count + 1 "
            "WHERE id = ?",
            (retrieved_at, episode_id),
        )
    conn.commit()


def log_retrieval_event(
    conn: sqlite3.Connection,
    turn_number: int,
    episode_id: str,
    similarity_score: float,
    decay_score: float,
    retrieval_type: str,
) -> None:
    event_id = str(uuid.uuid4())
    retrieved_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO retrieval_events "
        "(id, turn_number, episode_id, similarity_score, decay_score, retrieval_type, retrieved_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_id, turn_number, episode_id, similarity_score, decay_score, retrieval_type, retrieved_at),
    )
    conn.commit()


def log_retrieval_events_batch(
    conn: sqlite3.Connection,
    events: list,
) -> None:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for event in events:
        event_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO retrieval_events "
            "(id, turn_number, episode_id, similarity_score, decay_score, retrieval_type, retrieved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                event["turn_number"],
                event["episode_id"],
                event["similarity_score"],
                event["decay_score"],
                event["retrieval_type"],
                retrieved_at,
            ),
        )
    conn.commit()
