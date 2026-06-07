# Context Decay Window

Research project by Idris Applied AI Research investigating whether iteratively constructed context windows, built from embedding-based retrieval over a hierarchical episodic memory store, can maintain conversational coherence across long sessions compared to full context loading and summarization compaction.

## Research Question

Can a retrieval-based context window — where relevance, not recency or compression, determines what enters the active context at each turn — outperform existing approaches on detail fidelity, topic bleed, and behavioral consistency over extended conversations?

## Conditions Under Test

- **Condition A — Full Context Loading:** Complete history appended every turn. Theoretical ceiling, O(N) token growth, lost-in-the-middle attention degradation.
- **Condition B — Summarization Compaction:** History periodically summarized by the model. Industry standard, but lossy — precise facts and rules don't survive compression.
- **Condition C — Iterative Construction (contextDecayWindow):** Active context built dynamically from a SQLite episodic memory store via embedding similarity (K retrieval) and time-based decay (N retrieval). Sub-linear token growth by design.

## What We're Studying

- **Detail Fidelity:** Do specific numerical facts and named entities survive to late turns?
- **Topic Bleed:** After abrupt topic switches, does irrelevant context contaminate responses?
- **Behavioral Consistency:** Do early-established rules and constraints persist across long sessions?

## Architecture (Condition C)

- **Episode Layer:** Stores user-assistant response pairs with embeddings (Qwen3-Embedding-0.6B, 1024-dim)
- **Topic Layer:** Hierarchical topic nodes with running centroid embeddings, auto-assigned by cosine similarity
- **Retrieval:** Dual mechanism — similarity threshold (K) + decay score (N) — assembled chronologically
- **Database:** SQLite + sqlite-vec, local, single file

## Model

| Parameter | Value |
|-----------|-------|
| Inference | Qwen3.6 27B Q6_K via llama.cpp / Ollama |
| Embedding | Qwen3-Embedding-0.6B, 1024-dim |
| Context cap | 147,000 tokens |
| Hardware | RTX 5090 32GB VRAM |

## Studies

See `experiments/` for pre-registrations, run data, rubrics, and analysis reports. Each study includes a tamper-evident SHA timestamp.
