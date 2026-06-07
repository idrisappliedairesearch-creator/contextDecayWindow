# Study 002 — Run Notes (S2_008)

**Run:** run_001
**Date:** 2026-06-06
**Model:** Qwen3.6-27B-Q6_K GGUF
**Inference:** llama.cpp, n_ctx=262144, q8_0 KV cache, flash_attn enabled
**Embedding:** Qwen3-Embedding-0.6B-Q8_0, CPU-only (n_gpu_layers=0)

---

## Configuration Notes

- KV cache downgraded from f16 to q8_0 to fit n_ctx=262144 in available VRAM
- Flash attention enabled
- Embedding model runs on CPU (n_gpu_layers=0)
- CUDA PATH (v12.6) confirmed permanent in system environment variables

## Run Duration

| Condition | Start | End | Duration |
|---|---|---|---|
| full_context | ~8:00 PM | ~10:13 PM | ~2h 13m |
| compaction | ~10:13 PM | ~10:41 PM | ~28m |
| iterative | ~10:41 PM | ~11:25 PM | ~44m |
| **Total** | | | **~2h 55m** |

Total was shorter than the 3.5–4.5 hour estimate. Likely due to q8_0 KV cache improving throughput, and compaction/iterative context staying bounded.

## Speed Degradation — Condition A (full_context)

| Turn | tok/s | Context (est.) |
|---|---|---|
| 1 | 0.0 (0 output tokens) | 233 |
| 30 | 32.6 | 33,862 |
| 60 | 20.7 | 70,271 |
| 90 | 13.9 | 107,173 |
| 120 | 11.3 | 132,727 |

**Observation:** Steady degradation from 58 tok/s (turn 2) down to 11.3 tok/s by turn 120. Context grew to ~132k tokens. Never dropped below 25 tok/s until around turn 72. By turn 99, speed hit 0.3 tok/s (19 output tokens) — possible KV cache pressure or page fault. Speed recovered to ~13 tok/s afterward. Consistent with KV cache growth on GPU.

**Anomaly:** Turn 1 produced 0 output tokens (0.0 tok/s). Turn 2 hit 1024 output tokens at 57.6 tok/s. Turn 1 likely returned a very short or empty response.

## Condition B (compaction)

- **30 compaction events** across 120 turns (~1 per 4 turns)
- Context stayed bounded: 1,351 tokens at turn 120 (vs 3,034 at turn 60)
- Speed remained stable at 55–58 tok/s throughout (context never accumulated)
- **36 of 120 turns produced 0 output tokens** (30% zero-token rate). These likely correspond to compaction summary inference calls being recorded in `model_performance.csv` alongside actual turn responses. Need to verify in S2_009 whether the runner is double-logging (once for compaction call, once for turn call), or whether the model genuinely returned empty responses.
- Zero-token turns: 8, 10–13, 16, 22–23, 37–52 (16 consecutive), 54–56, 72, 97–102, 107–108

**Anomaly:** The 16-consecutive-turn stretch (37–52) is the most concerning. Either the compaction mechanism is generating very long summaries that saturate the context window, or the model stopped producing output. Verify rubric responses for turns 112–120 to confirm compaction condition produced usable late-turn output.

## Condition C (iterative)

### Episodes & Topics

| Metric | Value | Expected |
|---|---|---|
| Episodes | 120 | ~118–120 |
| Rules | 1 | ≥1 |
| Topics | 52 | <20 |

**CRITICAL FLAG:** 52 topics at run end. Spec expected <20. Consolidation events CSV is empty (header only) — **zero consolidation events fired**. The 0.60 merge threshold was never met, or the consolidation trigger at episodes 10/20/30... did not fire. This means the 52 topics were never merged. This is the primary finding for S2_009 analysis and Study 003 planning.

### Rule Detection

- **Iterative:** Rule detected on turn 1 only (1 rule). Summary: "Always format technical specifications and multiple items as numbered lists, and always conclude structural or engineering recommendations with a risk classification in parentheses (Low/Medium/High)."
- **Full context:** 0 rules detected across all 120 turns. The rule detection mechanism did not fire at all in full_context. This is an anomaly — turns 1–2 should have triggered detection in all conditions. The `ground_truth`, `true_positive`, and `false_positive` columns are empty across all conditions, meaning post-run validation was not populated.

### K Retrieval Activity

- Total retrieval events: 100 across 120 turns
- K fired from turn 2 onward, consistently
- Peak K=5 at turns 116, 117, and 120 (late-turn probe questions)
- K=1 for most early turns; K=2–3 by mid-study; K=3–5 in final probe turns
- Retrieval was active well beyond turn 20 as expected

### Context Token Bounds

Context stayed well bounded:

| Turn | Est. Tokens |
|---|---|
| 1 | 7 |
| 30 | 9,482 |
| 60 | 10,748 |
| 90 | 10,452 |
| 120 | 11,349 |

Speed remained stable at 43 tok/s throughout (never dropped below 35 tok/s). No degradation because context never grew.

### Consolidation

**Zero consolidation events.** The `consolidation_events.csv` file contains only a header row. Topics grew from 1 to 52 with no merging. This means either:
1. The episode-based trigger (episodes 10, 20, 30...) did not fire
2. The 0.60 similarity threshold for merging was never met between any topic pairs
3. Both

This is the key finding for Study 003 planning. The merge threshold or trigger mechanism needs investigation.

## Summary — Flags for S2_009

1. **Consolidation never fired (0 events, 52 topics)** — critical. Merge threshold or trigger mechanism needs fixing before Study 003.
2. **Compaction 0-token stretches** — turns 37–52 produced 16 consecutive zero-token turns. Verify rubric quality for compaction condition.
3. **Rule detection failed in full_context** — 0 rules detected across all 120 turns. Iterative correctly detected 1 rule on turn 1. Investigate whether full_context runner is suppressing rule detection.
4. **Full context speed degradation** — from 58 to 11.3 tok/s over 120 turns. Acceptable and expected with growing KV cache, but turn 99 dropped to 0.3 tok/s.
5. **Run completed faster than estimated** — ~2h 55m vs 3.5–4.5h estimate. q8_0 KV cache improved throughput significantly.

---

## Non-Intervention Compliance

All 9 non-intervention rules observed. No code was modified during the run. No rubric responses were read until all three conditions completed. Run order was fixed: full_context → compaction → iterative.

## Artifacts

All expected files present:
- `full_context/`: logs/, snapshots/, metrics/, constructed_prompts/, rubric/responses.md
- `compaction/`: logs/, snapshots/, metrics/, constructed_prompts/, rubric/responses.md
- `iterative/`: logs/, snapshots/, metrics/, constructed_prompts/, rubric/responses.md, study.db
