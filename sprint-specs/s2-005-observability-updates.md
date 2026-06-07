# CDW Sprint S2_005 — Observability Updates

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-05

---

## Objective

Bring the observability layer fully current with Study 002's architectural additions. S2_002, S2_003, and S2_004 each added terminal lines, metric fields, and CSV columns in isolation. This sprint audits every observability surface, closes gaps, and ensures the full terminal block and file output for Study 002 is coherent, complete, and consistent with what the analysis script in S2_009 will consume.

No new architecture. No new DB tables. Observability only.

---

## What Sprint S2_005 Modifies

```
contextDecayWindow/
  src/
    observability/
      turn_record.py    -- AUDITED: confirm all Study 002 fields present
      terminal.py       -- MODIFIED: full Study 002 terminal block
      file_writer.py    -- MODIFIED: all new CSV columns, new files confirmed
  tests/
    test_terminal_s2.py      -- NEW: full Study 002 terminal block
    test_file_writer_s2.py   -- NEW: new CSV columns and files
```

---

## Full Study 002 Terminal Block

This is the canonical terminal output format for Study 002. Every turn produces this exact block. The coding agent must implement this exactly — it is the pre-registered observability format.

```
══════════════════════════════════════════════════════════
TURN 047 | Condition: iterative | Topics: 8 | Store: 47 | Tokens: ~18,240
══════════════════════════════════════════════════════════
[USER] In the context of Keynesian monetary theory, what specific mechanisms...

[RULE STORE] 2 rules pinned (~3,400 tokens) | Rule detected this turn: No

[RETRIEVAL] K=4 above 0.50 | N=10 (cap) + 2 K-only | Store: 47 episodes
  → ep_a3f2b901 | sim: 0.81 | decay: 0.94 | type: KN  | topic: topic_3
  → ep_c7d1e445 | sim: 0.74 | decay: 0.88 | type: KN  | topic: topic_3
  → ep_f902aa31 | sim: 0.67 | decay: 0.41 | type: K   | topic: topic_1
  → ep_b210cc77 | sim: 0.51 | decay: 0.29 | type: K   | topic: topic_1
  (+ 8 N-only episodes not shown — see retrieval.jsonl)

[TOPIC LAYER] Topics: 8 | New node: No | Centroid drift: topic_3=0.031

[CONTEXT BUILT] ~18,240 tokens | Rules: ~3,400 | K: ~6,800 | N: ~8,040
[GENERATION] 44.1 tok/s | ~TTFT: 0.02s | Output: 1,487 tokens
[STORAGE] ep_d771f300 stored | Topic: topic_3 | Embedding: done
[DECAY UPDATED] 12 episodes updated
──────────────────────────────────────────────────────────
[ASSISTANT] Drawing on Keynesian monetary theory, the transmission mechanisms...
══════════════════════════════════════════════════════════
```

### Terminal Display Rules

**Header line:**
- `TURN NNN` — zero-padded to 3 digits
- `Condition: {condition}` — always shown (was absent in Study 001)
- `Topics: N` — current topic node count
- `Store: N` — total episodes in store (n_total_in_store)
- `Tokens: ~N` — estimated tokens for constructed context

**[RULE STORE] line:**
- Always shown, even when 0 rules pinned
- Shows count and token estimate of pinned rules
- Shows whether a rule was detected this turn

**[RETRIEVAL] line:**
- K count and threshold (0.50)
- N count with `(cap)` label when N_RETRIEVAL_CAP is reached
- K-only count (episodes that entered via K but not top-10 N)
- Store size
- Episode detail lines: show K and KN episodes with sim score, decay score, type, topic label
- N-only episodes suppressed from terminal detail (too many) — reference to retrieval.jsonl
- If K=0 and all N-only: show `(10 N-only episodes — see retrieval.jsonl)`

**[TOPIC LAYER] line:**
- Current topic count
- Whether a new node was created this turn
- Centroid drift for topics that changed (suppress zero-drift topics)

