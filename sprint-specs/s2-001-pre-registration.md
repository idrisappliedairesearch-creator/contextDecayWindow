# CDW Sprint S2_001 — Study 002 Pre-Registration

**Project:** contextDecayWindow
**Organization:** Idris Applied AI Research
**Status:** Complete
**Date:** 2026-06-06

---

## Objective

Commit the Study 002 pre-registration document before any architecture changes or implementation begins. The commit SHA is the tamper-evident timestamp proving the study design was locked prior to execution.

No code is written in this sprint.

---

## Context

Study 001 returned VALIDATED on all three success bars but produced two unexpected findings that motivate Study 002:

1. **K retrieval fired once in 32 turns.** The architecture succeeded primarily through decay-based recency (N retrieval), not embedding similarity. The 0.70 threshold was too strict for the embedding model's space.

2. **Iterative context exceeded full context** (24,854 vs 13,231 tokens). Uncapped N retrieval caused the system to converge toward full context loading. The pre-registered failure condition was triggered.

Study 002 directly addresses both findings through architectural changes and stresses the system with a significantly longer conversation designed to force lost-in-the-middle failure in the full context condition.

---

## Deliverables

1. `experiments/study_002/pre_registration.md` — see companion file `S2_001_pre_registration.md`
2. `experiments/study_002/` directory created in repo

---

## Tasks

| ID | Description |
|----|-------------|
| S2-T-001 | Create `experiments/study_002/` directory |
| S2-T-002 | Write `experiments/study_002/pre_registration.md` |
| S2-T-003 | Commit pre_registration.md — record SHA in document |
| S2-T-004 | Confirm SHA recorded before S2_002 begins |

---

## Acceptance Criteria

- [ ] `experiments/study_002/pre_registration.md` committed to repo
- [ ] Commit SHA filled into the SHA Record section
- [ ] No implementation code exists at time of commit
- [ ] S2_002 does not begin until SHA is recorded

---

## What This Sprint Is Not

No code. No architecture changes. No script writing. Any of those actions before the SHA is recorded invalidates the pre-registration.