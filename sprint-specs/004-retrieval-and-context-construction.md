# CDW Sprint 004 — Retrieval + Context Construction

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-05-31

---

## Objective

Implement the retrieval mechanism and context construction layer. At each turn, the system queries the memory store using two complementary mechanisms — K retrieval by semantic similarity, N retrieval by decay score — deduplicates the results, assembles them chronologically, and constructs the active prompt ready to send to the inference model.

At the end of this sprint, given a user message, the system produces a fully constructed prompt from memory. The inference model is not called yet — that is Sprint 008.

---

## What Sprint 004 Builds

```
contextDecayWindow/
  src/
    db/
      schema.py          -- unchanged
      episode.py         -- unchanged
      topic.py           -- unchanged
      retrieval.py       -- NEW: DB operations for retrieval logging and updates
    embeddings/
      provider.py        -- unchanged
    memory/
      __init__.py        -- unchanged
      topic_manager.py   -- unchanged
      retrieval_engine.py -- NEW: K and N retrieval logic, decay computation
      context_builder.py  -- NEW: prompt assembly, token estimation
  tests/
    test_retrieval_db.py      -- NEW
    test_retrieval_engine.py  -- NEW
    test_context_builder.py   -- NEW
```

---

## Decay Function

Exponential decay over time since last retrieval. Defined once in `retrieval_engine.py` as constants — never hardcoded inline.

```python
DECAY_RATE = 0.1          # per hour — gentle decay suited to single-session study runs
K_SIMILARITY_THRESHOLD = 0.70   # mirrors TOPIC_SIMILARITY_THRESHOLD from Sprint 003
```

Formula:

```
decay_score = exp(-DECAY_RATE * hours_since_last_retrieval)
```

Where `hours_since_last_retrieval` is computed from `last_retrieved_at` to current UTC time.

**Null handling:** If `last_retrieved_at` is NULL (episode has never been retrieved), `decay_score = 1.0` — treat as maximally fresh. The episode was activated at storage time.

**Range:** decay_score is always in (0.0, 1.0]. It approaches 0 asymptotically and equals 1.0 only when `last_retrieved_at` is NULL.

---

## Retrieval Mechanism

### K Retrieval

1. Embed the incoming user message
2. Compute cosine similarity between query embedding and every episode embedding in the store
3. Return all episodes where similarity ≥ `K_SIMILARITY_THRESHOLD` (0.70)
4. No top-K cap — all qualifying episodes included
5. Records: episode_id and similarity_score for each match

### N Retrieval

1. Fetch all episodes from the store
2. Compute decay_score fresh for each episode from `last_retrieved_at`
3. Sort descending by decay_score
4. Return all episodes (no threshold, no cap — all N included)
5. Records: episode_id and decay_score for each

### Deduplication and Assembly

1. Take the union of K and N episode sets by episode_id
2. Sort the unified set chronologically by `turn_number` ascending
3. Chronological ordering preserves narrative coherence — this is non-negotiable

### Post-Retrieval DB Updates

After assembly, before returning results:

1. Update `last_retrieved_at` to current UTC timestamp for every episode in the final set
2. Increment `retrieval_count` by 1 for every episode in the final set
3. Write one `retrieval_events` row per episode, recording `similarity_score`, `decay_score`, and `retrieval_type`

`retrieval_type` values:
- `"K"` — appeared in K retrieval only
- `"N"` — appeared in N retrieval only
- `"KN"` — appeared in both

---

## RetrievalResult

The retrieval engine returns a structured result object carrying everything Sprint 005 needs for observability.

