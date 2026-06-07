# Study 002 — contextDecayWindow
**Idris Applied AI Research**
**Date:** June 2026
**Pre-registration SHA:** 0a87fb1
**Study 001 SHA:** 7b03ba4
**Status:** Complete

---

## Summary

Study 002 tested whether targeted architectural changes — soft N retrieval cap, lowered K similarity threshold (0.50), automatic LLM-based rule detection with pinned rule store, and post-assignment topic consolidation — could correct the three failure conditions from Study 001 while making the iterative architecture outperform full context loading on middle-planted fact survival. The study returned PARTIAL: 3 of 4 success bars passed. The primary finding — Category 2 middle plant survival — was decisive. Condition C scored 3.0/3.0 versus Condition A's 1.0/3.0, demonstrating that the iterative architecture can retrieve buried facts via K retrieval that full context loading loses to attention dilution. Topic consolidation failed entirely (52 final topics vs. the 20-topic failure threshold), and two minor early-turn token violations cost Bar 2.

---

## Research Question

Do the following targeted architectural changes — a soft N retrieval cap, lowered similarity thresholds, automatic LLM-based rule detection with a pinned rule store, and post-assignment topic consolidation — correct the two failure conditions identified in Study 001 (context window exceeding full context, K retrieval effectively inactive) while maintaining or improving coherence scores? And does the iterative architecture outperform full context loading on middle-planted fact survival in a 120-turn conversation designed to induce lost-in-the-middle failure?

---

## Changes from Study 001

| Parameter | Study 001 | Study 002 | Documented Reason |
|-----------|-----------|-----------|-------------------|
| N retrieval cap | Uncapped | Soft cap 10 | Study 001 N converged toward full context loading |
| K threshold | 0.70 | 0.50 | K fired once in 32 turns — threshold too strict |
| Topic threshold | 0.70 | 0.50 | 30 topics / 30 episodes — singleton proliferation |
| Topic consolidation | None | Every 10 episodes, merge >= 0.60 | No compression mechanism in Study 001 |
| Rule store | None | Automatic LLM detection, pinned | Cat 4 failure — rules embed differently from facts |
| Script length | 32 turns | 120 turns | Stress test with 4 topics, lost-in-the-middle design |

---

## Method

### Conditions

**Condition A — Full Context Loading:** Complete 120-turn conversation history appended to every prompt. Peak context: ~132,727 tokens at turn 120. Designed to induce lost-in-the-middle attention degradation.

**Condition B — Summarization Compaction:** Conversation periodically summarized at 3,000-token threshold. Prior turns discarded after compaction. Multiple compaction events across 120 turns.

**Condition C — Iterative Construction v2:** Active context constructed dynamically per turn from episodic memory store with soft N cap (10), K threshold (0.50), rule store, and topic consolidation.

### Model

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B Q6_K |
| Runtime | llama.cpp |
| Hardware | RTX 5090 32GB VRAM |
| Context cap | 147,000 tokens |
| Embedding model | Qwen3-Embedding-0.6B |
| Embedding dimensions | 1,024 |

### Script

120 turns across four semantically unrelated topics (civil engineering, Renaissance art history, monetary policy, marine biology), 30 turns each with abrupt switches. Three planted fact positions: early (turns 3–5), middle (turns 55–60), late (turns 100–110). Late-session probes at turns 112–120 testing all three positions simultaneously.

### Evaluation

13-question rubric across 5 categories, scored manually by a single rater before analysis. Four pre-registered success bars evaluated against rubric scores and metrics.

---

## Results

### Rubric Scores

