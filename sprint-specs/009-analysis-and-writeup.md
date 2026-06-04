# CDW Sprint 009 — Analysis + Writeup

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-04

---

## Objective

Score the rubric responses for all three conditions, run the metric analysis, evaluate against pre-registered success criteria, and write the Study 001 report. At the end of this sprint, `experiments/study_001/README.md` exists as a complete, defensible research artifact.

---

## What Sprint 009 Produces

```
contextDecayWindow/
  experiments/
    study_001/
      README.md                          -- NEW: study report
      runs/
        run_001/
          full_context/
            rubric/
              responses.md               -- already written by Sprint 008
              scores.md                  -- FILL IN: manual scoring
          compaction/
            rubric/
              responses.md               -- already written by Sprint 008
              scores.md                  -- FILL IN: manual scoring
          iterative/
            rubric/
              responses.md               -- already written by Sprint 008
              scores.md                  -- FILL IN: manual scoring
  src/
    analysis/
      __init__.py                        -- NEW
      rubric_reader.py                   -- NEW: parses scores.md files
      metrics_reader.py                  -- NEW: reads CSV metric files
      criteria_evaluator.py              -- NEW: evaluates success criteria
  scripts/
    analyze_run.py                       -- NEW: entry point, prints full analysis
```

---

## Phase 1 — Manual Rubric Scoring

Do this before writing any code. Scoring is the primary research act of this sprint.

### Process

For each condition (full_context, compaction, iterative):

1. Open `runs/run_001/{condition}/rubric/responses.md`
2. Read the model's response for each rubric turn (25–32)
3. Apply the scoring criteria from `experiments/study_001/rubric_filled.md` exactly as written
4. Fill in the score and notes fields in `runs/run_001/{condition}/rubric/scores.md`

### scores.md Format

```markdown
# Rubric Scores — {condition}
**Scored by:** Muzaffer Ozen
**Date scored:** [DATE]

---

| Question | Score | Notes |
|----------|-------|-------|
| Q1 — Budget cap | [1.0 / 0.5 / 0.0] | |
| Q2 — Performance target | [1.0 / 0.5 / 0.0] | |
| Q3 — CRISPR dosage | [1.0 / 0.5 / 0.0] | |
| Q4 — Lead engineer + deadline | [1.0 / 0.5 / 0.0] | |
| Q5 — Cell line + expression rate | [1.0 / 0.5 / 0.0] | |
| Q6 — Topic bleed probe (turn 20) | [1 / 0] | |
| Q7 — Researcher disambiguation | [1 / 0] | |
| Q8 — Numerical enumeration | [1 / 0] | |
| Q9 — Rule recall | [1 / 0] | |
| Q10 — Rule compliance (turns 25–32) | [1 / 0] | |

**Category 1+2 Total:** [X] / 5.0
**Category 3 Total:** [X] / 3
**Category 4 Total:** [X] / 2
**Overall:** [X] / 10.0
```

### Scoring Discipline

- Score against rubric_filled.md criteria only — do not improvise new criteria
- If a response is ambiguous, default to the lower score and note why
- Q10 (rule compliance) is assessed by reviewing all assistant responses in turns 25–32 — not just one turn
- Score all three conditions before looking at the results comparatively — avoid confirmation bias

---

## Phase 2 — Analysis Script

### src/analysis/rubric_reader.py

Parses the completed scores.md files and returns structured scores.

```python
def read_scores(scores_path: str) -> dict:
    """
    Parses scores.md and returns:
    {
        "condition": str,
        "scores": {
            "Q1": float, "Q2": float, ..., "Q10": float
        },
        "category_1_2_total": float,   # Q1+Q2+Q3+Q4+Q5
        "category_3_total": float,      # Q6+Q7+Q8
        "category_4_total": float,      # Q9+Q10
        "overall": float
    }
    """
    ...
```

### src/analysis/metrics_reader.py

Reads the CSV metric files and returns summary statistics.

