# CDW Sprint 003 — Topic Layer

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-05-31

---

## Objective

Implement the topic layer — the hippocampal index of the memory store. Every episode gets assigned to a topic node at storage time. Topic nodes maintain a running-average centroid embedding. A live in-memory index makes assignment fast without hitting the database on every turn.

At the end of this sprint, storing an episode automatically assigns it to an existing topic or creates a new one. The database and in-memory state stay in sync.

---

## What Sprint 003 Builds

```
contextDecayWindow/
  src/
    db/
      schema.py        -- unchanged
      episode.py       -- add update_episode_topic()
      topic.py         -- NEW: store_topic(), get_all_topics(), update_topic_centroid()
    embeddings/
      provider.py      -- unchanged
    memory/
      __init__.py      -- NEW
      topic_manager.py -- NEW: TopicManager
  tests/
    test_topic_db.py       -- NEW
    test_topic_manager.py  -- NEW
```

---

## Assignment Logic

Pre-registered rule, implemented exactly as specified:

1. Embed the new episode (already done before this call)
2. Compute cosine similarity between the episode embedding and every topic centroid in the in-memory index
3. If any topic scores ≥ 0.70 → assign to the highest-scoring topic
4. If no topic scores ≥ 0.70 → create a new topic node
5. Update centroid (running average) for the assigned topic
6. Update `episode_count` and `last_updated_at` on the topic
7. Write `topic_id` back to the episode row

Threshold 0.70 is a constant defined once in `topic_manager.py` as `TOPIC_SIMILARITY_THRESHOLD = 0.70`. It is referenced by name throughout — never hardcoded inline.

---

## Centroid Update Formula

Running average — applied on every new episode assignment:

```
new_centroid = (old_centroid * episode_count + new_embedding) / (episode_count + 1)
```

`episode_count` used here is the count *before* the new episode is added. After the update, `episode_count` is incremented by 1.

This is a pure numpy operation. No model call required.

---

## Module Specifications

### src/db/topic.py

New module. Three functions:

**`store_topic(conn, label, centroid, created_at) -> str`**
- Generates UUID4 for id
- Sets `episode_count = 0`
- Sets `last_updated_at = created_at`
- Returns the topic id

**`get_all_topics(conn) -> list[dict]`**
- Returns all topic rows as a list of dicts
- Returns empty list if no topics exist
- Used at startup to populate the in-memory index

**`update_topic_centroid(conn, topic_id, new_centroid, new_episode_count) -> None`**
- Updates `centroid`, `episode_count`, and `last_updated_at` for the given topic_id
- `last_updated_at` set to current UTC timestamp

### src/db/episode.py

Add one function to the existing module:

**`update_episode_topic(conn, episode_id, topic_id) -> None`**
- Sets `topic_id` on the given episode row
- Called after topic assignment, before the turn completes

### src/memory/topic_manager.py

Central class for all topic layer logic. Owns the in-memory index.

```python
class TopicManager:

    TOPIC_SIMILARITY_THRESHOLD = 0.70

    def __init__(self, conn: sqlite3.Connection):
        # Load all existing topics from DB into memory at init
        # Store centroids as numpy arrays for fast similarity computation
        ...

    def assign(self, episode_id: str, embedding: np.ndarray) -> str:
        """
        Assign an episode to a topic. Creates a new topic if no match.
        Updates centroid, episode_count, last_updated_at in DB and in memory.
        Writes topic_id back to episode row.
        Returns the topic_id assigned.
        """
        ...

    def _find_best_match(self, embedding: np.ndarray) -> tuple[str | None, float]:
        """
        Returns (topic_id, similarity_score) for the best matching topic.
        Returns (None, 0.0) if no topics exist.
        """
        ...

    def _create_topic(self, embedding: np.ndarray) -> str:
        """
        Creates a new topic node. Label derived from embedding index
        (e.g. "topic_1", "topic_2") — simple, deterministic, no LLM call.
        Adds to DB and in-memory index.
        Returns the new topic_id.
        """
        ...

    def _update_centroid(self, topic_id: str, new_embedding: np.ndarray) -> None:
        """
        Applies running average centroid update.
        Updates DB and in-memory index.
        """
        ...

    @property
    def topic_count(self) -> int:
        """Number of topic nodes currently in the index."""
        ...
```