**[CONSOLIDATION] line:**
- Shown only when consolidation fires
- Topics before → after, pairs merged
- One detail line per merge (surviving label, merged label, similarity)
- Omitted entirely on non-consolidation turns

**[CONTEXT BUILT] line:**
- Total estimated tokens
- Breakdown: Rules / K / N (K-only tokens, N tokens — not including rules)

**[GENERATION] line:**
- tok/s, ~TTFT (labeled as estimate), output token count

**[STORAGE] line:**
- Episode ID (8 chars), topic assigned, embedding confirmation

**[DECAY UPDATED] line:**
- Count of episodes whose `last_retrieved_at` was updated this turn

**Condition A and B terminal differences:**
- `[RULE STORE]` line still shown (detection runs on all conditions)
- `[RETRIEVAL]` shows `K=0 | N=0 | Store: N/A (full context condition)`
- `[TOPIC LAYER]` shows `N/A (full context condition)`
- `[CONSOLIDATION]` never shown for A or B
- `[CONTEXT BUILT]` shows total tokens only, no breakdown

---

## TurnRecord Audit

Full field list for Study 002 TurnRecord. All fields must be present. Fields added across S2_002, S2_003, S2_004 confirmed here.

```python
@dataclass
class TurnRecord:
    # Identity
    turn_number: int
    condition: str

    # User input
    user_message: str

    # Rule store (S2_002)
    contains_rule: bool = False
    rule_summary: str | None = None
    rule_store_count: int = 0
    rule_token_estimate: int = 0

    # Retrieval (updated S2_003)
    k_count: int = 0
    n_count: int = 0                   # capped at N_RETRIEVAL_CAP
    n_total_in_store: int = 0          # S2_003: full store size
    k_only_count: int = 0              # S2_003: K episodes not in top-10 N
    total_in_context: int = 0
    k_episodes: list[dict] = field(default_factory=list)
    n_episodes: list[dict] = field(default_factory=list)
    estimated_tokens: int = 0
    k_token_estimate: int = 0
    n_token_estimate: int = 0

    # Topic layer
    topic_count: int = 0
    episode_count: int = 0
    new_topic_created: bool = False
    new_topic_label: str | None = None
    centroid_drift: dict[str, float] = field(default_factory=dict)

    # Consolidation (S2_004)
    consolidation_occurred: bool = False
    consolidation_result: ConsolidationResult | None = None

    # Generation
    tokens_per_second: float | None = None
    time_to_first_token: float | None = None
    output_tokens: int | None = None
    assistant_message: str | None = None

    # Storage
    stored_episode_id: str | None = None
    stored_topic_label: str | None = None

    # Compaction (Condition B)
    compaction_occurred: bool = False
    compaction_turn: int | None = None
    history_tokens_before_compaction: int | None = None

    # Context tracking
    previous_context_window: str | None = None
    constructed_prompt: str = ""
```

---

## File Output Audit

Full list of files written per condition run. All must exist after `Observer.init_run()` and be populated correctly after each turn.

### logs/
| File | Content | Format |
|------|---------|--------|
| turns.jsonl | Full TurnRecord per turn | JSONL |
| retrieval.jsonl | Full K, N, KN episode lists per turn | JSONL |
| context_windows.jsonl | Turn number + prompt path reference | JSONL |
| context_diffs.jsonl | Unified diff between consecutive prompts | JSONL |

### metrics/
| File | Content | New in S2 |
|------|---------|-----------|
| model_performance.csv | tok/s, TTFT, output tokens, estimated tokens | No |
| memory_store.csv | topic count, episode count, compaction fields | No |
| K_values.csv | Per K episode: id, sim score, topic, k_only flag | k_only column is new |
| N_values.csv | Per N episode: id, decay score, topic, n_total_in_store | n_total_in_store column is new |
| topic_events.csv | New node creation, centroid drift per turn | No |
| retrieval_events.csv | Per episode per turn: scores, type | No |
| rule_detection.csv | Per turn: contains_rule, summary, parse error | New in S2_002 |
| consolidation_events.csv | Per consolidation pass: before/after/merged | New in S2_004 |

