# CDW Sprint 008 — Inference Integration + Study Run

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-05-31

---

## Objective

Wire the inference model into the pipeline, implement the Condition C iterative runner, complete the compaction model call, build the study orchestrator, and execute the 32-turn study across all three conditions. At the end of this sprint, three complete run folders exist under `experiments/study_001/runs/` with full observability artifacts and rubric response files ready for Sprint 009 scoring.

This sprint has two phases: **build** (code) and **run** (execution). The run phase has strict non-intervention rules.

---

## What Sprint 008 Builds

```
contextDecayWindow/
  src/
    inference/
      __init__.py          -- NEW
      provider.py          -- NEW: InferenceProvider, InferenceResult
    runners/
      iterative_runner.py  -- NEW: Condition C
      compaction_runner.py -- MODIFIED: _run_compaction() real model call
    study/
      __init__.py          -- NEW
      script_loader.py     -- NEW: loads and validates script.json
      runner.py            -- NEW: StudyRunner orchestrator
  run_study.py             -- NEW: entry point at repo root
  tests/
    test_inference_provider.py  -- NEW (mock-based)
    test_iterative_runner.py    -- NEW (mock-based)
    test_study_runner.py        -- NEW (mock-based, 3-turn mini-script)
```

---

## Environment Variables

Three new variables added to the existing two:

```
CDW_INFERENCE_MODEL_PATH     absolute path to Qwen3.6 27B Q6_K GGUF
CDW_INFERENCE_N_GPU_LAYERS   number of GPU layers to offload (default: -1 = all)
CDW_INFERENCE_N_CTX          context window size in tokens (default: 147000)
```

All five environment variables must be set before `run_study.py` is executed. The study runner raises a descriptive error if any are missing.

---

## Module Specifications

### src/inference/provider.py

Wraps llama-cpp-python for the main inference model. Singleton — loaded once at process start.

```python
@dataclass
class InferenceResult:
    assistant_message: str
    tokens_per_second: float
    time_to_first_token: float   # seconds from prompt submission to first token
    output_tokens: int

class InferenceProvider:

    def __init__(self):
        # Loads Qwen3.6 27B Q6_K GGUF via llama-cpp-python
        # n_gpu_layers from CDW_INFERENCE_N_GPU_LAYERS (default -1)
        # n_ctx from CDW_INFERENCE_N_CTX (default 147000)
        # verbose=False
        ...

    def complete(self, prompt: str) -> InferenceResult:
        """
        Runs inference on the constructed prompt.
        Records timing: time_to_first_token and tokens_per_second.
        Returns InferenceResult.
        """
        ...
```

**Timing implementation:**

```python
import time

start = time.perf_counter()
response = self._llm(
    prompt,
    max_tokens=1024,
    echo=False,
    stream=False,
)
elapsed = time.perf_counter() - start

output_tokens = response["usage"]["completion_tokens"]
tokens_per_second = output_tokens / elapsed
# llama-cpp-python does not natively expose TTFT in non-streaming mode
# Use elapsed / output_tokens as an approximation for TTFT
time_to_first_token = elapsed / output_tokens if output_tokens > 0 else elapsed
```

Note: True TTFT requires streaming. Sprint 008 uses the approximation above. This is documented in the observability output as an estimate. If precise TTFT becomes important in a future study, switch to streaming mode then.

### src/runners/iterative_runner.py

Condition C — the system under study.

```python
class IterativeRunner(BaseRunner):

    condition = "iterative"

    def __init__(self, conn, embedding_provider, topic_manager, retrieval_engine, observer):
        ...

    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        """
        1. retrieval_engine.retrieve(user_message, turn_number) → RetrievalResult
        2. Populate TurnRecord from RetrievalResult
        3. Return (constructed_prompt, record)
        """
        ...

    def on_turn_complete(
        self,
        user_message: str,
        assistant_message: str,
        turn_number: int,
        embedding: np.ndarray
    ) -> AssignmentResult:
        """
        1. store_episode(user_message, assistant_message, embedding, turn_number)
        2. topic_manager.assign(episode_id, embedding)
        3. Returns AssignmentResult for TurnRecord population
        """
        ...

    @property
    def history_token_estimate(self) -> int:
        # Not meaningful for Condition C — returns 0
        return 0
```

Note: `on_turn_complete` signature differs from `BaseRunner` because Condition C requires the embedding. The base class signature uses `*args, **kwargs` for the extra parameter. Conditions A and B ignore it.

### src/runners/compaction_runner.py (modification)

Replace the Sprint 006 placeholder in `_run_compaction()`:

