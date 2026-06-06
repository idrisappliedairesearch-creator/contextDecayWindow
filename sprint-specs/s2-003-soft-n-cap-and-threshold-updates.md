# CDW Sprint S2_003 — Soft N Cap + Threshold Updates

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-05

---

## Objective

Implement the soft N retrieval cap, update the K similarity threshold from 0.70 to 0.50, and update the topic assignment threshold from 0.70 to 0.50. These three changes directly address Study 001's two failure conditions: K retrieval being effectively inactive and the iterative context window exceeding full context.

This sprint is constants and retrieval logic only. No new modules. No new tables.

---

## What Sprint S2_003 Modifies

```
contextDecayWindow/
  src/
    memory/
      retrieval_engine.py  -- MODIFIED: soft N cap, K threshold 0.50
      topic_manager.py     -- MODIFIED: topic threshold 0.50
  tests/
    test_retrieval_engine_s2.py  -- NEW: soft cap behavior
    test_topic_manager_s2.py     -- NEW: threshold behavior at 0.50
```

---

## Threshold Changes

Two constants updated. Both changes documented in pre-registration with explicit reasoning. No ambiguity about why they changed.

### retrieval_engine.py

```python
# Study 001
K_SIMILARITY_THRESHOLD = 0.70

# Study 002
K_SIMILARITY_THRESHOLD = 0.50
# Reduced from 0.70. Study 001: K fired once in 32 turns.
# 0.70 was too strict for Qwen3-Embedding-0.6B's embedding space.
```

### topic_manager.py

```python
# Study 001
TOPIC_SIMILARITY_THRESHOLD = 0.70

# Study 002
TOPIC_SIMILARITY_THRESHOLD = 0.50
# Reduced from 0.70. Study 001: 30 topics created for 30 episodes.
# 0.70 produced singleton topic proliferation with no meaningful consolidation.
```

Constants updated in place. The old value and documented reason appear as a comment directly above the new value — permanently in the codebase as a decision record.

---

## Soft N Cap Implementation

### Definition

```python
N_RETRIEVAL_CAP = 10
# Hard floor of the soft cap. Top 10 decay-sorted episodes always included.
# Additional episodes included if they score above K_SIMILARITY_THRESHOLD
# regardless of whether they appear in the top-10 N set.
# Rule episodes are unconditional and do not count against this cap.
```

### Retrieval Assembly — Updated Logic

```python
def _assemble_context(
    self,
    all_episodes: list[dict],
    query_embedding: np.ndarray,
) -> tuple[list[str], list[str], dict[str, float], dict[str, float]]:
    """
    Returns (k_ids, n_ids, k_scores, n_scores).

    Soft cap logic:
    1. Compute decay scores for all episodes → sort descending → take top N_RETRIEVAL_CAP
       These are the N ids (hard floor of soft cap).
    2. Compute cosine similarity for all episodes → filter above K_SIMILARITY_THRESHOLD
       These are the K ids (uncapped).
    3. Final included set = union(N_ids, K_ids).
       Episodes in both get retrieval_type "KN".
       Episodes only in N get "N".
       Episodes only in K get "K".
    4. Rule episodes handled separately — not part of this assembly.
    """
```

### Key Behavioral Difference from Study 001

Study 001: N retrieval was uncapped — all 30 episodes included by turn 32.
Study 002: N retrieval capped at 10. A highly relevant episode from turn 5 that has decayed out of the top-10 N can still enter context via K retrieval if its embedding similarity to the current query exceeds 0.50.

This is the mechanism that enables middle-plant survival in Condition C. Without the K threshold doing real work, the cap alone would cause early-planted facts to fall out of context entirely. The soft cap ensures both recency (top-10 N) and relevance (K) contribute.

### Context Window Token Budget — Expected Behavior

With N_RETRIEVAL_CAP = 10 and average ~1,700 tokens per episode:

- Rule episodes: ~2 episodes × 1,700 tokens = ~3,400 tokens (constant after turn 2)
- N episodes: 10 × 1,700 tokens = ~17,000 tokens (constant ceiling)
- K episodes: variable, 0–N additional
- Total ceiling: ~20,400 tokens for a turn with no K matches

Compared to Study 001's uncapped peak of 24,854 tokens, and Condition A's predicted 200,000 token peak — the iterative condition stays bounded well below full context.

---

## RetrievalResult Updates

Two fields updated to reflect soft cap behavior:

```python
@dataclass
class RetrievalResult:
    episodes: list[dict]
    k_episode_ids: list[str]
    k_scores: dict[str, float]
    n_episode_ids: list[str]          # now capped at N_RETRIEVAL_CAP
    n_scores: dict[str, float]
    constructed_prompt: str
    estimated_tokens: int
    k_count: int
    n_count: int                       # now reflects cap, not total store size
    n_total_in_store: int              # NEW: total episodes in store regardless of cap
    total_episodes_in_context: int
    rule_episodes: list[dict]
    rule_token_estimate: int
```

