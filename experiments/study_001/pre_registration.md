# Study 001 Pre-Registration — contextDecayWindow

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** Pre-Registered
**Pre-Registration Date:** 2026-05-31
**Commit SHA:** 7b03ba4

---

## Research Question

Can an iteratively constructed context window, built from embedding-based retrieval over a hierarchical episodic memory store, maintain conversational coherence across a long session — specifically under abrupt topic switching and extended conversation duration — compared to full context loading and summarization compaction?

---

## Motivation

Current approaches to LLM conversational memory exist on a lossy spectrum. Full context loading is O(N) in token cost and suffers from lost-in-the-middle attention degradation — a property that is architecturally real on the Qwen3.6 27B dense model used in this study, which uses full quadratic attention (GQA) where every token attends to every other token. Summarization compaction compresses rich context into lossy representations — specific facts, behavioral rules, and precise numerical details that do not survive the summary cut are permanently unrecoverable.

This study investigates a third approach: iterative context construction via embedding retrieval over a hierarchically organized episodic memory store, where relevance — not recency or compression — determines what enters the active context window at each turn.

---

## Conditions

Three conditions are tested against an identical scripted conversation and evaluated against an identical pre-written rubric.

**Condition A — Full Context Loading (ceiling)**

The complete conversation history is appended to every prompt in full. No compression, no retrieval. Represents the theoretical performance ceiling. Token usage grows O(N).

**Condition B — Summarization Compaction (current best practice)**

Conversation history is periodically summarized by the model when a token threshold is approached. The summary replaces the raw history. Prior turns are discarded. Represents the current industry standard for long-session memory management.

**Condition C — Iterative Construction (contextDecayWindow)**

At each turn, the active context window is constructed dynamically from a SQLite episodic memory store. Episodes are retrieved by two mechanisms:

- K retrieval: all episodes with cosine similarity ≥ 0.70 to the current query embedding
- N retrieval: all episodes in the store, sorted by decay score computed fresh from `last_retrieved_at` timestamp, descending

Retrieved episodes are assembled in chronological order. The full conversation history is never loaded. The context window grows sub-linearly by design.

---

## Hypotheses

**H1 — Full Context Loading**

Detail fidelity will be highest across all turns since no information is discarded. Measurable degradation will occur for facts positioned in the middle of long windows due to lost-in-the-middle attention dilution on the dense quadratic attention architecture. Token usage grows O(N). Topic bleed will be present but moderate — all context is available but attention dilutes across it. This condition establishes the performance ceiling.

**H2 — Summarization Compaction**

Detail fidelity will degrade sharply following each compaction event. Specific numerical facts, named entities, and early-established behavioral rules are most vulnerable — they are precise artifacts that resist lossy compression. Topic bleed will be lower than expected because summaries flatten topic boundaries into prose, reducing signal interference. Behavioral consistency will be the most damaged condition — instructions and rules established early are unlikely to survive summarization intact.

**H3 — Iterative Construction (contextDecayWindow)**

Detail fidelity will exceed Condition B for high-salience facts because embedding retrieval surfaces them on demand rather than compressing them away. Topic bleed will be the lowest of the three conditions because irrelevant topic episodes do not clear the 0.70 retrieval threshold and are not constructed into the active window. Context window token usage will grow sub-linearly compared to Condition A. Behavioral consistency will exceed Condition B because rules retrieved arrive verbatim rather than summarized. Primary risk: retrieval misses — facts that exist in the store but whose embeddings do not surface above threshold for a given query.

---

## Model

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B Q6_K |
| Runtime | llama.cpp / Ollama |
| Hardware | RTX 5090 32GB VRAM (GPU) |
| Context cap | 147,000 tokens — applied consistently across all three conditions |
| Embedding model | Qwen3-Embedding-0.6B |
| Embedding runtime | CPU (64GB system RAM) |
| Embedding dimensions | 1024 |

The model is the control variable. Same instance, same quantization, same context cap across all conditions. The independent variable is the memory architecture condition.

---

## Architecture Specification (Condition C)

### Episode Layer

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| topic_id | UUID | FK → topics.id |
| user_message | TEXT | |
| assistant_message | TEXT | |
| embedding | VECTOR(1024) | Qwen3-Embedding-0.6B |
| turn_number | INTEGER | |
| created_at | TIMESTAMP | |
| last_retrieved_at | TIMESTAMP | Reset on every retrieval |
| retrieval_count | INTEGER | Default 0 |

