import sqlite3
import sqlite_vec


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS episodes (
            id                TEXT PRIMARY KEY,
            topic_id          TEXT,
            user_message      TEXT NOT NULL,
            assistant_message TEXT NOT NULL,
            embedding         vec_float32(1024) NOT NULL,
            turn_number       INTEGER NOT NULL,
            created_at        TEXT NOT NULL,
            last_retrieved_at TEXT,
            retrieval_count   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS topics (
            id                TEXT PRIMARY KEY,
            label             TEXT NOT NULL,
            centroid          vec_float32(1024) NOT NULL,
            episode_count     INTEGER NOT NULL DEFAULT 0,
            created_at        TEXT NOT NULL,
            last_updated_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS retrieval_events (
            id                TEXT PRIMARY KEY,
            turn_number       INTEGER NOT NULL,
            episode_id        TEXT NOT NULL,
            similarity_score  REAL NOT NULL,
            decay_score       REAL NOT NULL,
            retrieval_type    TEXT NOT NULL,
            retrieved_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rule_store (
            id              TEXT PRIMARY KEY,
            episode_id      TEXT NOT NULL,
            rule_summary    TEXT NOT NULL,
            turn_number     INTEGER NOT NULL,
            created_at      TEXT NOT NULL
        );
    """)

    conn.commit()
    return conn
