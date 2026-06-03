# CDW Sprint 002 — Database + Embedding Layer

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-05-31

---

## Objective

Establish the full project harness and implement the two foundational layers the rest of the system depends on: the SQLite + sqlite-vec database with the locked schema, and the Qwen3-Embedding-0.6B inference provider running on CPU via llama-cpp-python.

At the end of this sprint, the system can embed a string and store and retrieve an episode. Nothing more.

---

## Project Setup (one-time, this sprint)

### Directory Structure

```
contextDecayWindow/
  experiments/
    study_001/
      pre_registration.md
  sprint-specs/
    001-sprint-spec.md
    002-sprint-spec.md
  src/
    __init__.py
    db/
      __init__.py
      schema.py
      episode.py
    embeddings/
      __init__.py
      provider.py
  tests/
    __init__.py
    test_db.py
    test_embeddings.py
  .gitignore
  pyproject.toml
  README.md
```

### pyproject.toml

```toml
[project]
name = "context-decay-window"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "llama-cpp-python>=0.3.0",
    "sqlite-vec>=0.1.0",
    "numpy>=1.26.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
]
```

### .gitignore

```
__pycache__/
*.py[cod]
*.egg-info/
.venv/
*.db
*.gguf
models/
experiments/study_001/runs/
*.log
.DS_Store
```

Note: `.gguf` model files are excluded from the repo. The embedding model path is configured via environment variable at runtime.

---

## Environment Variables

Two variables required before running anything:

```
CDW_EMBEDDING_MODEL_PATH   absolute path to Qwen3-Embedding-0.6B GGUF file
CDW_DB_PATH                absolute path to SQLite database file (e.g. /home/muzaffer/cdw/study_001.db)
```

These are read at module initialization. The system raises a clear error if either is missing.

---

## Module Specifications

### src/db/schema.py

Responsibilities:
- Define the three-table schema
- Expose `init_db(db_path: str) -> sqlite3.Connection`
- Load the sqlite-vec extension on every connection

Tables match the pre-registration schema exactly. Vector columns use sqlite-vec's `vec_float32` type at dimension 1024.

```python
# Table definitions (pseudo-schema for spec clarity)

episodes:
    id                TEXT PRIMARY KEY          -- UUID4
    topic_id          TEXT                      -- FK → topics.id, nullable until Sprint 003
    user_message      TEXT NOT NULL
    assistant_message TEXT NOT NULL
    embedding         vec_float32(1024) NOT NULL
    turn_number       INTEGER NOT NULL
    created_at        TEXT NOT NULL             -- ISO 8601
    last_retrieved_at TEXT                      -- ISO 8601, null until first retrieval
    retrieval_count   INTEGER NOT NULL DEFAULT 0

topics:
    id                TEXT PRIMARY KEY          -- UUID4
    label             TEXT NOT NULL
    centroid          vec_float32(1024) NOT NULL
    episode_count     INTEGER NOT NULL DEFAULT 0
    created_at        TEXT NOT NULL             -- ISO 8601
    last_updated_at   TEXT NOT NULL             -- ISO 8601

retrieval_events:
    id                TEXT PRIMARY KEY          -- UUID4
    turn_number       INTEGER NOT NULL
    episode_id        TEXT NOT NULL             -- FK → episodes.id
    similarity_score  REAL NOT NULL
    decay_score       REAL NOT NULL
    retrieval_type    TEXT NOT NULL             -- "K" or "N"
    retrieved_at      TEXT NOT NULL             -- ISO 8601
```

`init_db()` is idempotent — safe to call on an existing database. Uses `CREATE TABLE IF NOT EXISTS`.

`topic_id` on episodes is nullable in this sprint because topic assignment is Sprint 003. Episodes written in Sprint 002 tests will have `topic_id = NULL` temporarily.

### src/db/episode.py

Responsibilities:
- `store_episode(conn, user_message, assistant_message, embedding, turn_number) -> str`
  - Generates UUID4 for id
  - Sets `created_at` to current UTC timestamp
  - Sets `last_retrieved_at` to NULL
  - Sets `retrieval_count` to 0
  - Sets `topic_id` to NULL (assigned in Sprint 003)
  - Returns the episode id
