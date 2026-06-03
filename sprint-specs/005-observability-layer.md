# CDW Sprint 005 — Observability Layer

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-05-31

---

## Objective

Build the full observability infrastructure for Study 001. Every turn produces a structured terminal block and writes to isolated metric files, JSONL logs, DB snapshots, and constructed prompt archives. At the end of this sprint, the study pipeline is fully observable — before the inference model is wired in Sprint 008.

Maximum visibility was pre-registered. This sprint delivers it.

---

## What Sprint 005 Builds

```
contextDecayWindow/
  src/
    db/
      retrieval.py       -- unchanged
      episode.py         -- unchanged
      topic.py           -- unchanged
      schema.py          -- unchanged
    embeddings/
      provider.py        -- unchanged
    memory/
      topic_manager.py   -- MODIFIED: assign() returns AssignmentResult
      retrieval_engine.py -- unchanged
      context_builder.py  -- unchanged
    observability/
      __init__.py        -- NEW
      turn_record.py     -- NEW: TurnRecord and AssignmentResult dataclasses
      terminal.py        -- NEW: TerminalPrinter
      file_writer.py     -- NEW: FileWriter
      observer.py        -- NEW: Observer (orchestrates terminal + file writing)
      run_config.py      -- NEW: RunConfig
  tests/
    test_observer.py     -- NEW
    test_terminal.py     -- NEW
    test_file_writer.py  -- NEW
```

---

## Run Folder Structure

Created once at study start by `Observer.init_run()`. Matches the pre-registration exactly.

```
experiments/study_001/runs/
  run_001_full_context/
  run_001_compaction/
  run_001_iterative/
    logs/
      turns.jsonl
      retrieval.jsonl
      context_windows.jsonl
      context_diffs.jsonl
    metrics/
      model_performance.csv
      memory_store.csv
      K_values.csv
      N_values.csv
      topic_events.csv
      retrieval_events.csv
    snapshots/
      turn_001_db_state.json
      turn_002_db_state.json
      ...
    rubric/
      responses.md
      scores.md
    constructed_prompts/
      turn_001.txt
      turn_002.txt
      ...
```

`rubric/responses.md` and `rubric/scores.md` are created as empty files at run init — placeholders to be filled manually during Sprint 008 (study run) and Sprint 009 (analysis).

---

## TurnRecord — The Accumulator

The central data object for a single turn. Built up incrementally as the pipeline executes. Every module populates its section. The `Observer` flushes it to terminal and files at end of turn.

```python
@dataclass
class TurnRecord:
    # Identity
    turn_number: int
    condition: str              # "full_context" | "compaction" | "iterative"

    # User input
    user_message: str

    # Retrieval (populated by RetrievalEngine)
    k_count: int = 0
    n_count: int = 0
    total_in_context: int = 0
    k_episodes: list[dict] = field(default_factory=list)   # id, sim_score, topic_label
    n_episodes: list[dict] = field(default_factory=list)   # id, decay_score, topic_label
    estimated_tokens: int = 0
    k_token_estimate: int = 0
    n_token_estimate: int = 0

    # Topic layer (populated by TopicManager)
    topic_count: int = 0
    episode_count: int = 0
    new_topic_created: bool = False
    new_topic_label: str | None = None
    centroid_drift: dict[str, float] = field(default_factory=dict)  # topic_label → drift

    # Generation (populated by inference runner — Sprint 008)
    # None values render as "---" in terminal output
    tokens_per_second: float | None = None
    time_to_first_token: float | None = None
    output_tokens: int | None = None
    assistant_message: str | None = None

    # Storage (populated after generation)
    stored_episode_id: str | None = None
    stored_topic_label: str | None = None

    # Computed at flush time
    previous_context_window: str | None = None   # for diff computation
    constructed_prompt: str = ""
```

Generation fields default to None. Sprint 005 terminal output renders them as `---` when None. Sprint 008 populates them when inference is wired.

---

## AssignmentResult — TopicManager Modification

`topic_manager.assign()` currently returns `str` (topic_id). Sprint 005 changes the return type to `AssignmentResult` to expose the data the observability layer needs.

```python
@dataclass
class AssignmentResult:
    topic_id: str
    topic_label: str
    is_new_topic: bool
    centroid_drift: float    # L2 distance between old and new centroid
                             # 0.0 if new topic (no prior centroid to drift from)
```

This is a minor modification to `topic_manager.py`. All existing tests remain valid — update any that assert on the return type.

**Centroid drift formula:**

```python
drift = float(np.linalg.norm(new_centroid - old_centroid))
```

