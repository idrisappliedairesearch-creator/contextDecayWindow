# Study 002 Pre-Registration — contextDecayWindow
**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** Pre-Registered
**Pre-Registration Date:** 2026-06-06
**Commit SHA:** 6f91d8d
**Study 001 SHA:** 7b03ba4

---

## Research Question

Do the following targeted architectural changes — a soft N retrieval cap, lowered similarity thresholds, automatic LLM-based rule detection with a pinned rule store, and post-assignment topic consolidation — correct the two failure conditions identified in Study 001 (context window exceeding full context, K retrieval effectively inactive) while maintaining or improving coherence scores? And does the iterative architecture outperform full context loading on middle-planted fact survival in a 120-turn conversation designed to induce lost-in-the-middle failure?

---

## Motivation

Study 001 returned VALIDATED on all three success bars but produced two unexpected findings:

**Finding 1 — K retrieval was effectively inactive.** The 0.70 cosine similarity threshold produced only one K retrieval event across 32 turns. The architecture succeeded via decay-based recency (N retrieval), not semantic similarity. This means the architecture cannot retrieve non-recent facts by relevance — a fundamental limitation for long conversations where early-planted facts have decayed out of N scope.

**Finding 2 — Iterative context exceeded full context.** Uncapped N retrieval caused the system to include all 30 episodes in late-turn context windows, producing a peak of 24,854 tokens against full context's 13,231. This triggered the pre-registered failure condition and invalidated the efficiency claim.

**Finding 3 — Behavioral rules were not preserved.** Rules established in early turns embed differently from query embeddings about facts. K retrieval never surfaced rule episodes, and N retrieval buried them under more recent episodes. The system had no mechanism to enforce persistent behavioral constraints.

Study 002 addresses all three findings directly.

---

## Conditions

Three conditions tested against an identical 120-turn scripted conversation across four semantically unrelated topics.

**Condition A — Full Context Loading (ceiling)**
Complete conversation history appended to every prompt in full. Token usage grows O(N). At 120 turns targeting ~1,700 tokens per turn pair, peak context is approximately 200,000 tokens — designed to induce lost-in-the-middle attention degradation in the dense quadratic attention architecture.

**Condition B — Summarization Compaction (current best practice)**
Conversation history periodically summarized when the token threshold is approached. Summary replaces raw history. Prior turns discarded. Compaction threshold: 3,000 tokens (unchanged from Study 001).

**Condition C — Iterative Construction v2 (contextDecayWindow)**
Active context constructed dynamically per turn from episodic memory store with the following changes from Study 001:

