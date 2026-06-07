# CDW Sprint S2_008 — Study Run

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** In Progress
**Date:** 2026-06-05

---

## Objective

Execute the 120-turn study across all three conditions. Produce three complete run folders under `experiments/study_002/runs/` with full observability artifacts and rubric response files ready for S2_009 scoring.

This sprint has two phases: **build verification** and **run execution**. The run phase has strict non-intervention rules.

---

## What Sprint S2_008 Produces

```
experiments/study_002/runs/
  run_001/
    full_context/
      logs/           constructed_prompts/    metrics/
      snapshots/      rubric/
    compaction/
      logs/           constructed_prompts/    metrics/
      snapshots/      rubric/
    iterative/
      logs/           constructed_prompts/    metrics/
      snapshots/      rubric/
      study.db
```

---

## Pre-Run Checklist

Study 001 required three restarts due to preventable configuration issues. The following checklist must be completed before `python run_study.py` is executed. Do not start the run until every item is confirmed.

| Item | Check |
|------|-------|
| CUDA PATH set permanently — not just for this terminal session | [ ] |
| `CDW_INFERENCE_N_CTX` set to a value verified not to cause VRAM overflow | [ ] |
| `CDW_INFERENCE_MODEL_PATH` points to Qwen3.6 27B Q6_K GGUF | [ ] |
| `CDW_EMBEDDING_MODEL_PATH` points to Qwen3-Embedding-0.6B GGUF | [ ] |
| `CDW_DB_PATH` set correctly | [ ] |
| `experiments/study_002/runs/` directory empty — no prior run_001 folder | [ ] |
| `experiments/study_002/script.json` exists and has 120 turns | [ ] |
| `experiments/study_002/rubric_filled.md` exists | [ ] |
| GPU confirmed active — test inference run produces 40+ tok/s | [ ] |
| All 5 environment variables confirmed in a single pre-run test call | [ ] |

### CUDA PATH — Permanent Fix

Add the CUDA bin directory to system PATH permanently via Windows system environment variables, not just the current terminal session. Study 001 required this fix at runtime, causing a restart. Do not repeat this.

```powershell
# Verify CUDA is in permanent PATH before the run
[System.Environment]::GetEnvironmentVariable("PATH", "Machine") -split ";" | Where-Object { $_ -like "*CUDA*" }
```

If empty, add it permanently through System Properties → Environment Variables → System Variables → PATH.

### n_ctx Verification

Run a short test before the full study:

```python
python -c "
from src.inference.provider import InferenceProvider
p = InferenceProvider()
r = p.complete('Say hello.')
print(f'Speed: {r.tokens_per_second:.1f} tok/s')
print(f'GPU confirmed: OK' if r.tokens_per_second > 30 else 'WARNING: speed low — check GPU')
"
```

Must return > 30 tok/s before proceeding.

---

## Estimated Runtime

| Condition | Turns | Avg response | Estimated time |
|-----------|-------|-------------|----------------|
| full_context | 120 | ~1,500 tokens @ 45 tok/s | ~67 minutes |
| compaction | 120 | ~1,500 tokens + compaction calls | ~70 minutes |
| iterative | 120 | ~1,500 tokens + embedding per turn | ~75 minutes |
| **Total** | **360** | | **~3.5–4.5 hours** |

Plan the run accordingly. Do not start it if you have less than 5 hours available. The run must not be interrupted.

Compaction events add inference time for the summary call. With a 3,000-token threshold and ~1,700 tokens per turn, compaction fires roughly every 2 turns in the early study — more frequently than Study 001 because turn pairs are much longer. Expect 50–60 compaction events across the 120-turn run.

---

## What to Watch For

These are observation signals — not reasons to intervene. Note them in a run notes scratch file.

**K retrieval activity:**
Study 001 saw K fire once in 32 turns. Study 002 should show K firing consistently with the 0.50 threshold. Watch the `[RETRIEVAL]` line. If K=0 persists beyond turn 20, the threshold may still be too strict — document for S2_009 analysis.

**Topic consolidation:**
Consolidation fires at episodes 10, 20, 30... Watch for `[CONSOLIDATION]` lines. The first pass fires around turn 10. If topic count is not dropping toward single digits by turn 60, the 0.50 assignment threshold or 0.60 merge threshold may need adjustment for Study 003.

**Rule detection:**
Turns 1–2 should show `Rule detected this turn: Yes` in the `[RULE STORE]` line. All subsequent turns should show `No` unless the script contains additional rule-setting language. If rule detection fires on non-rule turns, note the turn numbers for false positive analysis.

**Context token growth:**
Watch the `Tokens: ~N` header. Condition C should plateau around 15,000–20,000 tokens by the time the N cap saturates (~turn 10). If it continues growing beyond that, the soft cap has an implementation issue.

