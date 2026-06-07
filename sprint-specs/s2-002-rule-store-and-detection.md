# CDW Sprint S2_002 — Rule Store + Detection

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-05

---

## Objective

Implement the rule store, automatic LLM-based rule detection piggybacked on the existing inference call, and the rule pinning mechanism at context construction time. At the end of this sprint, episodes containing behavioral rules are automatically detected, stored separately, and appended unconditionally to every constructed context window — bypassing K and N retrieval entirely.

---

## What Sprint S2_002 Builds

```
contextDecayWindow/
  src/
    db/
      schema.py          -- MODIFIED: add rule_store table
      rule_store.py      -- NEW: store_rule(), get_all_rules()
    inference/
      provider.py        -- MODIFIED: structured tag, InferenceResult gains
                         --   contains_rule and rule_summary fields,
                         --   assistant_message always clean
    memory/
      context_builder.py -- MODIFIED: prepend rule episodes to every prompt
      retrieval_engine.py -- MODIFIED: RetrievalResult gains rule_episodes field
    observability/
      turn_record.py     -- MODIFIED: rule detection fields added
      terminal.py        -- MODIFIED: [RULE STORE] terminal line
      file_writer.py     -- MODIFIED: rule_detection.csv
  tests/
    test_rule_store.py        -- NEW
    test_rule_detection.py    -- NEW
    test_context_builder_s2.py -- NEW: verifies rule prepending behavior
```

---

## Rule Detection Mechanism

### Inference Prompt Modification

The system prompt passed to every inference call gains one appended instruction:

```
After your response, append exactly one line in this format and no other text:
<rule_detection>{"contains_rule": BOOL, "rule_summary": "SUMMARY_OR_NULL"}</rule_detection>

Set contains_rule to true if and only if the user's message establishes a
persistent behavioral rule, formatting requirement, or constraint that should
apply to all future responses. Set rule_summary to a concise description of
the rule if contains_rule is true, otherwise null.
```

This instruction is appended once to the system prompt. It is not repeated in every user message. It persists across all turns via the constructed context window.

### Tag Parsing in InferenceProvider

`InferenceProvider.complete()` is responsible for:

1. Running inference as before
2. Detecting the `<rule_detection>` tag in the raw output via regex
3. Parsing the JSON payload
4. Stripping the tag and any trailing whitespace from `assistant_message`
5. Populating `contains_rule` and `rule_summary` on `InferenceResult`

The tag never leaves `InferenceProvider`. Nothing downstream sees raw tagged output.

**Parsing failure handling:**
If the tag is absent or the JSON is malformed, default to `contains_rule=False`, `rule_summary=None`. Log the parsing failure to `rule_detection.csv` as a detection error. Do not raise — inference succeeded, detection failed gracefully.

### Updated InferenceResult

```python
@dataclass
class InferenceResult:
    assistant_message: str        # always clean — tag stripped
    tokens_per_second: float
    time_to_first_token: float
    output_tokens: int
    contains_rule: bool           # NEW
    rule_summary: str | None      # NEW — None if contains_rule=False
```

---

## Module Specifications

### src/db/schema.py (modification)

Add one table to `init_db()`:

```sql
CREATE TABLE IF NOT EXISTS rule_store (
    id              TEXT PRIMARY KEY,      -- UUID4
    episode_id      TEXT NOT NULL,         -- FK → episodes.id
    rule_summary    TEXT NOT NULL,
    turn_number     INTEGER NOT NULL,
    created_at      TEXT NOT NULL          -- ISO 8601
);
```

`init_db()` remains idempotent — `CREATE TABLE IF NOT EXISTS`.

### src/db/rule_store.py

Two functions:

**`store_rule(conn, episode_id, rule_summary, turn_number) -> str`**
- Generates UUID4 for id
- Sets `created_at` to current UTC timestamp
- Returns the rule id