```python
def _run_compaction(self, history_text: str) -> str:
    """Real model call — replaces Sprint 006 placeholder."""
    prompt = COMPACTION_PROMPT_TEMPLATE.format(full_history_text=history_text)
    result = self._inference_provider.complete(prompt)
    return result.assistant_message
```

`CompactionRunner.__init__()` gains an `inference_provider: InferenceProvider` parameter. Update existing tests to pass a `MockInferenceProvider`.

### src/study/script_loader.py

```python
def load_script(path: str) -> dict:
    """
    Loads and validates script.json.
    Validates:
    - 'system_prompt' key present and non-empty
    - 'turns' key present and is a list
    - Each turn has 'turn' (int) and 'user' (str)
    - Turn numbers are sequential starting from 1
    - Minimum 30 turns
    Raises ValueError with descriptive message on any violation.
    Returns the full script dict.
    """
    ...
```

### src/study/runner.py

The study orchestrator. Runs all three conditions sequentially.

```python
class StudyRunner:

    CONDITION_ORDER = ["full_context", "compaction", "iterative"]

    def __init__(self, script_path: str, study_dir: str, run_id: str = "run_001"):
        ...

    def run(self) -> None:
        """
        Runs all three conditions in order: full_context → compaction → iterative.
        Each condition gets its own Observer, RunConfig, and (for iterative) fresh DB.
        """
        ...

    def _run_condition(self, condition: str) -> None:
        """
        Executes one condition end-to-end across all script turns.
        Full turn sequence per turn:
          1. runner.build_context(user_message, turn_number) → (prompt, record)
          2. inference_provider.complete(prompt) → InferenceResult
          3. Populate record generation fields
          4. runner.on_turn_complete(user_message, assistant_message, turn_number, [embedding])
          5. For Condition C: populate record from AssignmentResult
          6. observer.flush_turn(record)
        """
        ...

    def _write_rubric_responses(self, condition: str, turns: list[dict]) -> None:
        """
        Writes rubric/responses.md for the condition.
        Includes assistant responses from rubric turns (25–32) formatted for manual scoring.
        """
        ...
```

**Condition initialization:**

```python
# Condition A
runner = FullContextRunner()

# Condition B
runner = CompactionRunner(inference_provider=inference_provider)

# Condition C
db_path = os.path.join(run_config.output_dir, "study.db")
conn = init_db(db_path)
embedding_provider = EmbeddingProvider()   # from Sprint 002
topic_manager = TopicManager(conn)
retrieval_engine = RetrievalEngine(conn, embedding_provider)
runner = IterativeRunner(conn, embedding_provider, topic_manager, retrieval_engine, observer)
```

**Embedding for Condition C:**
The embedding for `on_turn_complete()` is the embedding of the full response pair — concatenation of user message and assistant message, embedded together. This is consistent with how episodes were defined in Sprint 002.

```python
pair_text = f"User: {user_message}\nAssistant: {assistant_message}"
embedding = embedding_provider.embed(pair_text)
```

### run_study.py (entry point)

```python
# Usage: python run_study.py
# All configuration via environment variables.

from src.study.runner import StudyRunner

if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_001/script.json",
        study_dir="experiments/study_001/runs",
        run_id="run_001",
    )
    runner.run()
```

---

## rubric/responses.md Format

Written automatically by `_write_rubric_responses()` after each condition completes. Contains the model's actual responses to rubric turns (25–32) formatted for manual scoring in Sprint 009.

```markdown
# Rubric Responses — {condition}
**Run:** run_001
**Condition:** {condition}
**Scored by:** [TO BE FILLED — Sprint 009]

---

## Turn 25 — Q1: Budget Cap

**User:** What is the exact budget cap for the Meridian project...

**Assistant response:**
{assistant_message}

**Score:** [  ] (1.0 / 0.5 / 0.0)
**Notes:**

---

## Turn 26 — Q4: Lead Engineer + Deadline
...
```

One section per rubric turn (25–32). Score fields left empty for Sprint 009.

---

## Mock Infrastructure for Tests

All Sprint 008 tests use `MockInferenceProvider` — no model path required.

```python
class MockInferenceProvider:
    def complete(self, prompt: str) -> InferenceResult:
        return InferenceResult(
            assistant_message="Mock assistant response.",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
        )
```

`MockInferenceProvider` is defined in `tests/conftest.py` and shared across all test files.

---

## Acceptance Criteria — Build Phase