**Condition A token growth:**
Should grow monotonically. Watch for any anomalous plateau — if it stops growing, context is being truncated. This would indicate n_ctx is too low.

**Speed degradation:**
Note tok/s at turn 1, turn 30, turn 60, turn 90, turn 120 for each condition. Condition A context grows to ~200k tokens — KV cache pressure may cause speed reduction in later turns even if n_ctx is sufficient. Document if speed drops below 25 tok/s.

---

## Non-Intervention Rules

Pre-registered. Not negotiable.

1. Do not stop the run unless the process crashes with an unrecoverable error
2. Do not modify the script after S2_007 commit
3. Do not modify any runner or architecture module during the run
4. Do not read rubric response files until all three conditions have completed
5. Observe terminal output only — note anomalies in a separate scratch file
6. If the process crashes: document the turn and error, fix the bug, delete the partial run folder, restart the affected condition from turn 1
7. Run order is fixed: full_context → compaction → iterative. Do not change.
8. If Condition A completes successfully and Condition B crashes, do not re-run Condition A. Resume from Condition B.
9. Compaction events are observation data — do not interfere with compaction timing or content

---

## Run Execution

```powershell
# Confirm pre-run checklist complete
# Confirm GPU active and speed > 30 tok/s
# Then:
python run_study.py
```

The study runner handles all three conditions sequentially. No manual intervention between conditions. The condition start and complete banners tell you where you are.

---

## Post-Run Verification

After all three conditions complete, verify before closing the terminal:

```powershell
# Confirm all three run folders exist
dir experiments\study_002\runs\run_001\

# Confirm iterative DB has episodes
python -c "
import sqlite3
conn = sqlite3.connect('experiments/study_002/runs/run_001/iterative/study.db')
ep = conn.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]
rules = conn.execute('SELECT COUNT(*) FROM rule_store').fetchone()[0]
topics = conn.execute('SELECT COUNT(*) FROM topics').fetchone()[0]
print(f'Episodes: {ep} | Rules: {rules} | Topics: {topics}')
conn.close()
"

# Confirm rubric responses written for all three conditions
dir experiments\study_002\runs\run_001\full_context\rubric\
dir experiments\study_002\runs\run_001\compaction\rubric\
dir experiments\study_002\runs\run_001\iterative\rubric\
```

Expected iterative DB state at run end:
- Episodes: ~118–120 (some turns may not store if both messages are empty)
- Rules: 1–2 (turns 1–2 should have fired detection)
- Topics: < 20 (consolidation should have merged aggressively)

If rules = 0, rule detection did not fire — document and flag for S2_009 analysis. The behavioral consistency bars will be uninterpretable.

---

## Acceptance Criteria — Build Phase

- [ ] Pre-run checklist complete — all 10 items confirmed
- [ ] GPU speed test returns > 30 tok/s
- [ ] CUDA PATH set permanently

---

## Acceptance Criteria — Run Phase

- [ ] All 120 turns complete for all three conditions without unrecoverable crash
- [ ] Three condition run folders populated with all expected files
- [ ] Condition A token estimates grow monotonically across 120 turns
- [ ] Condition B shows `[COMPACTION]` lines at regular intervals
- [ ] Condition C shows K retrieval activity beyond turn 20
- [ ] Condition C shows `[CONSOLIDATION]` lines at expected episode intervals
- [ ] Condition C rule store contains ≥ 1 rule at run end
- [ ] Condition C context tokens stay bounded below Condition A at every turn
- [ ] `rubric/responses.md` written for each condition — turns 112–120 present
- [ ] Post-run DB verification passes

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-063 | Set CUDA PATH permanently via Windows system environment variables |
| S2-T-064 | Run GPU speed verification test — confirm > 30 tok/s |
| S2-T-065 | Complete pre-run checklist — all 10 items |
| S2-T-066 | Execute `python run_study.py` — 120-turn study, all three conditions |
| S2-T-067 | Monitor terminal output — note anomalies in run notes scratch file |
| S2-T-068 | Run post-run DB verification |
| S2-T-069 | Confirm all run folders and rubric files present |
| S2-T-070 | Commit run notes and push S2_008 |

---

## Out of Scope — S2_008

- Rubric scoring (S2_009)
- Analysis (S2_009)
- Any architectural changes based on observations — observe only

---

## Notes

**Do not read rubric responses until all three conditions complete.** The temptation after Condition A finishes is to check whether it recalled the middle-planted facts. Resist this. Reading partial results before all conditions are complete risks unconscious bias when scoring.

**The run is long. Plan for it.** 3.5–4.5 hours of uninterrupted machine time. Ensure the machine does not sleep, the terminal session stays active, and no other GPU-intensive processes run concurrently.

**Run notes are a study artifact.** The scratch file where you note anomalies during the run is part of the research record. It becomes the Protocol Notes section of the Study 002 README. Write it as if someone else will read it — because in Study 003 planning, you will.