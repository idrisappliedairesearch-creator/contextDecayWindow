# CDW Sprint S2_006 — Baseline Updates + Runner Integration

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-05

---

## Objective

Wire all Study 002 architectural changes into the study runner and iterative runner. Verify Condition A and B runners handle 120 turns correctly. Confirm compaction rule detection does not false-positive on compaction summary calls. Produce an end-to-end mock study run across all three conditions as the acceptance gate.

This is the integration sprint — everything built in S2_002 through S2_005 comes together here.

---

## What Sprint S2_006 Modifies

```
contextDecayWindow/
  src/
    runners/
      iterative_runner.py   -- MODIFIED: integrates rule store write
      compaction_runner.py  -- MODIFIED: suppresses rule detection on compaction call
    study/
      runner.py             -- MODIFIED: 120-turn support, rule store init,
                            --   IterativeRunner v2 initialization
  tests/
    test_iterative_runner_s2.py  -- NEW: rule store integration
    test_study_runner_s2.py      -- NEW: 5-turn mock, all three conditions
```

---

## IterativeRunner Updates

The IterativeRunner from Study 001 depends on:
- `RetrievalEngine` — updated in S2_003 (soft cap, threshold 0.50)
- `TopicManager` — updated in S2_003 and S2_004 (threshold 0.50, consolidation)
- `EmbeddingProvider` — unchanged
- `Observer` — updated in S2_005

These dependencies are injected at construction time. The runner itself needs one change: after `store_episode()`, check `InferenceResult.contains_rule` and call `store_rule()` if true.

```python
def on_turn_complete(
    self,
    user_message: str,
    assistant_message: str,
    turn_number: int,
    embedding: np.ndarray,
    inference_result: InferenceResult,    # NEW parameter — carries rule detection
) -> AssignmentResult:
    episode_id = store_episode(
        self._conn, user_message, assistant_message, embedding, turn_number
    )
    if inference_result.contains_rule and inference_result.rule_summary:
        store_rule(
            self._conn,
            episode_id,
            inference_result.rule_summary,
            turn_number,
        )
    assignment = self._topic_manager.assign(episode_id, embedding)
    return assignment
```

`on_turn_complete` gains `inference_result` as a parameter. The study runner passes it. This is the only meaningful change to the runner itself — everything else flows through the updated dependencies.

---

## CompactionRunner — Rule Detection Suppression

The compaction summary call (`_run_compaction()`) uses the same `InferenceProvider`. The detection instruction is baked into the provider's system prompt. This means the compaction summary prompt will also receive the detection instruction and may produce a `<rule_detection>` tag.

The compaction summary prompt asks the model to summarize conversation history — it does not establish behavioral rules. In practice `contains_rule` should be `False` for compaction calls. However, relying on model behavior for correctness is not acceptable when a simple suppression is available.

**Fix:** `InferenceProvider` gains an optional `suppress_rule_detection: bool = False` parameter on `complete()`:

```python
def complete(
    self,
    prompt: str,
    suppress_rule_detection: bool = False,
) -> InferenceResult:
```

When `suppress_rule_detection=True`:
- The rule detection instruction is not appended to this specific call's system prompt
- `contains_rule` is forced to `False`
- `rule_summary` is forced to `None`
- No tag parsing attempted

`CompactionRunner._run_compaction()` calls `inference_provider.complete(prompt, suppress_rule_detection=True)`.

All other calls (study runner, iterative runner) use the default `suppress_rule_detection=False`.

---

## StudyRunner Updates

### 120-Turn Support

Study 001 runner assumed 32 turns. Study 002 requires 120. The runner reads turn count from the loaded script — no hardcoded limit. `script_loader.load_script()` validation already accepts any count ≥ 30. No change needed there.

The progress display in the condition banner adds a turn counter:

```
TURN 047 / 120 | Condition: iterative | ...
```

This is a minor addition to the terminal header — `TURN NNN / TOTAL` instead of `TURN NNN`.

### IterativeRunner Initialization

Study 002 runner initializes IterativeRunner with the rule store connection:

```python
# Condition C initialization
db_path = os.path.join(run_config.output_dir, "study.db")
conn = init_db(db_path)
embedding_provider = EmbeddingProvider()
topic_manager = TopicManager(conn)
retrieval_engine = RetrievalEngine(conn, embedding_provider)
runner = IterativeRunner(
    conn=conn,
    embedding_provider=embedding_provider,
    topic_manager=topic_manager,
    retrieval_engine=retrieval_engine,
    observer=observer,
)
```

No new parameters — the conn already carries the rule_store table created by `init_db()` in S2_002. `store_rule()` and `get_all_rules()` use the same connection.

### InferenceResult Threading

The study runner must thread `InferenceResult` through to `on_turn_complete()` for Condition C:

```python
# Inside _run_condition() for iterative:
prompt, record = runner.build_context(user_message, turn_number)
full_prompt = f"{prompt}\n\nUser: {user_message}\nAssistant:"
result = inference_provider.complete(full_prompt)
record.tokens_per_second = result.tokens_per_second
record.time_to_first_token = result.time_to_first_token
record.output_tokens = result.output_tokens
record.assistant_message = result.assistant_message
record.contains_rule = result.contains_rule
record.rule_summary = result.rule_summary

assignment = runner.on_turn_complete(
    user_message=user_message,
    assistant_message=result.assistant_message,
    turn_number=turn_number,
    embedding=embedding_provider.embed(f"User: {user_message}\nAssistant: {result.assistant_message}"),
    inference_result=result,
)
```