Computed before the centroid is updated. Stored on `AssignmentResult`. 0.0 for new topics.

---

## RunConfig

```python
@dataclass
class RunConfig:
    condition: str           # "full_context" | "compaction" | "iterative"
    run_id: str              # e.g. "run_001"
    output_dir: str          # absolute path to run folder
    study_dir: str           # absolute path to experiments/study_001/runs/
```

`output_dir` is constructed as: `{study_dir}/{run_id}_{condition}/`

---

## Module Specifications

### src/observability/terminal.py

One class: `TerminalPrinter`. One public method: `print_turn(record: TurnRecord)`.

Produces the pre-registered terminal block format exactly:

```
═══════════════════════════════════════════════════════
TURN 04 | Topics: 3 | Episodes: 7 | Tokens: ~4,832
═══════════════════════════════════════════════════════
[USER] We agreed the budget cap was $47,500...

[RETRIEVAL] K=3 above 0.70 | N=7 total episodes
  → ep_a3f2 | sim: 0.84 | decay: 0.92 | topic: topic_1
  → ep_b901 | sim: 0.79 | decay: 0.88 | topic: topic_1
  → ep_c412 | sim: 0.71 | decay: 0.61 | topic: topic_2

[TOPIC LAYER] No new nodes | Centroid drift: topic_1=0.023
[CONTEXT BUILT] ~2,847 tokens | K: ~1,203 | N: ~1,644
[GENERATION] 47.2 tok/s | TTFT: 0.31s | Output: 312 tokens
[STORAGE] ep_d771 stored | Topic: topic_1 | Embedding: done
[DECAY UPDATED] 7 episodes updated
───────────────────────────────────────────────────────
[ASSISTANT] The agreed budget cap was $47,500...
═══════════════════════════════════════════════════════
```

Rules:
- Token counts prefixed with `~` to signal estimate
- Generation fields render as `---` when None (Sprint 005 state before Sprint 008)
- Episode IDs truncated to 8 chars for readability
- User and assistant messages truncated to 120 chars in terminal — full text goes to files
- `[TOPIC LAYER]` line shows `New topic: topic_N created` when `new_topic_created=True`
- Centroid drift shown only for topics that changed — suppress zero-drift topics

### src/observability/file_writer.py

One class: `FileWriter`. Initialized with a `RunConfig`. Manages all file I/O for a run.

**`init_run(config: RunConfig) -> None`**
Creates the full directory structure. Creates empty `rubric/responses.md` and `rubric/scores.md` with placeholder headers. Creates CSV files with headers. Creates empty JSONL log files.

**`write_turn(record: TurnRecord) -> None`**
Called once per turn. Writes all files for that turn:

JSONL logs (append one record per turn):
- `turns.jsonl` — full TurnRecord as JSON (excluding constructed_prompt, use path reference)
- `retrieval.jsonl` — k_episodes, n_episodes, scores, retrieval_type per episode
- `context_windows.jsonl` — turn_number, estimated_tokens, constructed_prompt path
- `context_diffs.jsonl` — turn_number, lines added, lines removed (unified diff vs previous turn)

CSV files (append one row per turn):
- `model_performance.csv` — turn, tokens_per_second, time_to_first_token, output_tokens, estimated_tokens
- `memory_store.csv` — turn, topic_count, episode_count, new_topic_created, new_topic_label
- `K_values.csv` — turn, k_count, episode_id, similarity_score, topic_label (one row per K match)
- `N_values.csv` — turn, n_count, episode_id, decay_score, topic_label (one row per episode)
- `topic_events.csv` — turn, event_type (new_node | centroid_update), topic_label, centroid_drift
- `retrieval_events.csv` — turn, episode_id, similarity_score, decay_score, retrieval_type

Snapshots:
- `snapshots/turn_{NNN}_db_state.json` — full serialized DB state: all episodes (without raw embeddings — store dimension count only), all topics (without raw centroids — store dimension count only), retrieval_event count. Raw vectors excluded for file size.

Constructed prompts:
- `constructed_prompts/turn_{NNN}.txt` — exact prompt text the model received (or will receive)

Turn number formatted as zero-padded 3 digits: `001`, `002`, etc.

### src/observability/observer.py

Thin orchestrator. Owns a `TerminalPrinter` and a `FileWriter`.

```python
class Observer:

    def __init__(self, config: RunConfig):
        ...

    def init_run(self) -> None:
        """Create run folder structure. Call once before first turn."""
        ...

    def flush_turn(self, record: TurnRecord) -> None:
        """Print to terminal and write all files for this turn."""
        ...
```