**`get_all_rules(conn) -> list[dict]`**
- Returns all rows from rule_store as list of dicts
- Each dict includes: id, episode_id, rule_summary, turn_number, created_at
- Returns empty list if no rules exist
- Called at context construction time to retrieve all pinned rules

### src/memory/context_builder.py (modification)

`build_prompt()` gains a `rule_episodes` parameter:

```python
def build_prompt(
    episodes: list[dict],
    system_prompt: str,
    rule_episodes: list[dict] | None = None,
) -> str:
```

When `rule_episodes` is provided and non-empty, they are prepended to the history block before K and N episodes, with a clear label:

```
{system_prompt}

--- PINNED RULES ---
[Turn {turn_number}]
User: {user_message}
Assistant: {assistant_message}

[Turn {turn_number}]
...
--- END PINNED RULES ---

--- RETRIEVED CONVERSATION HISTORY ---
[Turn {turn_number}]
...
--- END HISTORY ---
```

Rule episodes appear before retrieved history. They are always present regardless of retrieval results. If `rule_episodes` is None or empty, the PINNED RULES block is omitted entirely — no empty section in the prompt.

`estimate_tokens()` accounts for rule episode tokens separately so the observability layer can report them distinctly.

### src/memory/retrieval_engine.py (modification)

`RetrievalResult` gains one field:

```python
@dataclass
class RetrievalResult:
    episodes: list[dict]
    k_episode_ids: list[str]
    k_scores: dict[str, float]
    n_episode_ids: list[str]
    n_scores: dict[str, float]
    constructed_prompt: str
    estimated_tokens: int
    k_count: int
    n_count: int
    total_episodes_in_context: int
    rule_episodes: list[dict]          -- NEW: episodes pinned from rule store
    rule_token_estimate: int           -- NEW: estimated tokens from rule block
```

`RetrievalEngine.retrieve()` calls `get_all_rules(conn)` at the start of each turn and passes rule episodes to `build_prompt()`. Rule episodes are fetched by joining `rule_store` with `episodes` on `episode_id` to get full episode content.

---

## Updated Full Turn Sequence After S2_002

1. User message arrives from script
2. `record = TurnRecord(...)`
3. `retrieval_result = retrieval_engine.retrieve(user_message, turn_number)`
   - Fetches all rule episodes from rule_store
   - Runs K and N retrieval
   - Calls `build_prompt(episodes, system_prompt, rule_episodes)`
4. Populate `record` from `retrieval_result`
5. Inference: `result = inference_provider.complete(constructed_prompt)`
   - Tag parsed and stripped inside provider
   - `result.contains_rule` and `result.rule_summary` populated
6. Populate `record` generation fields including `contains_rule`, `rule_summary`
7. `store_episode()` — stores response pair
8. If `result.contains_rule`: `store_rule(conn, episode_id, rule_summary, turn_number)`
9. `topic_manager.assign()` — assigns to topic
10. Populate `record` from `AssignmentResult`
11. `observer.flush_turn(record)` — terminal + files
12. Return response to user

---

## TurnRecord Modifications

```python
# Add to TurnRecord:
contains_rule: bool = False
rule_summary: str | None = None
rule_store_count: int = 0        # total rules pinned at this turn
rule_token_estimate: int = 0     # estimated tokens from rule block
```

### Terminal Output Addition

New line after `[RETRIEVAL]` block:

```
[RULE STORE] 2 rules pinned | Rule detected this turn: Yes — "always format multiple items as numbered list"
[RULE STORE] 2 rules pinned | Rule detected this turn: No
```

When no rules are in the store yet: `[RULE STORE] 0 rules pinned | Rule detected this turn: No`

### New Metric File: rule_detection.csv

```
turn_number, contains_rule_detected, rule_summary, parse_error, ground_truth, true_positive, false_positive
```

`ground_truth`, `true_positive`, `false_positive` are left empty at run time — filled during Sprint S2_009 analysis against known rule-setting turns in the script.

---

## Acceptance Criteria