- **Soft N cap:** Top 10 decay-sorted episodes included unconditionally. Additional episodes included if they score above the K threshold regardless of cap. Rule episodes appended unconditionally and do not count against the cap.
- **K threshold:** 0.50 (reduced from Study 001's 0.70)
- **Topic assignment threshold:** 0.50 (reduced from Study 001's 0.70)
- **Topic consolidation:** Every 10 stored episodes, scan all topic centroids for pairs with cosine similarity ≥ 0.60. Merge pairs by weighted average centroid. Reassign episodes. Logged to topic_events.csv.
- **Rule store:** Automatic LLM-based rule detection piggybacked on each inference call via structured output tag. Episodes containing behavioral rules are additionally written to a separate rule store and appended to every constructed context window unconditionally.

---

## Hypotheses

**H1 — Full Context Loading**
Detail fidelity will be highest for early-planted and late-planted facts. Middle-planted facts (turns 55–65, token position ~95,000–110,000 in a ~200,000 token context) will show measurable degradation due to lost-in-the-middle attention dilution. This condition is expected to fail on middle-plant survival — the primary stress test of Study 002.

**H2 — Summarization Compaction**
Detail fidelity will degrade sharply at compaction events. Facts planted shortly before a compaction event are most vulnerable. With 120 turns and a 3,000-token threshold, multiple compaction events are expected. Each compaction event discards episodic detail irreversibly.

**H3 — Iterative Construction v2**
With K threshold reduced to 0.50, K retrieval is predicted to fire consistently across turns, surfacing non-recent relevant episodes that decay-based N retrieval would miss. Middle-planted facts should be retrievable via similarity even when decay has buried them in the N sort. Rule pinning is predicted to restore behavioral consistency to the full-context ceiling. Context window should stay bounded well below Condition A's peak due to the soft N cap.

Primary remaining risk: K retrieval at 0.50 may introduce false positives — surfacing loosely related episodes that dilute context quality. Topic bleed risk increases as K becomes less selective.

---

## Model

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B Q6_K |
| Runtime | llama.cpp |
| Hardware | RTX 5090 32GB VRAM |
| Context cap | 147,000 tokens |
| Embedding model | Qwen3-Embedding-0.6B |
| Embedding runtime | CPU (64GB system RAM) |
| Embedding dimensions | 1,024 |

Model is the control variable. Same instance across all conditions.

---

## Architecture Specification (Condition C v2)

### Changed Parameters

| Parameter | Study 001 | Study 002 | Documented Reason |
|-----------|-----------|-----------|-------------------|
| N retrieval cap | Uncapped | Soft cap 10 | Study 001 N converged toward full context loading |
| K threshold | 0.70 | 0.50 | K fired once in 32 turns — threshold too strict for embedding space |
| Topic threshold | 0.70 | 0.50 | 30 topics / 30 episodes — threshold produced singleton proliferation |
| Topic consolidation | None | Every 10 episodes, merge ≥ 0.60 | No compression mechanism active in Study 001 |
| Rule store | None | Automatic LLM detection, pinned | Cat 4 failure — rules embed differently from facts |
| Min episode rule | N/A | Dropped | Threshold fix sufficient; additional constraint conflates variables |

### Rule Detection Mechanism

Rule detection is piggybacked on the existing inference call. The inference prompt instructs the model to append a structured tag after its response:

```
<rule_detection>{"contains_rule": true, "rule_summary": "..."}</rule_detection>
```

The tag is parsed after generation and stripped before the response is shown or stored. If `contains_rule` is true, the episode is written to both the standard episodes table and the rule store. Rule episodes are appended to every subsequent context window unconditionally and do not count against the N soft cap.

Detection accuracy is logged per turn to `metrics/rule_detection.csv` for post-hoc audit. Ground truth for detection accuracy is established by reviewing the script for known rule-setting turns before scoring.

### Topic Consolidation

Fires after episodes 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120 are stored.

Merge condition: cosine similarity between two topic centroids ≥ 0.60.

Merge threshold justification: 0.60 is above the assignment threshold (0.50) to prevent merging topics that are merely related. It is below Study 001's assignment threshold (0.70) to catch topics that drifted genuinely redundant over time.

On merge: new centroid is the weighted average of both centroids weighted by episode count. All episodes from the smaller topic are reassigned to the surviving topic. Merged topic is deleted. In-memory index updated immediately. Logged to topic_events.csv.

### Soft N Cap

Retrieval assembly per turn:

1. Rule episodes — all, always, unconditional
2. N retrieval — top 10 by decay score (hard floor of the soft cap)
3. K retrieval — all episodes above 0.50 cosine similarity to query, regardless of whether they appear in the top-10 N set
4. Deduplicate by episode_id
5. Sort chronologically by turn_number

The soft cap means a highly relevant early episode can always enter context via K even if 10 more recent episodes have saturated the N cap. This directly addresses Study 001's finding that K retrieval was inactive.

---

## Test Script Requirements

The test script will be written in Sprint S2_007, after architecture implementation and observability updates are complete. The script must satisfy all of the following constraints:

1. Exactly 120 turns
2. Four semantically unrelated topics, 30 turns each with abrupt switches
3. Topic domains: civil engineering, Renaissance art history, macroeconomics / monetary policy, marine biology
4. Behavioral rules established in turns 1–2, detectable by keyword and structural language
5. Three planted fact positions:
   - Early: turns 1–5 (beginning of context, token position ~0–8,500)
   - Middle: turns 55–65 (middle of context, token position ~93,500–110,500)
   - Late: turns 100–110 (near end of context, token position ~170,000–187,000)
6. Minimum five verifiable facts per planted position (numerical values, named entities, explicit decisions)
7. Late-session probes at turns 112–120 testing all three positions simultaneously
8. Questions designed to elicit responses of approximately 1,500 tokens (detailed analysis, step-by-step breakdowns, multi-part comparisons) to target ~200,000 tokens for Condition A at peak
9. Fully scripted and reproducible — no generative variance

The script is written against the rubric. The rubric is not written against the script.

---

## Evaluation Rubric

Categories, scoring criteria, and question count are locked here. Specific planted facts substituted when the script is written in Sprint S2_007.

### Category 1 — Early Plant Survival

Tests whether facts planted in turns 1–5 survive to turns 112–120. (3 questions)

- Q1: Specific numerical fact from Topic A planted in turn 1–5
- Q2: Named entity from Topic A planted in turn 1–5
- Q3: Behavioral rule established in turn 1–2 — stated correctly at turn 115+

Scoring: 1.0 = exact | 0.5 = approximate | 0.0 = wrong or absent

### Category 2 — Middle Plant Survival

Tests the lost-in-the-middle hypothesis. Facts planted in turns 55–65, at token position ~100,000 in a ~200,000 token context. (3 questions)

- Q4: Specific numerical fact from Topic B planted in turn 55–65
- Q5: Named entity from Topic B planted in turn 55–65
- Q6: Specific decision or constraint from Topic B planted in turn 55–65

Scoring: 1.0 = exact | 0.5 = approximate | 0.0 = wrong or absent

**This category is the primary test of Study 002.** Condition A is predicted to fail here. Condition C is predicted to succeed via K retrieval.

### Category 3 — Late Plant Survival

Baseline check — recent facts should survive in all conditions. (2 questions)

- Q7: Specific numerical fact from Topic C/D planted in turn 100–110
- Q8: Named entity from Topic C/D planted in turn 100–110

Scoring: 1.0 = exact | 0.5 = approximate | 0.0 = wrong or absent

### Category 4 — Topic Bleed Detection

Four topics, three switches. Expanded from Study 001's two topics. (3 questions)

- Q9: After Topic B switch, ask for a Topic A fact — clean retrieval without Topic B contamination
- Q10: After Topic C switch, ask for a Topic B fact — clean retrieval without Topic C contamination
- Q11: After Topic D switch, ask which researcher/entity belongs to which topic — disambiguation across all four topics

Scoring: binary — 1 = no bleed | 0 = contamination present

### Category 5 — Behavioral Consistency (Rule Pinning Test)

Direct test of the rule pinning mechanism. Rules established in turns 1–2. (2 questions)

- Q12: Are the formatting rules applied correctly in turns 112–120? (assessed by reviewing late-turn responses)
- Q13: Can the model state both rules correctly when asked directly at turn 115+?

Scoring: binary — 1 = rules honored / stated correctly | 0 = rules violated or missing

### Category 6 — Rule Detection Accuracy

Log-based evaluation. Not scored by rubric — assessed separately from metrics/rule_detection.csv.

- Ground truth: rule-setting turns identified from script (turns 1–2)
- Metric: did the LLM correctly tag those turns as `contains_rule: true`?
- False positive rate: did non-rule turns get tagged incorrectly?

Reported as precision and recall in the analysis summary. Not included in overall score.

---

## Success Criteria

**Bar 1 — Middle Plant Survival (primary)**
Condition C scores ≥ Condition A on Category 2. Full context is predicted to fail here; iterative is predicted to succeed via K retrieval. If Condition C also fails, K retrieval at 0.50 is still insufficient or the topic layer is suppressing middle-turn episodes.

**Bar 2 — Token Efficiency (Study 001 failure condition corrected)**
Condition C peak context tokens < Condition A peak context tokens at every turn. This was the pre-registered failure condition in Study 001. It must be corrected for the architecture to be considered viable.

**Bar 3 — Behavioral Consistency improvement**
Condition C Category 5 score > Condition C Study 001 Category 4 score (1/2). Rule pinning must demonstrably improve behavioral consistency over Study 001's baseline.

**Bar 4 — Topic Bleed maintained**
Condition C Category 4 bleed rate ≤ Condition A. Maintained from Study 001, now across four topics and three switches. Confirms that lowering K threshold to 0.50 did not introduce false-positive retrievals causing cross-topic contamination.

**Overall:**
- All 4 bars: VALIDATED
- 3 bars: PARTIAL — document which bar failed and why
- 2 or fewer: INVALIDATED — architectural redesign required before Study 003

---

## Failure Conditions

Pre-registered. Not post-hoc.

- K retrieval fires fewer than 10 times across 120 turns — threshold still too strict or embedding space is unsuitable for similarity retrieval at this granularity
- Topic count at run end > 20 — consolidation mechanism not functioning; threshold or merge logic requires redesign
- Rule detection precision < 0.80 or recall < 1.0 on known rule-setting turns — detection mechanism requires redesign before behavioral consistency claims are valid
- Condition C context window exceeds Condition A at any turn — soft cap logic has an implementation error

---

## Out of Scope — Study 002

- GABA-inspired inhibitory gating (Study 003)
- Consolidation pipeline replacing episodes with summaries (Study 003)
- Multi-model comparison
- Multi-rater evaluation (contingent on Study 002 results)
- Adaptive K threshold

---

## Observability Requirements

All Study 001 observability requirements carried forward. Study 002 additions:

**New metric files:**
- `metrics/rule_detection.csv` — per-turn: turn_number, contains_rule (detected), rule_summary, ground_truth (filled post-run), true_positive, false_positive
- `metrics/consolidation_events.csv` — per consolidation pass: episode_count_at_trigger, topics_before, topics_after, pairs_merged, turn_number

**Terminal output additions:**
```
[RULE STORE] 2 rules pinned | Rule detected this turn: No
[CONSOLIDATION] Triggered at episode 20 | Topics: 14 → 11 | Pairs merged: 3
```

---

## Sprint Sequence — Study 002

| Sprint | Title | Scope |
|--------|-------|-------|
| S2_001 | Pre-Registration | This document. No code. |
| S2_002 | Rule Store + Detection | rule_store DB table, rule_detection structured output, pin mechanism |
| S2_003 | Soft N Cap + Threshold Updates | N cap implementation, K and topic threshold changes |
| S2_004 | Topic Consolidation | Consolidation pass every 10 episodes, merge logic |
| S2_005 | Observability Updates | New metric files, terminal additions, consolidation logging |
| S2_006 | Baseline Updates | Condition B compaction real model call verification, n_ctx confirm |
| S2_007 | Test Script + Rubric | Rubric specifics first, then 120-turn script |
| S2_008 | Study Run | Execute all three conditions |
| S2_009 | Analysis + Writeup | Score rubric, analyze metrics, write experiments/study_002/README.md |

---

## SHA Record

**Pre-registration commit SHA:** 6f91d8d
**Committed by:** Muzaffer Ozen
**Date:** 2026-06-06

This SHA is the study's tamper-evident timestamp. Record it before any implementation begins.

---

*Idris Applied AI Research — Study 002*
*contextDecayWindow*
*Do not modify this document after the SHA is recorded.*