# CDW Sprint S2_004 — Topic Consolidation

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-05

---

## Objective

Implement post-assignment topic consolidation. Every 10 stored episodes, the system scans all topic centroids for pairs with cosine similarity ≥ 0.60, merges redundant topics, and reassigns their episodes. This directly addresses Study 001's 30-topics-for-30-episodes failure — the topic layer produced no meaningful compression because every episode created its own node.

---

## What Sprint S2_004 Builds

```
contextDecayWindow/
  src/
    db/
      topic.py           -- MODIFIED: merge_topics(), reassign_episodes()
    memory/
      topic_manager.py   -- MODIFIED: consolidation pass logic
    observability/
      turn_record.py     -- MODIFIED: consolidation fields
      terminal.py        -- MODIFIED: [CONSOLIDATION] terminal line
      file_writer.py     -- MODIFIED: consolidation_events.csv
  tests/
    test_consolidation.py     -- NEW
    test_topic_manager_s2b.py -- NEW: consolidation integration
```

---

## Consolidation Design

### Trigger

Consolidation fires after the episode store reaches a multiple of 10:

```python
CONSOLIDATION_INTERVAL = 10
CONSOLIDATION_MERGE_THRESHOLD = 0.60
# 0.60 justification: above assignment threshold (0.50) to avoid merging
# topics that are merely related. Below Study 001's assignment threshold
# (0.70) to catch topics that have grown genuinely redundant over time.
```

The trigger check runs inside `TopicManager.assign()` after storage and assignment complete:

```python
if self._episode_count % CONSOLIDATION_INTERVAL == 0:
    self._run_consolidation_pass()
```

Where `_episode_count` is the total number of episodes stored since the run started. Fires at episodes 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120.

### Consolidation Pass Algorithm

```
1. Fetch all topic centroids from in-memory index
2. Compute pairwise cosine similarity between all topic centroids
3. Find all pairs with similarity ≥ CONSOLIDATION_MERGE_THRESHOLD
4. For each qualifying pair — merge smaller into larger (by episode_count):
   a. Compute new centroid: weighted average by episode_count
      new_centroid = (centroid_A * count_A + centroid_B * count_B) / (count_A + count_B)
   b. Update surviving topic centroid and episode_count in DB and memory
   c. Reassign all episodes from merged topic to surviving topic in DB
   d. Delete merged topic from DB and memory index
5. Repeat until no qualifying pairs remain
   (single pass may create new qualifying pairs after merges — iterate to completion)
6. Log consolidation event to consolidation_events.csv
```

**Iteration to completion:** After each merge, recompute similarities for the updated surviving centroid against remaining topics. Continue until a full scan finds no pairs above threshold. In practice, with 120 episodes and 15-20 topic nodes, this converges in 1-3 iterations per consolidation pass.

### Merge Direction

Always merge the topic with fewer episodes into the topic with more episodes. On a tie, merge the more recently created topic into the older one. The surviving topic retains its id, label, and creation timestamp. Its centroid and episode_count are updated.

---

## New DB Functions — src/db/topic.py

**`merge_topics(conn, surviving_topic_id, merged_topic_id, new_centroid, new_episode_count) -> None`**
- Updates `centroid` and `episode_count` on surviving topic
- Updates `last_updated_at` to current UTC
- Deletes merged topic row
- Does not move episodes — that is `reassign_episodes()`

**`reassign_episodes(conn, from_topic_id, to_topic_id) -> int`**
- Updates `topic_id` on all episodes where `topic_id = from_topic_id`
- Returns count of reassigned episodes
- Called before `merge_topics()` so no orphaned episodes exist

**`get_all_topics_with_centroids(conn) -> list[dict]`**
- Returns all topics including centroid deserialized to numpy array
- Used by consolidation pass for pairwise similarity computation
- Distinct from existing `get_all_topics()` which may not deserialize vectors

---

## TopicManager Modifications

```python
class TopicManager:

    CONSOLIDATION_INTERVAL = 10
    CONSOLIDATION_MERGE_THRESHOLD = 0.60

    def assign(self, episode_id: str, embedding: np.ndarray) -> AssignmentResult:
        # ... existing assignment logic ...
        self._episode_count += 1
        if self._episode_count % self.CONSOLIDATION_INTERVAL == 0:
            consolidation_result = self._run_consolidation_pass()
        else:
            consolidation_result = None
        # return AssignmentResult with consolidation_result attached

    def _run_consolidation_pass(self) -> ConsolidationResult:
        """
        Runs the full consolidation algorithm.
        Returns ConsolidationResult for observability logging.
        """
        ...

    def _find_merge_pairs(self) -> list[tuple[str, str, float]]:
        """
        Returns list of (topic_id_a, topic_id_b, similarity) for all pairs
        above CONSOLIDATION_MERGE_THRESHOLD. Sorted by similarity descending.
        """
        ...

    def _merge_pair(self, surviving_id: str, merged_id: str) -> None:
        """
        Executes one merge operation. Updates DB and in-memory index.
        """
        ...
```

### ConsolidationResult Dataclass

```python
@dataclass
class ConsolidationResult:
    triggered_at_episode: int
    topics_before: int
    topics_after: int
    pairs_merged: int
    merge_log: list[dict]    # [{surviving_label, merged_label, similarity, episodes_reassigned}]
```