- [ ] `rule_store` table created by `init_db()` — idempotent
- [ ] `store_rule()` writes row and returns valid UUID
- [ ] `get_all_rules()` returns all rows correctly, empty list when empty
- [ ] Inference prompt contains rule detection instruction
- [ ] `<rule_detection>` tag stripped from `assistant_message` before returning
- [ ] `InferenceResult.contains_rule` and `rule_summary` populated correctly
- [ ] Malformed or absent tag defaults to `contains_rule=False` without raising
- [ ] `build_prompt()` prepends PINNED RULES block when `rule_episodes` non-empty
- [ ] PINNED RULES block absent when `rule_episodes` is None or empty
- [ ] `RetrievalResult.rule_episodes` populated from rule store at each turn
- [ ] `RetrievalResult.rule_token_estimate` computed correctly
- [ ] `rule_detection.csv` written with one row per turn
- [ ] `[RULE STORE]` terminal line appears correctly
- [ ] `rule_store_count` increments correctly on TurnRecord
- [ ] All prior tests pass — no regressions
- [ ] All acceptance criteria verified by tests

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-001 | Add `rule_store` table to `src/db/schema.py` |
| S2-T-002 | Implement `src/db/rule_store.py` — `store_rule()` and `get_all_rules()` |
| S2-T-003 | Modify `src/inference/provider.py` — append detection instruction to system prompt, parse and strip tag, populate new `InferenceResult` fields |
| S2-T-004 | Modify `src/memory/context_builder.py` — `rule_episodes` parameter, PINNED RULES block |
| S2-T-005 | Modify `src/memory/retrieval_engine.py` — fetch rules, populate `RetrievalResult.rule_episodes` and `rule_token_estimate` |
| S2-T-006 | Modify `src/observability/turn_record.py` — add rule detection fields |
| S2-T-007 | Modify `src/observability/terminal.py` — `[RULE STORE]` line |
| S2-T-008 | Modify `src/observability/file_writer.py` — `rule_detection.csv` |
| S2-T-009 | Write `tests/test_rule_store.py` — covers schema, store_rule, get_all_rules |
| S2-T-010 | Write `tests/test_rule_detection.py` — covers tag parsing, strip behavior, malformed tag handling, InferenceResult fields |
| S2-T-011 | Write `tests/test_context_builder_s2.py` — covers PINNED RULES prepend, empty rule_episodes behavior, token estimate |
| S2-T-012 | Run `pytest` — all tests pass including all Study 001 tests |
| S2-T-013 | Commit and push S2_002 |

---

## Out of Scope — S2_002

- Soft N cap implementation (S2_003)
- Threshold changes (S2_003)
- Topic consolidation (S2_004)
- Observability additions beyond rule_detection.csv (S2_005)
- Any changes to Condition A or B runners
- Script writing (S2_007)

---

## Notes for the Coding Agent

**System prompt injection:** The rule detection instruction is appended to the system prompt inside `InferenceProvider.__init__()` — not at call time. It is baked into the provider at initialization. This means every call automatically includes it without the study runner needing to manage it.

**Regex for tag extraction:**
```python
import re
pattern = r'<rule_detection>(.*?)</rule_detection>'
match = re.search(pattern, raw_output, re.DOTALL)
```

Strip everything from the opening `<rule_detection>` tag to the end of the closing tag, plus any leading/trailing whitespace on the remaining text.

**Rule episodes in context builder:** Rule episodes are fetched as full episode dicts (same structure as regular episodes). The `build_prompt()` function formats them identically to regular history entries — turn number, user message, assistant message. The PINNED RULES label is the only distinction.

**Rule store is append-only.** No updates, no deletes. Rules accumulate across the study run. `get_all_rules()` always returns the full set. This is intentional — once a rule is pinned it stays pinned for the entire session.

**Token estimate for rule block:** Use the same `estimate_tokens()` function from Sprint 004. `rule_token_estimate` is `estimate_tokens(rule_block_text)` where `rule_block_text` is the formatted PINNED RULES section including headers.