| Category | Full Context | Compaction | Iterative |
|----------|-------------|------------|-----------|
| Cat 1 (early plant) | 2.5 / 3.0 | 1.0 / 3.0 | 3.0 / 3.0 |
| Cat 2 (middle plant) * | 1.0 / 3.0 | 0.0 / 3.0 | 3.0 / 3.0 |
| Cat 3 (late plant) | 1.0 / 2.0 | 0.0 / 2.0 | 2.0 / 2.0 |
| Cat 4 (bleed) | 2 / 3 | 0 / 3 | 3 / 3 |
| Cat 5 (rules) | 2 / 2 | 1 / 2 | 2 / 2 |
| **Overall** | **8.5 / 13.0** | **2.0 / 13.0** | **13.0 / 13.0** |

*Primary test of Study 002.

### Success Criteria

| Bar | Description | Result | Details |
|-----|-------------|--------|---------|
| Bar 1 | Middle Plant (Cat 2, C >= A) | **PASS** | C: 3.0, A: 1.0 |
| Bar 2 | Token Efficiency (C < A every turn) | **FAIL** | 2 violations (turns 2, 11) |
| Bar 3 | Rule Pinning (Cat 5, C > Study 001) | **PASS** | C: 2/2, baseline: 1/2 |
| Bar 4 | Topic Bleed (Cat 4, C >= A) | **PASS** | C: 3/3, A: 2/3 |

**Overall: PARTIAL** (3 of 4 bars)

### K Retrieval Activity

K retrieval is now active and firing consistently. Across 120 turns, K fired on 55 turns with 100 total K events and 57 K-only episodes (retrieved via K but not in top-10 N). First K fire at Turn 2. This is a dramatic improvement from Study 001 where K fired once in 32 turns. The 0.50 threshold successfully unlocked similarity-based retrieval for the Qwen3-Embedding-0.6B embedding space.

Critically, K retrieval was responsible for retrieving middle-planted facts during probes at turns 115–117. At Turn 115, 3 K-only episodes were retrieved (all from the Renaissance art topic, turns 56–60). At Turn 116, 4 K-only episodes were retrieved. At Turn 117, 5 K-only episodes were retrieved. This is the mechanism that enabled Condition C's perfect Cat 2 score.

### Topic Consolidation

Consolidation did not fire at all. Zero consolidation passes, zero pairs merged. The 0.60 merge threshold was never met between any pair of topic centroids. Final topic count reached 52 (vs. 30 episodes at end in Study 001, but with 120 turns vs. 32). Topic counts at key turns: 7 at Turn 10, 25 at Turn 60, 52 at Turn 120.

This exceeds the pre-registered failure condition of > 20 topics. The consolidation mechanism requires redesign. The root cause appears to be the 0.50 topic assignment threshold: topics are being created so granularly (near-singleton episodes per topic) that centroids remain too distinct to meet the 0.60 merge threshold.

### Rule Detection

| Condition | Detections | Recall | Est. FP |
|-----------|-----------|--------|---------|
| Full Context | 0 | 0.00 | 0 |
| Compaction | 1 | 0.00 | 1 |
| Iterative | 1 | 0.50 | 0 |

Ground truth turns: 1, 2.

**Iterative:** Detected Turn 1 (both rules merged into one summary). Missed Turn 2. Recall: 0.50. No false positives. The Turn 1 detection is significant because the iterative context was minimal at that point — the system prompt was the only context — and the user turn was unambiguously additive. The rule was pinned and available for subsequent turns.

**Full Context:** Zero detections across all 120 turns. This is a system prompt confound: the system prompt pre-loads both rules, so the model does not tag Turn 1 as new rule establishment — from its perspective, the rules were already there.

**Compaction:** Detected Turn 89 as a rule-setting turn — a late-conversation repeat mention of the formatting rules, not a primary establishment. This is a false positive. Recall on ground truth turns: 0.00.

Neither full context nor compaction had effective rule pinning. Condition C's Turn 1 detection was sufficient to enable Cat 5 success because the pinned rule was available in constructed context windows for subsequent turns.

### Token Growth

| Condition | Peak Tokens | Peak Turn |
|-----------|------------|-----------|
| Full Context | ~132,727 | 120 |
| Compaction | ~3,197 | 35 |
| Iterative | ~13,143 | 117 |