Unit of storage is the response pair (user message + assistant message together). Embedding computed programmatically. Storage occurs after generation, before response is returned to the user.

### Topic Layer

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| label | TEXT | Derived from first episode assigned |
| centroid | VECTOR(1024) | Running average of assigned episode embeddings |
| episode_count | INTEGER | Default 0 |
| created_at | TIMESTAMP | |
| last_updated_at | TIMESTAMP | |

Assignment rule: cosine similarity ≥ 0.70 to nearest topic centroid → assign to that topic. Below threshold → create new topic node. Topic nodes are unbounded in Study 001. A live in-memory topic index is maintained for fast assignment at storage time.

### Retrieval Events Log

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| turn_number | INTEGER | |
| episode_id | UUID | FK → episodes.id |
| similarity_score | FLOAT | |
| decay_score | FLOAT | Computed fresh at retrieval time |
| retrieval_type | TEXT | "K" or "N" |
| retrieved_at | TIMESTAMP | |

### Retrieval Mechanism

K retrieval: all episodes with cosine similarity ≥ 0.70 to the current query embedding. No top-K cap in Study 001 — all qualifying episodes are included.

N retrieval: all episodes in the store, sorted by decay score descending. Decay score computed fresh at retrieval time from `last_retrieved_at`. Decay function: exponential decay over time since last retrieval. `last_retrieved_at` is updated for every episode included in a retrieval event.

Assembly: retrieved episodes ordered chronologically by `turn_number`, not by similarity score. Chronological ordering preserves narrative coherence for the model.

### Database

SQLite + sqlite-vec. Single file, local, no external dependencies. Vector dimension: 1024.

---

## Test Script Requirements

The test script will be written in Sprint 007, after the architecture is implemented and the observability layer is in place. The script must satisfy all of the following constraints before it is considered valid:

1. Minimum 30 turns in length
2. Contains at least two clean, abrupt topic switches — topics must be semantically unrelated
3. Plants a minimum of five specific verifiable facts early in the conversation (numerical values, named entities, explicit decisions)
4. Contains a late-session return to early-planted facts (minimum turn 25+)
5. Establishes at minimum two behavioral rules or constraints in the first five turns
6. Is fully scripted and reproducible — no generative variance

The script is written against the rubric. The rubric is not written against the script.

---

## Evaluation Rubric

Rubric categories, scoring criteria, and question count are locked here and are immutable from this point forward. Specific planted facts will be substituted in when the script is written in Sprint 007.

### Category 1 — Numerical Detail Fidelity

Tests whether specific numerical facts planted early survive to late turns. (3 questions)

- Q1: What specific [number / price / date / quantity] was established in the opening of the conversation?
- Q2: What were the exact parameters of the [decision / constraint] agreed upon early?
- Q3: What was the specific [measurement / threshold / target] mentioned before the first topic switch?

Scoring: 1.0 = exact recall | 0.5 = approximate recall within reasonable range | 0.0 = wrong or absent

### Category 2 — Named Entity Fidelity

Tests whether specific names and roles planted early survive to late turns. (2 questions)

- Q4: Who was identified as [role] and what were their specific responsibilities?
- Q5: What was the name of [project / place / system] established early and what distinguished it?

Scoring: 1.0 = exact | 0.5 = partial | 0.0 = wrong or absent

### Category 3 — Topic Bleed Detection

Tests whether the model contaminates responses with irrelevant topic context after a clean topic switch. (3 questions)

- Q6: After switching to Topic B, ask a question answerable only from Topic A context — does the model answer cleanly from the correct topic?
- Q7: Introduce a fact in Topic B superficially similar to a Topic A fact — does the model conflate them?
- Q8: After extended Topic B discussion, ask the model to recall a specific Topic A detail — does it retrieve cleanly without Topic B contamination?

Scoring: binary — 1 = no bleed detected | 0 = contamination present

### Category 4 — Behavioral Consistency

Tests whether rules and constraints established early persist across topic switches and extended conversation. (2 questions)

- Q9: A formatting or response style rule established in turns 1–3 — is it still being followed at turn 25+?
- Q10: A constraint or boundary established early — does the model still apply it correctly after topic switches?

Scoring: binary — 1 = rule honored | 0 = rule violated or forgotten

---

## Success Criteria

All three bars must be met for Study 001 to validate the architecture. Meeting two of three is a partial result requiring documented analysis before Study 002 proceeds. Meeting zero or one invalidates the architecture at current threshold settings and triggers a redesign review.

