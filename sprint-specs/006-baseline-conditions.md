# CDW Sprint 006 — Baseline Conditions

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-05-31

---

## Objective

Implement the two baseline condition runners — full context loading (Condition A) and summarization compaction (Condition B). Both produce context prompts and populate TurnRecord for the observability layer. Neither calls the inference model — that is Sprint 008. At the end of this sprint, all three conditions can build context and be observed. The study runner just needs to wire inference.

---

## Design Decision — Compaction Threshold

Not specified in pre-registration (implementation detail of the baseline, not the architecture under study). Locked here before any code is written.

```python
COMPACTION_THRESHOLD_TOKENS = 3000
```

Reasoning: the study script is 30+ turns. At roughly 100–200 estimated tokens per turn pair, full history reaches 3000 tokens around turn 15–20. This guarantees at least one compaction event mid-study — the exact failure mode being tested. A higher threshold risks no compaction occurring during the run, making Condition B indistinguishable from Condition A.

**Compaction prompt** — what is sent to the model when compaction triggers:

```
You are summarizing a conversation history. Your summary will replace the full 
history and must preserve every key fact, decision, name, number, measurement, 
and behavioral rule that was established. Be precise — do not paraphrase 
specific values. Omit only conversational filler.

CONVERSATION HISTORY:
{full_history_text}

Provide the summary now.
```

This prompt is defined as a constant `COMPACTION_PROMPT_TEMPLATE` in `compaction_runner.py`. It is not modified at runtime.

---

## What Sprint 006 Builds

```
contextDecayWindow/
  src/
    runners/
      __init__.py          -- NEW
      base_runner.py       -- NEW: BaseRunner abstract class
      full_context_runner.py -- NEW: Condition A
      compaction_runner.py   -- NEW: Condition B
    observability/
      turn_record.py       -- MODIFIED: add compaction fields
  tests/
    test_full_context_runner.py  -- NEW
    test_compaction_runner.py    -- NEW
```

---

## TurnRecord Modifications

Two fields added to support Condition B observability. Both default to values that are invisible in Condition A and C output.

```python
# Add to TurnRecord dataclass:
compaction_occurred: bool = False
compaction_turn: int | None = None        # turn number when compaction fired
history_tokens_before_compaction: int | None = None  # token estimate of history replaced
```

These fields are written to:
- `memory_store.csv` — new columns `compaction_occurred`, `compaction_turn`
- `turns.jsonl` — included in the full record
- Terminal output — `[COMPACTION]` line inserted when `compaction_occurred=True`

Terminal compaction line:

```
[COMPACTION] History compacted at turn 17 | Replaced ~3,214 tokens → summary
```

---

## Module Specifications

### src/runners/base_runner.py

Abstract base class. All three condition runners inherit from it.

```python
from abc import ABC, abstractmethod

class BaseRunner(ABC):

    condition: str   # set by subclass: "full_context" | "compaction" | "iterative"

    @abstractmethod
    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        """
        Build the context prompt for this turn.
        Returns (constructed_prompt, partially_populated_TurnRecord).
        Generation fields on TurnRecord are left as None — populated by Sprint 008.
        """
        ...

    @abstractmethod
    def on_turn_complete(self, user_message: str, assistant_message: str, turn_number: int) -> None:
        """
        Called after generation completes.
        Updates internal state (history, summary, etc.) for the next turn.
        """
        ...

    @property
    @abstractmethod
    def history_token_estimate(self) -> int:
        """Current estimated token count of maintained history."""
        ...
```

### src/runners/full_context_runner.py

Condition A — Full Context Loading.

**Internal state:**
- `_history: list[dict]` — grows every turn. Each entry: `{turn_number, user_message, assistant_message}`

**`build_context(user_message, turn_number)`:**
1. Assemble prompt from full `_history` using `context_builder.build_prompt()`
2. Append current user message
3. Populate TurnRecord:
   - `k_count = 0`, `n_count = 0`
   - `total_in_context = len(_history)`
   - `topic_count = 0`, `episode_count = len(_history)`
   - `estimated_tokens = estimate_tokens(constructed_prompt)`
4. Return (prompt, record)

**`on_turn_complete(user_message, assistant_message, turn_number)`:**
- Append `{turn_number, user_message, assistant_message}` to `_history`
- No other state changes

**`history_token_estimate`:**
- `estimate_tokens(full history text)`

### src/runners/compaction_runner.py

Condition B — Summarization Compaction.

**Internal state:**
- `_history: list[dict]` — grows every turn until compaction fires
- `_summary: str | None` — the compacted summary, replaces history when set
- `_compaction_count: int` — how many times compaction has fired
- `_last_compaction_turn: int | None`

**Constants:**
```python
COMPACTION_THRESHOLD_TOKENS = 3000
COMPACTION_PROMPT_TEMPLATE = "..."   # as defined above
```