### snapshots/
`turn_NNN_db_state.json` — per turn. Gains two new sections in Study 002:
- `rule_store_count` — number of pinned rules at time of snapshot
- `topic_consolidation_count` — number of consolidation passes that have fired

### rubric/ and constructed_prompts/
Unchanged from Study 001.

---

## Condition Label in Header

Study 001's terminal header did not show which condition was running. This caused confusion during the run — impossible to tell from the terminal output whether you were watching full_context, compaction, or iterative.

Study 002 fixes this. `TURN NNN | Condition: iterative |` is always shown. The study runner prints a condition start banner before the first turn:

```
╔══════════════════════════════════════════════════════════╗
║  STARTING CONDITION: full_context                        ║
║  Run: run_001 | Script: 120 turns | Study: 002           ║
╚══════════════════════════════════════════════════════════╝
```

And a condition complete banner after the last turn:

```
╔══════════════════════════════════════════════════════════╗
║  CONDITION COMPLETE: full_context                        ║
║  32 turns | Peak tokens: ~204,320 | Duration: 14m 22s    ║
╚══════════════════════════════════════════════════════════╝
```

Duration is wall clock time from first turn to last turn for that condition.

---

## Acceptance Criteria

- [ ] Full Study 002 terminal block renders correctly for Condition C
- [ ] Condition A and B terminal blocks render with N/A fields correctly
- [ ] `[RULE STORE]` line present every turn for all conditions
- [ ] `[CONSOLIDATION]` line present only on consolidation turns
- [ ] `[CONSOLIDATION]` line absent on non-consolidation turns
- [ ] `Condition:` shown in header for all three conditions
- [ ] Condition start and complete banners printed by study runner
- [ ] `k_only` column present in `K_values.csv`
- [ ] `n_total_in_store` column present in `N_values.csv`
- [ ] `rule_detection.csv` present and populated from S2_002
- [ ] `consolidation_events.csv` present and populated from S2_004
- [ ] DB snapshots include `rule_store_count` and `topic_consolidation_count`
- [ ] All TurnRecord fields present and correctly typed
- [ ] All prior tests pass — no regressions
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-037 | Audit and confirm full TurnRecord field list — add any missing fields |
| S2-T-038 | Implement full Study 002 terminal block in `terminal.py` including condition label, N/A handling for A and B |
| S2-T-039 | Add condition start and complete banners to `study/runner.py` |
| S2-T-040 | Audit `file_writer.py` — confirm all 8 metric files, correct headers, new columns |
| S2-T-041 | Update DB snapshot structure to include `rule_store_count` and `topic_consolidation_count` |
| S2-T-042 | Write `tests/test_terminal_s2.py` — full Study 002 block for Condition C, N/A rendering for A and B, consolidation line present/absent |
| S2-T-043 | Write `tests/test_file_writer_s2.py` — new CSV columns, new files, snapshot structure |
| S2-T-044 | Run `pytest` — all tests pass |
| S2-T-045 | Commit and push S2_005 |

---

## Out of Scope — S2_005

- Baseline condition runner changes (S2_006)
- Script writing (S2_007)
- Analysis script (S2_009)
- Any architectural changes

---

## Notes for the Coding Agent

**N-only episodes suppressed from terminal detail.** With N capped at 10 and K potentially adding more, the episode detail section could show 12+ lines per turn. Only K and KN episodes are shown in detail — they are the interesting ones, the ones that entered via similarity. N-only episodes are logged to `retrieval.jsonl` but suppressed from terminal display with a count reference. This keeps the terminal readable during a 120-turn run.

**Condition banners are printed by `study/runner.py`, not `Observer`.** The Observer handles per-turn output. The runner handles between-condition output. Duration tracking for the complete banner uses `time.perf_counter()` started at the first turn of each condition.

**The terminal block for Conditions A and B is intentionally sparse.** Showing `N/A (full context condition)` for retrieval and topic fields is not a bug — it's accurate. Conditions A and B have no retrieval mechanism. Showing zeros would be misleading; showing N/A is honest. The analysis script handles N/A values in CSV files by treating them as not applicable, not as missing data.