- [ ] `InferenceProvider` loads model and returns `InferenceResult` with all fields populated
- [ ] `InferenceProvider` respects `CDW_INFERENCE_N_GPU_LAYERS` and `CDW_INFERENCE_N_CTX`
- [ ] `IterativeRunner.build_context()` returns a populated `TurnRecord` with retrieval fields
- [ ] `IterativeRunner.on_turn_complete()` stores episode and assigns topic
- [ ] `CompactionRunner._run_compaction()` calls inference provider (verified with mock)
- [ ] `script_loader.load_script()` validates all constraints and raises on violation
- [ ] `StudyRunner` runs a 3-turn mock study end-to-end across all three conditions
- [ ] Three run folders created with correct structure
- [ ] `rubric/responses.md` written for each condition with correct turn references
- [ ] All tests pass including all prior sprints (mock-based inference tests gate on missing model path)

---

## Acceptance Criteria — Run Phase

These are verified by observation during the study run, not by automated tests.

- [ ] Terminal output appears for every turn across all three conditions
- [ ] Condition A token estimates increase monotonically
- [ ] Condition B shows `[COMPACTION]` line at least once
- [ ] Condition C shows K and N retrieval counts per turn
- [ ] All 32 turns complete for all three conditions without error
- [ ] Three run folders populated with all expected files
- [ ] `rubric/responses.md` for each condition contains assistant responses for turns 25–32
- [ ] No intervention during the run — observe only

---

## Tasks

| ID | Description |
|----|-------------|
| T-058 | Implement `src/inference/provider.py` — `InferenceProvider` and `InferenceResult` |
| T-059 | Implement `src/runners/iterative_runner.py` — Condition C |
| T-060 | Modify `src/runners/compaction_runner.py` — real `_run_compaction()` call |
| T-061 | Implement `src/study/script_loader.py` — load and validate script.json |
| T-062 | Implement `src/study/runner.py` — `StudyRunner` with full condition orchestration |
| T-063 | Implement `run_study.py` — entry point |
| T-064 | Add `MockInferenceProvider` to `tests/conftest.py` |
| T-065 | Write `tests/test_inference_provider.py` — mock-based, covers InferenceResult fields |
| T-066 | Write `tests/test_iterative_runner.py` — mock-based, covers build_context and on_turn_complete |
| T-067 | Write `tests/test_study_runner.py` — mock-based 3-turn mini-study, all three conditions |
| T-068 | Run `pytest` — all tests pass |
| T-069 | Set all five environment variables, verify model paths |
| T-070 | Execute `python run_study.py` — full 32-turn study run, all three conditions |
| T-071 | Verify all run folders populated correctly |
| T-072 | Commit and push Sprint 008 |

---

## Run Phase — Non-Intervention Rules

These are pre-registered and must be followed during T-070.

1. **Do not stop the run** unless the process crashes with an unrecoverable error
2. **Do not modify the script** after Sprint 007 commit
3. **Do not modify any runner** during the run
4. **Do not read rubric response files** until all three conditions have completed
5. **Observe terminal output only** — note anomalies in a separate scratch file if needed
6. **If the process crashes:** document the turn and error, fix the bug, restart the affected condition from turn 1 with a fresh DB. Document the restart in the run notes.
7. **Run order is fixed:** full_context → compaction → iterative. Do not change.

---

## Estimated Run Time

Rough estimates based on Qwen3.6 27B Q6_K at ~45 tok/s on RTX 5090:

- Average assistant response: ~200 tokens → ~4.5 seconds per turn
- 32 turns × 3 conditions = 96 turns total
- Estimated run time: ~7–10 minutes excluding compaction calls
- Compaction adds one extra inference call (~500–800 token summary) — negligible

The study run should complete in under 15 minutes.

---

## Out of Scope — Sprint 008

- Rubric scoring (Sprint 009)
- Analysis and writeup (Sprint 009)
- Any architectural changes based on observed results — observe only

---

## Notes for the Coding Agent

**Condition C DB path:** `{run_config.output_dir}/study.db` — inside the run folder, not at repo root. This keeps each run fully self-contained. The DB is gitignored.

**Response pair embedding:** embed `f"User: {user_message}\nAssistant: {assistant_message}"` as a single string. This is consistent with the episode storage design from Sprint 002.

**Inference context for Conditions A and B:** The constructed prompt from `build_context()` already includes the system prompt and full history. Pass it directly to `inference_provider.complete()`. Do not prepend the system prompt again.

**Inference context for Condition C:** `build_prompt()` from Sprint 004 returns the history block. The current user message must be appended by the study runner before calling inference:

```python
full_prompt = f"{constructed_prompt}\n\nUser: {user_message}\nAssistant:"
result = inference_provider.complete(full_prompt)
```

**TTFT approximation is documented, not hidden.** The terminal output and `model_performance.csv` label TTFT values as `~TTFT` to signal they are estimates. This is honest observability.