**Bar 1 — Detail Fidelity**

Condition C scores ≥ 15 percentage points higher than Condition B on Categories 1 and 2 combined.

**Bar 2 — Topic Bleed**

Condition C shows equal or lower bleed rate than Condition A on Category 3. Condition C does not need to beat the ceiling — it must not be worse than it.

**Bar 3 — Behavioral Consistency**

Condition C scores equal or higher than Condition B on Category 4.

---

## Failure Conditions

The following outcomes invalidate the architecture and require redesign before Study 002 proceeds. These conditions are pre-registered and are not post-hoc determinations.

- Retrieval miss rate above 30% on Categories 1 and 2 — indicates similarity threshold or embedding model requires adjustment
- Topic bleed rate higher than Condition A — indicates topic layer assignment is failing
- Condition C context window token count exceeds Condition A at any turn — indicates a context construction logic error

---

## Out of Scope — Study 001

The following are explicitly deferred. They must not be introduced during implementation or analysis of Study 001.

- GABA-inspired inhibitory gating mechanism
- Consolidation pipeline (episode compression into topic summaries)
- Top-K retrieval tuning (K is threshold-based in Study 001, not count-based)
- Decay as a gating signal (decay is a sort signal only in Study 001)
- Embedding model quality comparison
- Multi-model comparison

---

## Observability Requirements

### Terminal Output

Every turn produces a visible structured block in the terminal:

```
═══════════════════════════════════════════════════════
TURN 04 | Topics: 3 | Episodes: 7 | Tokens: 4,832
═══════════════════════════════════════════════════════
[USER] ...
[RETRIEVAL] K=3 above 0.70 | N=7 total episodes
  → ep_002 | sim: 0.84 | decay: 0.92 | topic: topic_1
  → ep_005 | sim: 0.79 | decay: 0.88 | topic: topic_1
  → ep_001 | sim: 0.71 | decay: 0.61 | topic: topic_2
[TOPIC LAYER] No new nodes | Centroid drift: topic_1=0.02
[CONTEXT BUILT] 2,847 tokens | K: 1,203 | N: 1,644
[GENERATION] 47 tok/s | TTFT: 0.3s | Output tokens: 312
[STORAGE] ep_008 stored | Topic: topic_1 | Embedding: done
[DECAY UPDATED] 7 episodes updated
───────────────────────────────────────────────────────
[ASSISTANT] ...
═══════════════════════════════════════════════════════
```

### File Output

Per run, per condition:

```
experiments/study_001/runs/
  run_001_full_context/
  run_001_compaction/
  run_001_iterative/
    logs/
      turns.jsonl
      retrieval.jsonl
      context_windows.jsonl
      context_diffs.jsonl
    metrics/
      model_performance.csv
      memory_store.csv
      K_values.csv
      N_values.csv
      topic_events.csv
      retrieval_events.csv
    snapshots/
      turn_001_db_state.json
      turn_002_db_state.json
    rubric/
      responses.md
      scores.md
    constructed_prompts/
      turn_001.txt
      turn_002.txt
```

---

## Sprint Sequence

| Sprint | Title | Scope |
|--------|-------|-------|
| 001 | Pre-Registration | This document. No code. |
| 002 | Database + Embedding Layer | SQLite schema, sqlite-vec, Qwen3-Embedding-0.6B CPU inference, episode storage and retrieval |
| 003 | Topic Layer | Centroid management, similarity assignment, node creation, live in-memory index |
| 004 | Retrieval + Context Construction | K retrieval, N decay sort, context assembly, chronological ordering |
| 005 | Observability Layer | Terminal output, metric files, DB snapshots, run folder structure |
| 006 | Baseline Conditions | Full context loader and summarization compaction — both runnable against the same script |
| 007 | Test Script + Rubric | Rubric specifics written first, then script. Rich detail, two topic switches, late return. |
| 008 | Study Run | Execute all three conditions. No intervention. |
| 009 | Analysis + Writeup | Score rubric, analyze metrics, write `experiments/study_001/README.md` |

---

## SHA Record

**Pre-registration commit SHA:** 7b03ba4
**Committed by:** Muzaffer Ozen
**Date:** 2026-05-31

This SHA is the study's tamper-evident timestamp. It must be recorded before any implementation code is written.

---

*Idris Applied AI Research — Study 001*
*contextDecayWindow*
*Do not modify this document after the SHA is recorded.*