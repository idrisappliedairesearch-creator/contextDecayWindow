import sqlite3
import uuid
from datetime import datetime, timezone


def store_rule(
    conn: sqlite3.Connection,
    episode_id: str,
    rule_summary: str,
    turn_number: int,
) -> str:
    rule_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO rule_store (id, episode_id, rule_summary, turn_number, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (rule_id, episode_id, rule_summary, turn_number, created_at),
    )
    conn.commit()
    return rule_id


def get_all_rules(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute(
        "SELECT id, episode_id, rule_summary, turn_number, created_at "
        "FROM rule_store ORDER BY turn_number ASC"
    )
    rows = cursor.fetchall()
    columns = ["id", "episode_id", "rule_summary", "turn_number", "created_at"]
    return [dict(zip(columns, row)) for row in rows]