For Conditions A and B, `inference_result` is passed to `on_turn_complete()` but `contains_rule` is logged only — no rule storage in those conditions. The detection still runs (all conditions use the same inference provider) but only Condition C acts on the result.

---

## Rubric Response File — 120 Turns

`_write_rubric_responses()` in Study 001 wrote turns 25–32. Study 002 rubric turns are 112–120. The method must be updated to reference the correct turn range from the pre-registration.

```python
RUBRIC_TURNS = list(range(112, 121))   # turns 112–120 inclusive
```

Hardcoded in `runner.py` as a named constant — not computed dynamically.

---

## End-to-End Mock Test

`tests/test_study_runner_s2.py` runs a 5-turn mock study across all three conditions. The mock script:

```json
{
  "study": "study_002_mock",
  "system_prompt": "You are a helpful assistant.",
  "turns": [
    {"turn": 1, "user": "Always respond in bullet points. This is a rule."},
    {"turn": 2, "user": "What is the capital of France?"},
    {"turn": 3, "user": "Name three types of bridges."},
    {"turn": 4, "user": "What rule did I establish at the start?"},
    {"turn": 5, "user": "Summarize everything we discussed."}
  ]
}
```

Turn 1 is designed to trigger rule detection. The mock verifies:
- Rule detected on turn 1 (contains_rule=True)
- Rule stored in rule_store table for Condition C
- Rule not stored for Conditions A and B
- Compaction call suppresses rule detection
- All three conditions complete 5 turns without error
- Run folders created for all three conditions
- All metric files written

---

## Acceptance Criteria

- [ ] `IterativeRunner.on_turn_complete()` calls `store_rule()` when `contains_rule=True`
- [ ] `IterativeRunner.on_turn_complete()` does not call `store_rule()` when `contains_rule=False`
- [ ] `CompactionRunner._run_compaction()` uses `suppress_rule_detection=True`
- [ ] `InferenceProvider.complete(suppress_rule_detection=True)` forces `contains_rule=False`
- [ ] StudyRunner reads turn count from script — no hardcoded 32-turn limit
- [ ] Terminal header shows `TURN NNN / TOTAL` format
- [ ] `RUBRIC_TURNS = list(range(112, 121))` defined in runner.py
- [ ] `_write_rubric_responses()` writes turns 112–120
- [ ] 5-turn mock study runs end-to-end for all three conditions without error
- [ ] Rule detected and stored correctly in mock (turn 1)
- [ ] Compaction call does not store a rule
- [ ] All prior tests pass — no regressions
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-046 | Add `suppress_rule_detection` parameter to `InferenceProvider.complete()` |
| S2-T-047 | Update `CompactionRunner._run_compaction()` to pass `suppress_rule_detection=True` |
| S2-T-048 | Update `IterativeRunner.on_turn_complete()` — add `inference_result` parameter, call `store_rule()` conditionally |
| S2-T-049 | Update `StudyRunner._run_condition()` — thread `InferenceResult` through to `on_turn_complete()` |
| S2-T-050 | Update `StudyRunner._write_rubric_responses()` — `RUBRIC_TURNS = list(range(112, 121))` |
| S2-T-051 | Update terminal header to `TURN NNN / TOTAL` format |
| S2-T-052 | Update `MockInferenceProvider` in `conftest.py` — add `suppress_rule_detection` parameter, return `contains_rule=True` on first call only (simulates turn 1 rule detection) |
| S2-T-053 | Write `tests/test_iterative_runner_s2.py` — rule store integration, store_rule called correctly |
| S2-T-054 | Write `tests/test_study_runner_s2.py` — 5-turn mock, all three conditions, rule detection verified |
| S2-T-055 | Run `pytest` — all tests pass |
| S2-T-056 | Commit and push S2_006 |

---

## Out of Scope — S2_006

- Script writing (S2_007)
- Actual study run (S2_008)
- Analysis (S2_009)
- Any further architectural changes

---

## Notes for the Coding Agent

**`suppress_rule_detection` is per-call, not per-provider.** The system prompt baked into the provider still contains the detection instruction. `suppress_rule_detection=True` simply skips tag parsing and forces the result fields to False/None. The tag may still appear in raw output for compaction calls — it is just ignored. This is cleaner than modifying the system prompt per call.

**Rule storage is Condition C only by design.** Conditions A and B detect rules (the InferenceProvider runs for all conditions) but do not write to the rule store. This is intentional — the rule_store table only exists in Condition C's DB. Do not attempt to write rules in the Condition A or B run loop. The `contains_rule` field on TurnRecord is logged for all conditions for observability purposes.

**The 5-turn mock script is not the study script.** It exists only for testing. Do not commit it to `experiments/study_002/`. It lives in `tests/fixtures/mock_script_s2.json` or inline in the test file.

**`MockInferenceProvider` must be updated, not replaced.** The existing mock from Study 001 returns deterministic responses. For Study 002 tests, it gains `suppress_rule_detection` support and returns `contains_rule=True` only on the first call in a session — simulating a single rule-establishment turn. All other calls return `contains_rule=False`. This mirrors realistic behavior without requiring the real model.