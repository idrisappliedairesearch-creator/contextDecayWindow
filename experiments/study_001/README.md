# Study 001 -- contextDecayWindow
**Idris Applied AI Research**
**Date:** June 2026
**Pre-registration SHA:** 7b03ba4
**Status:** Complete

---

## Summary

Study 001 tested whether embedding-based, iterative context construction can maintain conversational coherence across a 32-turn, two-topic session better than full context loading and summarization compaction. The architecture passed all three pre-registered success criteria: it matched the full-context ceiling on detail fidelity (5.0/5.0), achieved zero topic bleed (3/3), and tied compaction on behavioral consistency (1/2). The overall result is VALIDATED. However, two unexpected findings emerged: the iterative context window grew larger than full context (triggering a pre-registered failure condition), and K retrieval barely fired, meaning the architecture succeeded primarily through decay-based recency rather than similarity matching.

---

## Research Question

Can an iteratively constructed context window, built from embedding-based retrieval over a hierarchical episodic memory store, maintain conversational coherence across a long session -- specifically under abrupt topic switching and extended conversation duration -- compared to full context loading and summarization compaction?

---

## Method

### Conditions

Three conditions ran against an identical 32-turn scripted conversation with two abrupt topic switches (Meridian software project, then CRISPR-Cas9 gene editing) and late-session return probes for early-planted facts.

**Condition A -- Full Context Loading (ceiling):** Complete conversation history appended to every prompt in full. No compression, no retrieval.

**Condition B -- Summarization Compaction (current best practice):** Conversation history periodically summarized by the model when a token threshold was approached. The summary replaced raw history. Prior turns discarded.

**Condition C -- Iterative Construction (contextDecayWindow):** At each turn, active context constructed dynamically from a SQLite episodic memory store. Episodes retrieved by two mechanisms: K retrieval (cosine similarity >= 0.70 to query embedding) and N retrieval (all episodes sorted by decay score from last retrieval timestamp). Retrieved episodes assembled chronologically.

### Model

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B Q6_K |
| Runtime | llama.cpp / Ollama |
| Hardware | RTX 5090 32GB VRAM |
| Context cap | 147,000 tokens |
| Embedding model | Qwen3-Embedding-0.6B (CPU) |
| Embedding dimensions | 1024 |

Same model instance, same quantization, same context cap across all three conditions. The independent variable is the memory architecture.

### Script

32 turns. Topic A (Meridian) in turns 1-11: project parameters with five specific numerical facts and two behavioral rules. Topic B (CRISPR-Cas9) in turns 12-19: abrupt topic switch with five additional planted facts. Turns 20-32: late-session probes returning to early facts from both topics, plus topic bleed checks and behavioral consistency tests. Fully scripted and reproducible.

### Evaluation

10-question rubric across four categories:
- **Category 1 (Numerical Detail, Q1-Q3):** Exact recall of budget ($47,500), performance target (180ms P95), CRISPR dosage (2.5 mg/kg). Scored 1.0/0.5/0.0.
- **Category 2 (Named Entity, Q4-Q5):** Exact recall of lead engineer + deadline, cell line + expression rate. Scored 1.0/0.5/0.0.
- **Category 3 (Topic Bleed, Q6-Q8):** Clean retrieval without cross-topic contamination. Scored binary (1/0).
- **Category 4 (Behavioral Consistency, Q9-Q10):** Formatting rules recalled and applied in late turns. Scored binary (1/0).

Three pre-registered success bars:
- **Bar 1:** Condition C Cat1+2 >= 15 percentage points above Condition B
- **Bar 2:** Condition C topic bleed rate <= Condition A
- **Bar 3:** Condition C Cat4 >= Condition B

---

## Results

### Rubric Scores

| Category | Full Context | Compaction | Iterative |
|----------|-------------|------------|-----------|
| Cat 1+2 (detail) | 5.0 / 5.0 | 2.5 / 5.0 | 5.0 / 5.0 |
| Cat 3 (bleed) | 3 / 3 | 0 / 3 | 3 / 3 |
| Cat 4 (behavior) | 2 / 2 | 1 / 2 | 1 / 2 |
| **Overall** | **10.0 / 10.0** | **3.5 / 10.0** | **9.0 / 10.0** |

### Success Criteria

| Bar | Description | Result |
|-----|-------------|--------|
| 1 | Detail Fidelity (Cat1+2, C vs B, >=15pp) | **PASS** -- C: 5.0, B: 2.5, delta: 2.50pp (threshold: 0.75pp) |
| 2 | Topic Bleed (Cat3, C <= A) | **PASS** -- C: 3/3, A: 3/3 |
| 3 | Behavioral Consistency (Cat4, C >= B) | **PASS** -- C: 1/2, B: 1/2 |

**Overall: VALIDATED**

### Token Growth

| Condition | Peak Context | Peak Turn | Notes |
|-----------|-------------|-----------|-------|
| Full Context | ~13,231 tokens | 32 | Linear O(N) growth as expected |
| Compaction | ~3,098 tokens | 4 | 8 compaction events; summary replaced history |
| Iterative | ~24,854 tokens | 32 | **Exceeded full context** -- unexpected |