**In-memory index structure:**

```python
# Internal representation inside TopicManager
_topics: dict[str, dict] = {
    topic_id: {
        "label": str,
        "centroid": np.ndarray,   # shape (1024,), float32
        "episode_count": int,
        "created_at": str,
        "last_updated_at": str,
    }
}
```

The in-memory index is the source of truth for assignment decisions. The DB is the persistence layer. They must stay in sync after every `assign()` call.

**Label convention:**
Labels are auto-generated as `topic_1`, `topic_2`, etc. Sequential, based on total topic count at creation time. Deterministic, human-readable for log output. No LLM call for label generation in Study 001.

---

## Updated Storage Flow

The full episode storage sequence after Sprint 003:

1. User submits message
2. Generate assistant response (inference model)
3. Embed the response pair (embedding model)
4. `store_episode()` — writes row with `topic_id = NULL`
5. `topic_manager.assign()` — assigns topic, updates centroid, writes `topic_id` back
6. Return response to user

Steps 3–5 happen before the response is returned. Step 5 is what Sprint 003 adds.

---

## Acceptance Criteria

- [ ] First episode stored creates `topic_1` — no existing topics to match against
- [ ] Second episode with similar embedding (sim ≥ 0.70) is assigned to `topic_1`, not a new topic
- [ ] Second episode with dissimilar embedding (sim < 0.70) creates `topic_2`
- [ ] Centroid of `topic_1` updates correctly after second assignment (running average verified numerically)
- [ ] `episode_count` on topic increments correctly after each assignment
- [ ] `topic_id` is written back to the episode row in the database
- [ ] In-memory index matches database state after every `assign()` call
- [ ] `TopicManager` initialized from existing DB state correctly — topics loaded on startup
- [ ] `TopicManager` initialized on empty DB starts with no topics and creates `topic_1` on first assignment
- [ ] `TOPIC_SIMILARITY_THRESHOLD` constant used everywhere — no inline 0.70 values
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| T-018 | Implement `src/db/topic.py` — `store_topic()`, `get_all_topics()`, `update_topic_centroid()` |
| T-019 | Add `update_episode_topic()` to `src/db/episode.py` |
| T-020 | Implement `src/memory/topic_manager.py` — `TopicManager` with full assignment logic |
| T-021 | Write `tests/test_topic_db.py` — covers `store_topic()`, `get_all_topics()`, `update_topic_centroid()` |
| T-022 | Write `tests/test_topic_manager.py` — covers new topic creation, assignment to existing, centroid update, DB/memory sync, startup from existing DB |
| T-023 | Run `pytest` — all tests pass including Sprint 002 tests |
| T-024 | Commit and push Sprint 003 |

---

## Out of Scope — Sprint 003

- Retrieval logic (Sprint 004)
- Decay scoring (Sprint 004)
- Context window assembly (Sprint 004)
- Observability and terminal output (Sprint 005)
- Any inference call to the main Qwen3.6 27B model
- LLM-generated topic labels (explicitly deferred — simple sequential labels only)

---

## Notes for the Coding Agent

**Centroid storage in sqlite-vec:** Store centroids as `vec_float32(1024)` matching the episodes table. When loading topics into memory via `get_all_topics()`, deserialize the centroid back to a numpy array — sqlite-vec returns raw bytes for vector columns.

**In-memory sync discipline:** Every write to the DB in `TopicManager` must be immediately followed by the equivalent update to `_topics`. If the DB write fails, do not update memory. Keep these paired — a diverged in-memory index is the primary failure mode to guard against.

**Thread safety:** Not required for Study 001. Single-threaded execution. Do not add locks or async machinery.

**Startup behavior:** `TopicManager.__init__()` calls `get_all_topics()` and populates `_topics`. If the DB is empty, `_topics` starts as an empty dict. The first `assign()` call will create `topic_1`.