- `get_episode_by_id(conn, episode_id: str) -> dict | None`
  - Returns full episode row as a dict
  - Returns None if not found

No retrieval logic in this module. Retrieval is Sprint 004.

### src/embeddings/provider.py

Responsibilities:
- Load Qwen3-Embedding-0.6B GGUF via llama-cpp-python on CPU
- Expose `embed(text: str) -> np.ndarray` — returns shape (1024,), dtype float32
- Expose `cosine_similarity(a: np.ndarray, b: np.ndarray) -> float`
- Singleton pattern — model loads once at process start, not per call

```python
# Key llama-cpp-python initialization for embedding mode
Llama(
    model_path=CDW_EMBEDDING_MODEL_PATH,
    embedding=True,       # embedding mode
    n_gpu_layers=0,       # CPU only — do not change
    n_ctx=512,            # sufficient for episode pairs
    verbose=False,
)
```

`cosine_similarity` is a pure numpy operation — no model call required. Lives here because it is always used alongside embeddings.

---

## Acceptance Criteria

- [ ] `uv sync` installs all dependencies cleanly from a fresh clone
- [ ] `init_db()` creates the database file with all three tables
- [ ] `init_db()` is idempotent — second call does not error or corrupt
- [ ] `embed("hello world")` returns a numpy array of shape (1024,) and dtype float32
- [ ] Embedding model runs on CPU — GPU VRAM is unaffected
- [ ] `store_episode()` writes a row to the episodes table and returns a valid UUID
- [ ] `get_episode_by_id()` retrieves the stored row and all fields match
- [ ] `cosine_similarity(a, a)` returns 1.0 for any vector a
- [ ] `cosine_similarity(a, b)` returns a value in range [-1.0, 1.0]
- [ ] Both environment variables raise a clear, descriptive error if missing
- [ ] All acceptance criteria verified by tests in `tests/test_db.py` and `tests/test_embeddings.py`

---

## Tasks

| ID | Description |
|----|-------------|
| T-006 | Create directory structure as specified |
| T-007 | Write `pyproject.toml` |
| T-008 | Write `.gitignore` |
| T-009 | Run `uv sync` — confirm clean install |
| T-010 | Implement `src/db/schema.py` — `init_db()` with sqlite-vec extension loading |
| T-011 | Implement `src/db/episode.py` — `store_episode()` and `get_episode_by_id()` |
| T-012 | Download Qwen3-Embedding-0.6B GGUF — confirm path, set `CDW_EMBEDDING_MODEL_PATH` |
| T-013 | Implement `src/embeddings/provider.py` — singleton loader, `embed()`, `cosine_similarity()` |
| T-014 | Write `tests/test_db.py` — covers `init_db()` idempotency, `store_episode()`, `get_episode_by_id()` |
| T-015 | Write `tests/test_embeddings.py` — covers output shape, dtype, cosine_similarity edge cases |
| T-016 | Run `pytest` — all tests pass |
| T-017 | Commit and push Sprint 002 |

---

## Out of Scope — Sprint 002

- Topic assignment (Sprint 003)
- Topic layer and centroid management (Sprint 003)
- K retrieval and N decay retrieval (Sprint 004)
- Context window assembly (Sprint 004)
- Observability and terminal output (Sprint 005)
- Any inference call to the main Qwen3.6 27B model

---

## Notes for the Coding Agent

**sqlite-vec extension loading:** sqlite-vec ships as a native extension. Load it with `conn.enable_load_extension(True)` then `sqlite_vec.load(conn)`. Do this inside `init_db()` and on every new connection — the extension does not persist across connections.

**Embedding model GGUF:** Qwen3-Embedding-0.6B is available on HuggingFace as a GGUF. Download the Q8_0 quantization — it is small (~660MB) and runs comfortably on CPU. Store it outside the repo (excluded by .gitignore). Set `CDW_EMBEDDING_MODEL_PATH` to its absolute path.

**n_ctx for embeddings:** 512 tokens is sufficient for a response pair. Episode pairs in this study will not approach that limit.

**Do not run the embedding model on GPU.** `n_gpu_layers=0` is non-negotiable. The main inference model owns the GPU. This is an architectural constraint from the pre-registration.