`n_total_in_store` is new — it replaces `n_count` as the "total episodes" signal for observability. `n_count` now means "episodes retrieved via N mechanism" (capped at 10). Both are logged to the metric files so the relationship between store size and retrieved set is visible across the run.

---

## Observability Updates

### Terminal Output Change

```
# Study 001 format:
[RETRIEVAL] K=3 above 0.70 | N=7 total episodes

# Study 002 format:
[RETRIEVAL] K=3 above 0.50 | N=10 (cap) + 2 K-only | Store: 47 episodes
```

The terminal now shows:
- K count and threshold
- N count with explicit `(cap)` label when N_RETRIEVAL_CAP is hit
- K-only episodes (those that entered via K but not top-10 N)
- Total episodes in store

### CSV Updates

`N_values.csv` gains one column: `n_total_in_store` per turn.
`K_values.csv` gains one column: `k_only` (bool — true if episode entered via K but not top-10 N).

---

## Acceptance Criteria

- [ ] `K_SIMILARITY_THRESHOLD` updated to 0.50 in `retrieval_engine.py` with documented comment
- [ ] `TOPIC_SIMILARITY_THRESHOLD` updated to 0.50 in `topic_manager.py` with documented comment
- [ ] `N_RETRIEVAL_CAP = 10` defined in `retrieval_engine.py` with documented comment
- [ ] N retrieval returns exactly top 10 episodes when store has > 10 episodes
- [ ] N retrieval returns all episodes when store has ≤ 10 episodes
- [ ] K retrieval returns all episodes above 0.50 regardless of N cap
- [ ] Episodes above 0.50 that are not in top-10 N are included in final set
- [ ] Episodes in both K and N get `retrieval_type = "KN"`
- [ ] Episodes only in top-10 N get `retrieval_type = "N"`
- [ ] Episodes only in K (above cap) get `retrieval_type = "K"`
- [ ] Rule episodes not counted in N cap
- [ ] `n_count` reflects capped N set size
- [ ] `n_total_in_store` reflects full store size
- [ ] Terminal shows updated format with store size and K-only count
- [ ] `N_values.csv` includes `n_total_in_store` column
- [ ] `K_values.csv` includes `k_only` column
- [ ] All prior tests pass — no regressions on Study 001 test suite
- [ ] All acceptance criteria verified by new tests

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-014 | Update `K_SIMILARITY_THRESHOLD` to 0.50 in `retrieval_engine.py` with documented comment |
| S2-T-015 | Update `TOPIC_SIMILARITY_THRESHOLD` to 0.50 in `topic_manager.py` with documented comment |
| S2-T-016 | Define `N_RETRIEVAL_CAP = 10` in `retrieval_engine.py` with documented comment |
| S2-T-017 | Implement soft cap assembly logic in `RetrievalEngine._assemble_context()` |
| S2-T-018 | Add `n_total_in_store` field to `RetrievalResult` |
| S2-T-019 | Update terminal format in `terminal.py` for new retrieval display |
| S2-T-020 | Update `N_values.csv` and `K_values.csv` in `file_writer.py` for new columns |
| S2-T-021 | Write `tests/test_retrieval_engine_s2.py` — covers cap enforcement, K-only episodes, KN dedup, retrieval_type assignment, n_total_in_store |
| S2-T-022 | Write `tests/test_topic_manager_s2.py` — covers assignment at 0.50 threshold, topic creation at below-threshold similarity |
| S2-T-023 | Run `pytest` — all tests pass |
| S2-T-024 | Commit and push S2_003 |

---

## Out of Scope — S2_003

- Topic consolidation (S2_004)
- Additional observability files beyond CSV column additions (S2_005)
- Rule store integration already handled in S2_002
- Script writing (S2_007)
- Any changes to Condition A or B runners

---

## Notes for the Coding Agent

**Soft cap assembly order matters.** Compute decay scores and take top-10 first. Then compute K similarity scores. Then take the union. Do not compute K scores only on the top-10 N set — K must scan the entire episode store so non-top-10 episodes can still enter via similarity.

**Single DB fetch.** `get_all_episodes_with_embeddings()` is called once per turn. Both N and K computations operate on this single fetched list. Do not make separate DB calls for N and K. This was established in Study 001 and remains unchanged.

**`n_count` vs `n_total_in_store` distinction is non-negotiable for observability.** Study 001's terminal showed `N=7 total episodes` when there were 7 episodes in the store. Study 002 must distinguish between `N=10 (cap)` (retrieved) and `Store: 47 episodes` (total). The analysis script uses both values to track cap saturation across the run — the point at which `n_count` stops growing while `n_total_in_store` continues is the point where K retrieval must compensate.

**Threshold comments are permanent documentation.** The comments above `K_SIMILARITY_THRESHOLD`, `TOPIC_SIMILARITY_THRESHOLD`, and `N_RETRIEVAL_CAP` explaining why the value changed from Study 001 are not cleanup candidates. They are architectural history. Do not remove them.