```python
def read_model_performance(run_dir: str) -> dict:
    """
    Reads model_performance.csv.
    Returns: avg_tokens_per_second, avg_output_tokens, total_output_tokens,
             peak_estimated_tokens (max context size across all turns)
    """
    ...

def read_memory_store(run_dir: str) -> dict:
    """
    Reads memory_store.csv.
    Returns: final_topic_count, final_episode_count,
             compaction_events (list of turns where compaction fired)
    """
    ...

def read_k_values(run_dir: str) -> dict:
    """
    Reads K_values.csv.
    Returns: avg_k_per_turn, max_k_per_turn, turns_with_zero_k (count)
    """
    ...

def read_token_growth(run_dir: str) -> list[dict]:
    """
    Reads model_performance.csv.
    Returns per-turn token estimates as list for growth curve comparison.
    """
    ...
```

### src/analysis/criteria_evaluator.py

Evaluates the three pre-registered success criteria programmatically.

```python
def evaluate_criteria(scores: dict[str, dict]) -> dict:
    """
    Takes scores dict keyed by condition name.
    Returns:
    {
        "bar_1": {
            "passed": bool,
            "condition_c_score": float,
            "condition_b_score": float,
            "difference": float,
            "threshold": 0.15,
            "description": "Condition C Cat1+2 ≥ 15pp above Condition B"
        },
        "bar_2": {
            "passed": bool,
            "condition_c_bleed": float,
            "condition_a_bleed": float,
            "description": "Condition C topic bleed ≤ Condition A"
        },
        "bar_3": {
            "passed": bool,
            "condition_c_score": float,
            "condition_b_score": float,
            "description": "Condition C Cat4 ≥ Condition B Cat4"
        },
        "overall": "VALIDATED" | "PARTIAL" | "INVALIDATED"
    }
    """
    ...
```

Overall result:
- `VALIDATED` — all three bars passed
- `PARTIAL` — two bars passed
- `INVALIDATED` — zero or one bar passed

### scripts/analyze_run.py

Entry point. Reads all data, prints full analysis to terminal, writes summary to `experiments/study_001/analysis_summary.txt`.

```
python scripts/analyze_run.py
```

Terminal output format:

```
═══════════════════════════════════════════════════════
STUDY 001 ANALYSIS — contextDecayWindow
Idris Applied AI Research
═══════════════════════════════════════════════════════

RUBRIC SCORES
─────────────────────────────────────────────────────
                     Full Context   Compaction   Iterative
Category 1+2 (det)       X.X / 5.0    X.X / 5.0    X.X / 5.0
Category 3 (bleed)         X / 3        X / 3        X / 3
Category 4 (behav)         X / 2        X / 2        X / 2
Overall                  X.X / 10.0   X.X / 10.0   X.X / 10.0

SUCCESS CRITERIA
─────────────────────────────────────────────────────
Bar 1 — Detail Fidelity (Cat1+2, C vs B, ≥15pp):  PASS / FAIL
  Condition C: X.X  |  Condition B: X.X  |  Δ: X.Xpp

Bar 2 — Topic Bleed (Cat3, C ≤ A):                PASS / FAIL
  Condition C: X/3  |  Condition A: X/3

Bar 3 — Behavioral Consistency (Cat4, C ≥ B):     PASS / FAIL
  Condition C: X/2  |  Condition B: X/2

OVERALL RESULT: VALIDATED / PARTIAL / INVALIDATED

TOKEN GROWTH
─────────────────────────────────────────────────────
Full Context peak:   ~X,XXX tokens (turn XX)
Compaction peak:     ~X,XXX tokens (turn XX, X compaction events)
Iterative peak:      ~X,XXX tokens (turn XX)

CONDITION C — RETRIEVAL SUMMARY
─────────────────────────────────────────────────────
Avg K per turn:      X.X episodes
Turns with K=0:      XX / 32
Final topic count:   X
Final episode count: XX

PROTOCOL NOTES
─────────────────────────────────────────────────────
[loaded from run notes if present]
═══════════════════════════════════════════════════════
```

---

## Phase 3 — Study Report

### experiments/study_001/README.md

Written by Muzaffer after scoring and analysis are complete. Structure below. Content should be written in first person — this is your research, your observations, your conclusions.