```python
@dataclass
class RetrievalResult:
    episodes: list[dict]            # chronologically ordered, deduplicated
    k_episode_ids: list[str]        # episode IDs that cleared the K threshold
    k_scores: dict[str, float]      # episode_id → similarity_score (K matches only)
    n_episode_ids: list[str]        # all episode IDs from N retrieval, ordered by decay
    n_scores: dict[str, float]      # episode_id → decay_score (all episodes)
    constructed_prompt: str         # ready to send to inference model
    estimated_tokens: int           # character-based estimate: len(prompt) // 4
    k_count: int                    # number of K matches
    n_count: int                    # total episodes in store (= N count)
    total_episodes_in_context: int  # deduplicated count
```

Token estimation uses `len(prompt) // 4` — a character-based approximation sufficient for Study 001 observability. Precise tokenization via llama-cpp-python is deferred; this estimate is clearly labeled as an estimate in all output.

---

## Module Specifications

### src/db/retrieval.py

Four functions:

**`get_all_episodes_with_embeddings(conn) -> list[dict]`**
Returns all episodes including their embeddings deserialized to numpy arrays. Used by both K and N retrieval. Single DB call per turn.

**`update_retrieval_metadata(conn, episode_ids: list[str], retrieved_at: str) -> None`**
Sets `last_retrieved_at` to `retrieved_at` and increments `retrieval_count` by 1 for all given episode IDs. Batch update — single DB call.

**`log_retrieval_event(conn, turn_number, episode_id, similarity_score, decay_score, retrieval_type) -> None`**
Writes one row to `retrieval_events`. Called once per retrieved episode per turn.

**`log_retrieval_events_batch(conn, events: list[dict]) -> None`**
Batch version of the above. Preferred for performance. Each dict has keys: `turn_number`, `episode_id`, `similarity_score`, `decay_score`, `retrieval_type`.

### src/memory/retrieval_engine.py

```python
class RetrievalEngine:

    def __init__(self, conn: sqlite3.Connection, embedding_provider):
        ...

    def retrieve(self, user_message: str, turn_number: int) -> RetrievalResult:
        """
        Full retrieval pipeline for one turn.
        Embeds query, runs K and N retrieval, deduplicates, assembles,
        updates DB metadata, logs retrieval events.
        Returns RetrievalResult.
        """
        ...

    def _k_retrieve(self, query_embedding: np.ndarray, all_episodes: list[dict]) -> tuple[list[str], dict[str, float]]:
        """
        Returns (k_episode_ids, k_scores) for episodes above threshold.
        """
        ...

    def _n_retrieve(self, all_episodes: list[dict]) -> tuple[list[str], dict[str, float]]:
        """
        Returns (n_episode_ids_sorted_by_decay, n_scores) for all episodes.
        """
        ...

    def _compute_decay(self, last_retrieved_at: str | None) -> float:
        """
        Computes decay score from last_retrieved_at timestamp.
        Returns 1.0 if last_retrieved_at is None.
        """
        ...

    def _deduplicate_and_sort(self, all_episodes: list[dict], included_ids: set[str]) -> list[dict]:
        """
        Filters all_episodes to included_ids, sorts by turn_number ascending.
        """
        ...
```

### src/memory/context_builder.py

```python
def build_prompt(episodes: list[dict], system_prompt: str) -> str:
    """
    Assembles the constructed context prompt from retrieved episodes.

    Format:
        {system_prompt}

        --- RETRIEVED CONVERSATION HISTORY ---
        [Turn {turn_number}]
        User: {user_message}
        Assistant: {assistant_message}

        [Turn {turn_number}]
        ...
        --- END HISTORY ---

        User: {current_user_message}

    Note: current_user_message is NOT included here — it is passed
    separately by the inference runner in Sprint 008. This function
    builds the history block only.
    """
    ...

def estimate_tokens(text: str) -> int:
    """
    Character-based token estimate: len(text) // 4.
    Clearly labeled as estimate — not used for hard limits.
    """
    return len(text) // 4
```

---

## Full Turn Sequence After Sprint 004