### AssignmentResult Update

```python
@dataclass
class AssignmentResult:
    topic_id: str
    topic_label: str
    is_new_topic: bool
    centroid_drift: float
    consolidation: ConsolidationResult | None   # NEW — None if no consolidation this turn
```

---

## Observability

### TurnRecord Additions

```python
consolidation_occurred: bool = False
consolidation_result: ConsolidationResult | None = None
```

### Terminal Output

When consolidation fires:

```
[CONSOLIDATION] Episode 20 trigger | Topics: 14 → 11 | Merged: 3 pairs
  → topic_3 + topic_7 (sim: 0.68) → topic_3 | 4 episodes reassigned
  → topic_9 + topic_12 (sim: 0.64) → topic_9 | 2 episodes reassigned
  → topic_1 + topic_15 (sim: 0.61) → topic_1 | 1 episode reassigned
```

When consolidation fires but no pairs qualify:

```
[CONSOLIDATION] Episode 30 trigger | No pairs above 0.60 | Topics unchanged: 11
```

When consolidation does not fire (most turns):

No consolidation line in terminal output. Silence is correct — do not print a "no consolidation" line every turn.

### New Metric File: consolidation_events.csv

```
episode_count_at_trigger, turn_number, topics_before, topics_after,
pairs_merged, surviving_labels, merged_labels, similarities, episodes_reassigned
```

One row per consolidation pass. Empty if consolidation never fires (shouldn't happen in a 120-turn study with 12 trigger points).

---

## Acceptance Criteria

- [ ] Consolidation fires at episodes 10, 20, 30 — verified in tests
- [ ] Consolidation does not fire at episodes 9, 11, 15 — verified in tests
- [ ] Pairs above 0.60 similarity are merged correctly
- [ ] Pairs below 0.60 similarity are not merged
- [ ] Surviving topic centroid updated to weighted average
- [ ] Surviving topic episode_count updated correctly
- [ ] Merged topic deleted from DB and in-memory index
- [ ] Episodes reassigned from merged topic to surviving topic in DB
- [ ] No orphaned episodes after merge (topic_id references non-existent topic)
- [ ] Iterates to completion — re-scans after each merge
- [ ] `ConsolidationResult` populated correctly
- [ ] `AssignmentResult.consolidation` is None on non-consolidation turns
- [ ] `[CONSOLIDATION]` terminal line appears only on consolidation turns
- [ ] No terminal output on non-consolidation turns
- [ ] `consolidation_events.csv` written with one row per consolidation pass
- [ ] In-memory index matches DB state after every consolidation pass
- [ ] All prior tests pass — no regressions
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-025 | Add `merge_topics()`, `reassign_episodes()`, `get_all_topics_with_centroids()` to `src/db/topic.py` |
| S2-T-026 | Add `ConsolidationResult` dataclass to `src/memory/topic_manager.py` |
| S2-T-027 | Implement `_run_consolidation_pass()`, `_find_merge_pairs()`, `_merge_pair()` in `TopicManager` |
| S2-T-028 | Add consolidation trigger to `TopicManager.assign()` |
| S2-T-029 | Update `AssignmentResult` with `consolidation` field |
| S2-T-030 | Add consolidation fields to `TurnRecord` in `turn_record.py` |
| S2-T-031 | Add `[CONSOLIDATION]` terminal output to `terminal.py` |
| S2-T-032 | Add `consolidation_events.csv` to `file_writer.py` |
| S2-T-033 | Write `tests/test_consolidation.py` — covers trigger timing, merge logic, centroid math, episode reassignment, iteration to completion, no-merge case |
| S2-T-034 | Write `tests/test_topic_manager_s2b.py` — consolidation integration with full assign() flow |
| S2-T-035 | Run `pytest` — all tests pass |
| S2-T-036 | Commit and push S2_004 |

---

## Out of Scope — S2_004

- Observability additions beyond consolidation_events.csv (S2_005)
- Script writing (S2_007)
- Any changes to Condition A or B runners
- GABA mechanism

---

## Notes for the Coding Agent

**Pairwise similarity is O(n²) in topic count.** With a well-functioning consolidation mechanism and threshold of 0.50, topic count should stay well below 20 across a 120-turn study. O(n²) over 20 topics is trivially fast — 190 similarity computations. Do not optimize prematurely.

**Iterate to completion — not just one pass.** After merging topic A into topic B, the new topic B centroid may now be above threshold with topic C. A single scan would miss this. The outer loop must continue until a full scan of all remaining pairs finds no qualifying matches.

**Orphan check.** After every consolidation pass, assert that no episodes have a `topic_id` pointing to a deleted topic. This can be a debug-mode assertion, not production enforcement. If it fires, the merge order has a bug.

**In-memory index is the source of truth for the pass.** Pairwise similarity is computed from in-memory centroids (numpy arrays), not from DB. After each merge, update the in-memory centroid immediately before the next similarity scan in the iteration. The DB is updated in parallel but the pass logic operates on memory.

**`_episode_count` must survive TopicManager initialization from an existing DB.** If the study runner restarts from a partially completed run, `_episode_count` must be initialized from the actual episode count in the DB, not from zero. Add this to `TopicManager.__init__()`.