The `Observer` is the only interface the study runner (Sprint 008) needs. It does not know about terminal or file internals.

---

## Updated Full Turn Sequence After Sprint 005

1. User message arrives
2. `record = TurnRecord(turn_number=N, condition=..., user_message=...)`
3. `retrieval_result = retrieval_engine.retrieve(user_message, turn_number)`
4. Populate `record` from `retrieval_result`
5. Inference model called with `retrieval_result.constructed_prompt` (Sprint 008)
6. Populate `record` generation fields (Sprint 008)
7. `store_episode()` — stores response pair
8. `assignment = topic_manager.assign(episode_id, embedding)`
9. Populate `record` from `assignment`
10. `observer.flush_turn(record)` — terminal + files
11. Return response to user

Steps 5–6 are stubs until Sprint 008. `flush_turn()` renders `---` for unpopulated generation fields.

---

## Acceptance Criteria

- [ ] `Observer.init_run()` creates full directory structure with all subdirectories
- [ ] CSV files created with correct headers
- [ ] JSONL log files created as empty files
- [ ] Rubric placeholder files created with headers
- [ ] `flush_turn()` prints terminal block matching the pre-registered format
- [ ] Generation fields render as `---` when None
- [ ] `turns.jsonl` receives one record per turn
- [ ] `retrieval.jsonl` receives correct K and N episode data per turn
- [ ] `K_values.csv` receives one row per K match (not one row per turn)
- [ ] `N_values.csv` receives one row per episode per turn
- [ ] `topic_events.csv` records new node creation and centroid updates
- [ ] `model_performance.csv` writes `---` for None generation fields
- [ ] `snapshots/turn_001_db_state.json` created after turn 1 with correct structure
- [ ] `constructed_prompts/turn_001.txt` contains exact prompt text
- [ ] `context_diffs.jsonl` records diff between consecutive constructed prompts
- [ ] `topic_manager.assign()` now returns `AssignmentResult` — all prior tests updated and passing
- [ ] Centroid drift is 0.0 for new topic nodes
- [ ] Centroid drift is a positive float for updated topic nodes
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| T-033 | Add `AssignmentResult` dataclass to `topic_manager.py`, update `assign()` return type, update affected tests |
| T-034 | Implement `src/observability/run_config.py` — `RunConfig` dataclass |
| T-035 | Implement `src/observability/turn_record.py` — `TurnRecord` dataclass |
| T-036 | Implement `src/observability/terminal.py` — `TerminalPrinter.print_turn()` |
| T-037 | Implement `src/observability/file_writer.py` — `FileWriter.init_run()` and `write_turn()` |
| T-038 | Implement `src/observability/observer.py` — `Observer.init_run()` and `flush_turn()` |
| T-039 | Write `tests/test_terminal.py` — covers format correctness, None rendering, truncation |
| T-040 | Write `tests/test_file_writer.py` — covers directory creation, CSV headers, JSONL append, snapshot structure, prompt archive |
| T-041 | Write `tests/test_observer.py` — covers end-to-end flush with a fully populated and a partially populated TurnRecord |
| T-042 | Run `pytest` — all tests pass including all prior sprints |
| T-043 | Commit and push Sprint 005 |

---

## Out of Scope — Sprint 005

- Inference model integration (Sprint 008)
- Baseline condition runners (Sprint 006)
- Test script (Sprint 007)
- Populating generation fields (Sprint 008)

---

## Notes for the Coding Agent

**`context_diffs.jsonl`:** Use Python's `difflib.unified_diff()` to compute the diff between `previous_context_window` and the current `constructed_prompt`. Store line counts (added, removed) and the diff string. On turn 1, `previous_context_window` is None — write a `{"turn": 1, "note": "first turn, no diff"}` record.

**CSV None handling:** Write the string `"---"` for None numeric fields in CSVs. Do not write empty strings or skip the cell — `"---"` is explicit and survives pandas import cleanly.

**Snapshot raw vector exclusion:** Raw 1024-dim float32 vectors are ~4KB each. A 50-episode store would add ~200KB per snapshot × 50 turns = ~10MB of redundant data. Exclude raw embeddings and centroids from snapshots. Record `"embedding_dim": 1024` and `"centroid_dim": 1024` as confirmation they exist.

**Terminal truncation:** Truncate user and assistant messages at 120 chars with `...` suffix. Full text lives in `turns.jsonl` and `constructed_prompts/`. The terminal is for live monitoring, not archiving.

**Episode ID display:** Show first 8 chars of UUID only in terminal (e.g. `ep_a3f2b901`). Full UUIDs in all file outputs.