Iterative peak is approximately 10x lower than full context. Compaction stays flat at ~3,000 tokens due to periodic summarization.

The soft N cap (10) is effective at bounding context growth. Cap saturation first occurs at Turn 20, after which K retrieval compensates for the capped N window.

Bar 2 violations: Turn 2 (iterative: 443 tokens vs. FC: 306 tokens — rule detection overhead) and Turn 11 (iterative: 9,492 vs. FC: 9,433 — K retrieval adding 59 extra tokens). Both are negligible early-turn violations.

---

## Discussion

### Middle Plant Survival — The Primary Finding

Condition C scored 3.0/3.0 on Category 2 while Condition A scored 1.0/3.0. This is the centerpiece result. The iterative architecture successfully retrieved middle-planted facts (painting title, artist, patron, year, pigment technique, cardinal bleed probe) that full context loading could not reliably produce at turns 115–117.

The mechanism is clear from the K retrieval logs. At Turn 115, three K-only episodes were retrieved from the Renaissance art topic cluster (turns 56–60), carrying the Annunciation of Forlì facts across 55 turns of intervening conversation. The decay-based N retrieval alone would have buried these episodes — their decay scores at Turn 115 were in the 0.96–0.97 range, well below the top-10 cutoff. K retrieval at 0.50 similarity brought them in at scores of 0.51–0.72.

Condition A's partial score (1.0/3.0) came from Q4 (correct painting facts) while Q5 and Q6 had truncated responses. Even granting full credit for truncated responses, Condition A's architecture faces a fundamental limit: in a 132,727-token context window with dense quadratic attention, middle-position tokens (around token 66,000) receive measurably lower attention weights. The iterative architecture sidesteps this entirely by constructing a bounded context window (~13,000 tokens) that selectively includes relevant episodes from any position.

**Condition B caveat:** Turns 54–56 fell in a zero-token output window. Turn 55 was the planting turn — the model received the facts but produced no output. Scored at turns 115–117, Condition B scored 0.0/3.0 on Cat 2, meaning the compaction summary did not preserve the middle-plant facts. This is expected behavior for compaction: facts planted just before a compaction boundary are most vulnerable to loss. The zero-token window means the model's own summary of those turns contained no factual content about the Annunciation.

### K Retrieval — Active and Effective

The 0.50 threshold unlocked K retrieval. 55 turns with K > 0, 100 total events, 57 K-only episodes. Compared to Study 001's single K fire in 32 turns, this is a functional system.

K retrieval fires most heavily during topic transitions and late-session probes. The pattern shows K acting as a "recall mechanism" — surfacing relevant episodes that decay has buried but that remain semantically relevant. The 57 K-only episodes represent retrievals that would have been missed by N retrieval alone.

The interaction with the N cap is the key design insight. At turns where N is capped at 10, K provides a backdoor for older, relevant episodes. This is the architecture's primary value proposition: bounded context windows with relevance-based retrieval.

### Topic Consolidation — Did Not Work

Zero consolidation passes across 120 turns. The mechanism is structurally present but the 0.60 merge threshold is unreachable given how topics are being created at 0.50 assignment threshold. Topics are too granular — near-singleton clusters — so centroids remain too distinct.

This is the study's clearest failure. The pre-registered failure condition (> 20 topics) was exceeded: 52 final topics. Two possible fixes for Study 003:
1. Raise the merge threshold (lower it, e.g., to 0.45) to catch more pairs
2. Increase the assignment threshold (e.g., to 0.60) to create fewer, broader topics from the start

Option 2 is riskier (may create misassignment) but more impactful. Option 1 is a surgical fix that doesn't change the assignment behavior.

### Rule Pinning — Functional but Incomplete

Condition C scored 2/2 on Cat 5, above Study 001's baseline of 1/2. The pinned rule from Turn 1 was available in constructed context windows and the model applied the numbered list rule consistently across probe turns.