1. User submits message
2. `retrieval_engine.retrieve(user_message, turn_number)` →
   a. Embed user message
   b. Fetch all episodes from DB
   c. K retrieval — similarity ≥ 0.70
   d. N retrieval — all episodes sorted by decay
   e. Deduplicate and sort chronologically
   f. Update `last_retrieved_at` and `retrieval_count` in DB
   g. Log retrieval events to DB
   h. Build constructed prompt via `context_builder.build_prompt()`
   i. Return `RetrievalResult`
3. Inference model receives constructed prompt (Sprint 008)
4. `store_episode()` — stores response pair with embedding
5. `topic_manager.assign()` — assigns to topic
6. Return response to user

---

## Acceptance Criteria

- [ ] `retrieve()` returns a `RetrievalResult` with all fields populated
- [ ] K retrieval returns only episodes with similarity ≥ 0.70 — verified with known embeddings
- [ ] K retrieval returns empty list when no episodes clear the threshold
- [ ] N retrieval returns all episodes sorted by decay score descending
- [ ] Episode with NULL `last_retrieved_at` receives decay_score = 1.0
- [ ] Decay score decreases as `last_retrieved_at` moves further into the past — verified numerically
- [ ] Deduplication: episode in both K and N appears once in final set
- [ ] Assembly: final episode list is sorted by `turn_number` ascending — not by score
- [ ] `retrieval_type` is `"K"`, `"N"`, or `"KN"` correctly assigned per episode
- [ ] `last_retrieved_at` updated in DB for all retrieved episodes after `retrieve()` call
- [ ] `retrieval_count` incremented in DB for all retrieved episodes after `retrieve()` call
- [ ] `retrieval_events` rows written to DB — one per episode per turn
- [ ] `build_prompt()` produces correctly formatted output with turn numbers visible
- [ ] `estimate_tokens()` returns `len(text) // 4`
- [ ] `DECAY_RATE` and `K_SIMILARITY_THRESHOLD` constants defined once — no inline values
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| T-025 | Implement `src/db/retrieval.py` — all four functions |
| T-026 | Implement `src/memory/retrieval_engine.py` — `RetrievalEngine` and `RetrievalResult` |
| T-027 | Implement `src/memory/context_builder.py` — `build_prompt()` and `estimate_tokens()` |
| T-028 | Write `tests/test_retrieval_db.py` — covers all retrieval DB functions |
| T-029 | Write `tests/test_retrieval_engine.py` — covers K retrieval, N retrieval, decay, deduplication, assembly, DB updates |
| T-030 | Write `tests/test_context_builder.py` — covers prompt format, turn number visibility, token estimate |
| T-031 | Run `pytest` — all tests pass including all prior sprints |
| T-032 | Commit and push Sprint 004 |

---

## Out of Scope — Sprint 004

- Inference model calls (Sprint 008)
- Terminal observability output (Sprint 005)
- Metric file writing (Sprint 005)
- DB snapshot writing (Sprint 005)
- Baseline conditions — full context and compaction (Sprint 006)
- Test script (Sprint 007)

---

## Notes for the Coding Agent

**Single DB fetch per turn:** `get_all_episodes_with_embeddings()` is called once per turn and the result is passed to both `_k_retrieve()` and `_n_retrieve()`. Do not make two separate DB calls. At study scale (30–50 episodes) this is trivially fast.

**Embedding deserialization:** sqlite-vec returns vector columns as raw bytes. Deserialize to numpy float32 arrays before any similarity computation. This was established in Sprint 002 — follow the same pattern.

**Decay rate and study duration:** `DECAY_RATE = 0.1` per hour means an episode last retrieved 10 hours ago scores ≈ 0.37. Study 001 runs in a single session — decay differences will be subtle within a session. This is expected and correct. Decay is a sort signal in Study 001, not a gate.

**`build_prompt()` does not include the current user message.** The inference runner (Sprint 008) appends it. This keeps context construction and inference cleanly separated.

**`RetrievalResult` is a dataclass.** Import from `dataclasses` — no external dependency needed.