```markdown
# Study 001 — contextDecayWindow
**Idris Applied AI Research**
**Date:** June 2026
**Pre-registration SHA:** [from pre_registration.md]
**Status:** Complete

---

## Summary

[2–3 sentences: what was tested, what was found, whether architecture was validated]

---

## Research Question

[Copy from pre_registration.md — do not paraphrase]

---

## Method

### Conditions
[Brief description of all three conditions]

### Model
[Qwen3.6 27B Q6K, hardware, context cap]

### Script
[Brief: 32 turns, two topics, planted facts summary]

### Evaluation
[Rubric categories, scoring criteria, success bars]

---

## Results

### Rubric Scores
[Table — copy from analysis output]

### Success Criteria
[Bar 1, 2, 3 — pass/fail with numbers]

### Token Growth
[Growth curve comparison — narrative]

### Condition C Retrieval Behavior
[K/N patterns across turns — what did the system actually retrieve?]

---

## Discussion

[Your observations. What worked. What didn't. What surprised you.
Did the architecture behave as hypothesized? Where did it differ from prediction?
What does this tell you about the research question?]

---

## Protocol Notes

[Engineering findings from the run — CUDA PATH fix, n_ctx calibration,
Unicode encoding fix, restarts. These are real findings, not failures.]

---

## Limitations

[Study 001 specific: single model, scripted conversation, solo rater,
single run. What would need to be different for stronger claims?]

---

## Next Steps

[What Study 002 should investigate based on what you observed here]

---

## Appendix

- Pre-registration: `experiments/study_001/pre_registration.md`
- Script: `experiments/study_001/script.json`
- Rubric: `experiments/study_001/rubric_filled.md`
- Run data: `experiments/study_001/runs/run_001/`
```

---

## Acceptance Criteria

- [ ] scores.md completed for all three conditions
- [ ] Scores filled using rubric_filled.md criteria exactly — no improvised criteria
- [ ] `analyze_run.py` runs without error and produces correct output
- [ ] Success criteria evaluated programmatically against pre-registered bars
- [ ] `experiments/study_001/analysis_summary.txt` written
- [ ] `experiments/study_001/README.md` written with all sections complete
- [ ] Protocol notes section documents all three run issues (encoding, n_ctx × 2, CUDA PATH)
- [ ] Pre-registration SHA referenced in README
- [ ] Sprint 009 committed and pushed

---

## Tasks

| ID | Description |
|----|-------------|
| T-073 | Score rubric responses for Condition A — fill `runs/run_001/full_context/rubric/scores.md` |
| T-074 | Score rubric responses for Condition B — fill `runs/run_001/compaction/rubric/scores.md` |
| T-075 | Score rubric responses for Condition C — fill `runs/run_001/iterative/rubric/scores.md` |
| T-076 | Implement `src/analysis/rubric_reader.py` |
| T-077 | Implement `src/analysis/metrics_reader.py` |
| T-078 | Implement `src/analysis/criteria_evaluator.py` |
| T-079 | Implement `scripts/analyze_run.py` — full terminal output and summary file |
| T-080 | Run `python scripts/analyze_run.py` — verify output is correct |
| T-081 | Write `experiments/study_001/README.md` |
| T-082 | Commit and push Sprint 009 |

---

## Out of Scope — Sprint 009

- Study 002 design (informed by Discussion section observations — not spec'd here)
- Multi-rater evaluation
- GABA mechanism implementation
- Any changes to the study data or run artifacts

---

## Notes

**Score all three conditions before comparing.** Read each condition's rubric responses cold. Score them against the rubric. Then run the analysis. Seeing the comparison before scoring risks confirmation bias — you might unconsciously score Condition C higher because you expect it to win.

**The Discussion section is the most important part of the README.** The rubric numbers tell you what happened. The Discussion section tells you what it means. Write it after you've sat with the results. Don't rush it.

**Protocol notes are findings, not failures.** The CUDA PATH issue, the n_ctx calibration across three restarts, the Unicode encoding fix — these are real engineering discoveries about running local inference on Windows for research purposes. They belong in the report.

**The pre-registration SHA is your credibility anchor.** Reference it explicitly in the README. It proves the design was locked before the data existed.