The iterative condition's peak context was nearly double the full context peak. This triggers the pre-registered failure condition: "Condition C context window token count exceeds Condition A at any turn." The root cause is discussed below.

### Condition C Retrieval Behavior

| Metric | Value |
|--------|-------|
| Avg K per turn | 1.0 episodes |
| Total K retrieval events | 1 (turn 30 only) |
| Final topic count | 30 |
| Final episode count | 30 |

The K retrieval mechanism (similarity-based) only fired once across the entire 32-turn run. This means the architecture was operating almost entirely as a decay-based recency system (N retrieval), not as a similarity-based retrieval system. The 0.70 similarity threshold was so selective that it rarely surfaced matches.

The topic layer created 30 topics for 32 episodes -- nearly one topic per episode. The centroid similarity threshold of 0.70 was too strict to produce meaningful topic consolidation. The topic layer organized episodes but did not meaningfully reduce retrieval scope.

---

## Discussion

### Detail fidelity: The architecture works, but not for the reason I predicted.

Hypothesis 3 predicted that embedding retrieval would surface high-salience facts on demand, outperforming compaction because facts are stored verbatim rather than compressed. The result confirms this: iterative scored 5.0/5.0 on detail, matching the full-context ceiling and far exceeding compaction (2.5/5.0).

But the mechanism wasn't similarity matching. K retrieval only fired once. The architecture succeeded because N retrieval (decay-sorted recency) pulled the relevant episodes into context. The episodes containing planted facts were still recent enough in the decay sort to be retrieved. If this conversation had been 100 turns long with facts planted in turns 2-5, those episodes would have decayed far enough down the sort that they might not have been retrieved. The architecture may have succeeded on recency, not relevance.

This is a critical distinction. The pre-registration called this "embedding-based retrieval." The data shows it operated as "decay-based recency retrieval." The embedding mechanism exists but is effectively inactive at the 0.70 threshold. Study 002 should test with a lower threshold to see whether K retrieval actually contributes to recall, and test with longer conversations where recency alone wouldn't surface early-planted facts.

### Topic bleed: Natural isolation is real and robust.

Iterative achieved zero topic bleed, matching the full-context ceiling. When the user asked "What was the response time target?" after 8 turns of CRISPR discussion, the system retrieved only Meridian episodes. When asked for CRISPR facts after returning to Meridian, it retrieved only CRISPR episodes. No cross-contamination.

This is the strongest architectural finding. It emerged from two mechanisms working in concert: K retrieval's 0.70 threshold excluded irrelevant-topic episodes from similarity matches, and N retrieval's decay sort prioritized recent episodes (which belonged to the current topic). The topic layer contributed by organizing episodes into nodes, but even without effective topic consolidation (30 topics, 30 episodes), the retrieval mechanics naturally isolated topics.

Compaction achieved a 0/3 on topic bleed, but for the wrong reason: the compaction summary at turn 14 discarded the entire Meridian topic and kept only CRISPR content. When the user asked about Meridian at turn 20, the model had no Meridian context to retrieve. This isn't "low bleed" -- it's "complete loss." The compaction mechanism is lossy in a way that's invisible until you probe for the missing content. The model doesn't know what it doesn't know.

### Behavioral consistency: The architectural blind spot.

Both iterative (1/2) and compaction (1/2) underperformed full context (2/2) on behavioral consistency. The two formatting rules established in Turn 1 -- numbered lists for multiple items, confidence levels on technical recommendations -- were not applied in late turns by either Condition B or Condition C.

For compaction, this is expected: the rules were established in Turn 1, and the compaction summary at turn 14 compressed early turns into prose. The specific formatting instructions didn't survive the summary cut.

For iterative, this reveals a fundamental limitation. The formatting rules exist verbatim in the memory store as Turn 1's episode. But when the user asks "What is the budget?" at turn 25, the embedding of that query is similar to budget-related episodes, not to formatting-rule episodes. The K threshold doesn't surface the rule episode, and the N decay sort buries it under more recent episodes. The architecture can retrieve facts but can't retrieve rules, because facts and rules embed differently from the queries that need them.

This isn't a bug -- it's a design constraint. Embedding retrieval optimizes for topical relevance. Formatting rules are not topical; they're structural. They need a different retrieval mechanism: always-include rule episodes, or a separate rule store that's appended to every context window regardless of retrieval. Study 002 should implement rule pinning.

### Token growth: The architecture failed its efficiency target.

The iterative condition's peak context (24,854 tokens) exceeded the full context peak (13,231 tokens). This is the opposite of what was hypothesized. The pre-registration stated that the context window would grow sub-linearly. Instead, it grew super-linearly.

The cause is clear: N retrieval pulls all episodes in the store, sorted by decay. With 30 episodes and no cap on how many N retrieves, the system constructed context from most of the conversation history by the later turns. The decay sort doesn't gate -- it only sorts. Without a cap on N retrieval, the system converges toward full context loading, just in a different order.