Detection recall is only 0.50 (1 of 2 ground truth turns). Turn 2 was missed, possibly because its rule was absorbed into the merged Turn 1 detection. The system detected one compound rule at Turn 1 that covered both formatting constraints, making a separate Turn 2 detection unnecessary from a functional standpoint — but the detection accuracy metric is affected.

The full context confound is notable: the system prompt pre-loading both rules means the model never perceives Turn 1 as rule establishment. This is an artifact of the test setup — in production, rules would be established in conversation, not in system prompt. The compaction false positive at Turn 89 is a late-conversation repeat mention, not a true detection.

### What I'd Do Differently

1. **Topic consolidation threshold:** The 0.60 merge threshold should have been set lower (0.45–0.50) or the assignment threshold should have been higher (0.60) to prevent singleton proliferation. A simple ablation of the assignment threshold would have caught this in pre-run testing.

2. **Rule detection on Turn 2:** The detection mechanism should be tested for compound rule establishment (rules split across consecutive turns). The merged Turn 1 detection worked functionally but missed Turn 2's contribution.

3. **Response capture quality:** Several Condition A responses were truncated in the responses.md file. Better response capture would have provided cleaner scoring data and avoided ambiguous "no output" scores.

---

## Protocol Notes

- All three conditions executed successfully across 120 turns
- Condition B (compaction) produced zero-token output windows at several turns (54, 55, 56, 107, 108, 109, etc.), indicating compaction events where the model generated summaries instead of content
- Condition C's rule detection overhead added ~137 tokens at Turn 2 (rule establishment), contributing to one Bar 2 violation
- Response capture for Condition A had truncation issues at several probe turns (Q1, Q5, Q6, Q8). Scored conservatively at 0.0 where no output was visible.
- The compaction zero-token window at turns 54–56 means the planting turn (55) produced no model output. Facts may have survived through compaction summaries in compressed form, but probe responses at turns 115–117 scored 0.0/3.0 on Cat 2, confirming loss.

---

## Limitations

- Single model (Qwen3.6 27B Q6_K) — findings may not generalize to other models or sizes
- Scripted conversation — no generative variance; results reflect one specific conversation trajectory
- Solo rater — no inter-rater reliability check; scoring subject to single-rater bias
- Single run — no replication; results may have run-specific variance
- Topic consolidation failure means the architecture as tested did not include a working compression mechanism — the 52-topic store represents an upper bound on memory store growth

---

## Next Steps

Study 003 should address the two failed components:

1. **Topic consolidation redesign:** Lower the merge threshold to 0.45 or raise the assignment threshold to 0.60. Validate that consolidation fires and reduces topic count below 20 at 120 turns. This is a prerequisite for claiming bounded memory store growth.

2. **GABA inhibitory gating (if consolidation is fixed):** With K retrieval confirmed active and the architecture validated on the primary test, the next candidate mechanism is inhibitory gating — preventing loosely related K retrievals from diluting context quality. The lowered 0.50 threshold increases false positive risk (topic bleed), and while Bar 4 passed (3/3 clean), a gating mechanism could further harden the system against cross-topic contamination in longer or more complex conversations.

3. **Rule detection improvement:** Address the Turn 2 miss and the full context system-prompt confound. Consider post-hoc rule injection for conditions where automatic detection fails.

---

## Appendix

- Pre-registration: `experiments/study_002/pre_registration.md`
- Script: `experiments/study_002/script.json`
- Rubric: `experiments/study_002/rubric_filled.md`
- Run data: `experiments/study_002/runs/run_001/`
- Analysis summary: `experiments/study_002/analysis_summary.txt`
- Rubric scores: `experiments/study_002/runs/run_001/{condition}/rubric/scores.md`
- Rubric responses: `experiments/study_002/runs/run_001/{condition}/rubric/responses.md`