**`build_context(user_message, turn_number)`:**
1. Check if compaction should fire: `history_token_estimate >= COMPACTION_THRESHOLD_TOKENS`
2. If yes — compaction fires:
   - Record `history_tokens_before_compaction`
   - Build compaction prompt from full history text
   - **In Sprint 006: compaction does not call the model.** A placeholder summary is used: `"[COMPACTION PENDING — inference not yet wired]"`. Sprint 008 replaces this with a real model call.
   - Set `_summary` to placeholder, clear `_history`
   - Set `compaction_occurred = True` on TurnRecord
3. Assemble context from `_summary` (if set) + remaining `_history` items since last compaction
4. Populate TurnRecord with compaction fields
5. Return (prompt, record)

**`on_turn_complete(user_message, assistant_message, turn_number)`:**
- Append turn to `_history`

**`history_token_estimate`:**
- Sum of estimated tokens across all `_history` entries + `_summary` if set

---

## Context Format — Condition A and B

Both conditions use `context_builder.build_prompt()` from Sprint 004, with one addition — when a summary is present in Condition B, it is prepended with a clear label:

```
{system_prompt}

--- CONVERSATION SUMMARY (prior history) ---
{summary_text}
--- END SUMMARY ---

--- RECENT CONVERSATION ---
[Turn 22]
User: ...
Assistant: ...
--- END RECENT ---

User: {current_message}
```

When no summary exists (pre-compaction), format is identical to Condition C's history block.

---

## TurnRecord Population Differences by Condition

| Field | Condition A | Condition B | Condition C |
|-------|-------------|-------------|-------------|
| k_count | 0 | 0 | ≥ 0 |
| n_count | 0 | 0 | = total episodes |
| total_in_context | len(history) | len(history since compaction) | deduplicated K ∪ N |
| topic_count | 0 | 0 | ≥ 1 |
| episode_count | len(history) | len(history since compaction) | total in store |
| compaction_occurred | False | True when fires | False |
| new_topic_created | False | False | True when fires |

This table is the integration contract between Sprint 006 runners and the Sprint 005 observability layer.

---

## Acceptance Criteria

- [ ] `FullContextRunner.build_context()` returns a prompt containing all prior turns
- [ ] Prompt grows each turn — verified by token estimate increasing monotonically
- [ ] `CompactionRunner.build_context()` returns prompt containing full history before threshold
- [ ] Compaction fires when `history_token_estimate >= COMPACTION_THRESHOLD_TOKENS`
- [ ] After compaction, `_history` is cleared and `_summary` is set
- [ ] `compaction_occurred = True` on TurnRecord when compaction fires
- [ ] `compaction_occurred = False` on TurnRecord when compaction does not fire
- [ ] `history_tokens_before_compaction` recorded correctly on compaction turn
- [ ] Terminal output shows `[COMPACTION]` line when `compaction_occurred=True`
- [ ] `memory_store.csv` includes compaction columns
- [ ] `COMPACTION_THRESHOLD_TOKENS` constant defined once — not hardcoded inline
- [ ] `COMPACTION_PROMPT_TEMPLATE` constant defined once
- [ ] Both runners implement `BaseRunner` interface completely
- [ ] `FullContextRunner` passes all tests without model path set
- [ ] `CompactionRunner` passes all tests without model path set (placeholder summary)
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| T-044 | Add compaction fields to `TurnRecord` in `turn_record.py` |
| T-045 | Update `FileWriter` and `TerminalPrinter` for compaction fields — `[COMPACTION]` terminal line, new CSV columns |
| T-046 | Implement `src/runners/base_runner.py` — `BaseRunner` abstract class |
| T-047 | Implement `src/runners/full_context_runner.py` — Condition A |
| T-048 | Implement `src/runners/compaction_runner.py` — Condition B with placeholder compaction |
| T-049 | Write `tests/test_full_context_runner.py` — covers context growth, TurnRecord population, history accumulation |
| T-050 | Write `tests/test_compaction_runner.py` — covers pre-threshold behavior, compaction trigger, post-compaction context, TurnRecord fields |
| T-051 | Run `pytest` — all tests pass including all prior sprints |
| T-052 | Commit and push Sprint 006 |

---

## Out of Scope — Sprint 006

- Actual model call during compaction (Sprint 008 — replaced with placeholder here)
- Iterative condition runner (Sprint 008)
- Test script (Sprint 007)
- Inference integration (Sprint 008)

---

## Notes for the Coding Agent

**Compaction in Sprint 006 uses a placeholder.** The `CompactionRunner` detects when compaction should fire and records the event correctly, but does not call the inference model. Sprint 008 replaces the placeholder with a real `Llama.create_chat_completion()` call using `COMPACTION_PROMPT_TEMPLATE`. Design the runner so this replacement is a single localized change — a `_run_compaction(history_text: str) -> str` method that Sprint 008 overrides.

**`on_turn_complete()` is called after generation, not after `build_context()`.** The turn pair is not added to history until the assistant response is available. This is the correct sequence — you cannot store a turn that hasn't happened yet.

**Both runners are entirely stateful in memory.** No SQLite involvement in Conditions A or B. The DB is Condition C's concern. Conditions A and B maintain their state as Python lists and strings.

**Token estimates only.** Both runners use `estimate_tokens()` (len // 4) for all threshold checks. This is pre-registered behavior — do not introduce precise tokenization here.