The 30-topic fragmentation also contributed: with nearly every episode in its own topic, the topic layer provided no compression. The architecture has three mechanisms that should reduce context size (K threshold, topic consolidation, N cap), and none of them were effective at Study 001 settings. K was too strict (0.70), topic assignment was too strict (0.70), and N had no cap.

This is a failure condition per the pre-registration. It doesn't invalidate the detail fidelity or topic bleed findings, but it does mean the architecture didn't achieve its third goal: efficiency. Study 002 needs to address all three parameters: lower the K threshold (or make it adaptive), lower the topic assignment threshold (or implement consolidation), and cap N retrieval at a fixed number of episodes.

### What I'd do differently

If I were to run this study again with what I know now:

1. **Cap N retrieval.** The single most impactful change. Limiting N to, say, the top 5-10 decay-sorted episodes would immediately reduce context size and force K retrieval to do more of the work.

2. **Pin structural rules.** Separate formatting and behavioral rules from episodic memory. Append them to every context window. They're not facts to be retrieved -- they're constraints to be enforced.

3. **Lower the K threshold to 0.50.** The 0.70 threshold was too selective for Qwen3-Embedding-0.6B. The model's embedding space may be more diffuse than expected. A lower threshold would let K retrieval actually function.

4. **Cap topic count or use a consolidation step.** 30 topics for 32 episodes provides no compression. A post-hoc consolidation step that merges topics with high centroid similarity would reduce fragmentation.

5. **Test with a longer conversation.** The 32-turn length may have been too short to stress the architecture. Early-planted facts were still recent enough for decay retrieval. A 60+ turn conversation would force the system to rely on similarity matching.

---

## Protocol Notes

Three engineering issues required resolution during the study run:

1. **CUDA PATH configuration:** The initial run failed with a CUDA initialization error on Windows. The fix was ensuring the NVIDIA CUDA binaries directory was in the system PATH before launching the inference process. This is a known issue with llama.cpp on Windows and doesn't affect the study's validity, but it required a full restart of the compaction condition.

2. **n_ctx calibration:** The context cap of 147,000 tokens required three restart attempts to calibrate correctly. The first attempt used an insufficient n_ctx value that truncated context in the middle of the full_context run. The second attempt set n_ctx too high, causing OOM on the RTX 5090's 32GB VRAM. The third attempt found the correct setting. All three conditions were re-run with the calibrated value.

3. **Unicode encoding fix:** The initial run produced garbled output in the terminal due to cp1252 encoding on Windows. The fix was setting PYTHONIOENCODING=utf-8 for the run process. This affected terminal output and log files but did not affect the model's responses or the metric data.

These are real engineering discoveries about running local inference on Windows for research purposes. They are findings, not failures.

---

## Limitations

Study 001 has four specific limitations that constrain the strength of its claims:

1. **Single model.** Results are specific to Qwen3.6 27B Q6_K with its full quadratic attention architecture. Different models (especially those with sliding window or attention streaming) may interact with the retrieval mechanisms differently.

2. **Scripted conversation.** The test script is deterministic and controlled. Real conversations have branching structure, user corrections, and topical drift that may stress the architecture differently. The 32-turn length may be too short to expose long-term decay failures.

3. **Solo rater.** Rubric scoring was performed by a single rater (Muzaffer Ozen) without inter-rater reliability checks. While the scoring criteria are explicit and the responses are largely unambiguous, a second rater would strengthen the findings.

4. **Single run.** Each condition ran once. There's no measure of variance across runs. The compaction condition's performance, in particular, depends on the model's summary quality, which may vary across runs.

For stronger claims, Study 002 should test with multiple runs per condition, a longer conversation script, and a second rater for scoring.

---

## Next Steps

Based on Study 001's findings, Study 002 should investigate:

1. **Rule pinning mechanism.** Separate structural rules from episodic memory. Measure whether always-included rules improve behavioral consistency without bloating context size.

2. **N retrieval cap.** Implement a hard cap on N retrieval (e.g., top 10 decay-sorted episodes). Measure impact on context size and whether K retrieval compensates for the reduced N scope.

3. **K threshold tuning.** Test thresholds from 0.40 to 0.70 in increments. Measure recall rate vs. context size tradeoff.

4. **Longer conversations.** Extend the script to 60+ turns. Plant facts in the first 5 turns. Force the system to retrieve non-recent episodes.

5. **Topic consolidation.** Implement a post-storage consolidation step that merges topics with centroid similarity above a threshold. Measure impact on topic count and retrieval quality.

---

## Appendix

- Pre-registration: `experiments/study_001/pre_registration.md`
- Script: `experiments/study_001/script.json`
- Rubric: `experiments/study_001/rubric_filled.md`
- Run data: `experiments/study_001/runs/run_001/`
- Analysis summary: `experiments/study_001/analysis_summary.txt`
- Scoring sheets: `experiments/study_001/runs/run_001/{condition}/rubric/scores.md`
