# Study 001 — Filled Rubric
**Locked:** Sprint 007
**Do not modify after Sprint 007 commit.**

---

## Planted Facts Reference

### Topic A — Meridian (turns 1–5, returns turn 20–24)
| Fact | Value | First planted |
|------|-------|---------------|
| Project name | Meridian | Turn 2 |
| Budget cap | $47,500 | Turn 2 |
| Deadline | October 14th | Turn 2 |
| Lead engineer | Dr. Priya Nair | Turn 2 |
| Performance target | 180ms (95th percentile) | Turn 3 |

### Topic B — CRISPR Study (turns 13–19)
| Fact | Value | First planted |
|------|-------|---------------|
| Researcher | Dr. Yuki Tanaka | Turn 13 |
| Cell line | HEK-293T | Turn 13 |
| Dosage | 2.5 mg/kg | Turn 13 |
| Expression rate | 73% | Turn 13 |

### Behavioral Rules (turns 1–2)
| Rule | Description |
|------|-------------|
| Rule 1 | Multiple items always formatted as numbered list |
| Rule 2 | Technical recommendations always end with (Confidence: High/Medium/Low) |

---

## Category 1 — Numerical Detail Fidelity

**Q1 (Turn 25):** What is the exact budget cap for the Meridian project?
- Expected answer: $47,500
- Scoring: 1.0 = "$47,500" | 0.5 = "approximately $47,000–$48,000" or "around $47k" | 0.0 = wrong value or absent

**Q2 (Turn 30):** What is the performance target for Meridian's API responses?
- Expected answer: Under 180 milliseconds at the 95th percentile
- Scoring: 1.0 = "180ms" with percentile reference | 0.5 = "180ms" without percentile | 0.0 = wrong or absent

**Q3 (Turn 29):** What was the exact dosage used in Dr. Yuki Tanaka's CRISPR experiment?
- Expected answer: 2.5 mg/kg
- Scoring: 1.0 = "2.5 mg/kg" | 0.5 = "approximately 2–3 mg/kg" | 0.0 = wrong or absent

---

## Category 2 — Named Entity Fidelity

**Q4 (Turn 26):** Who is the lead engineer on Meridian and what is the project deadline?
- Expected answer: Dr. Priya Nair, October 14th
- Scoring: 1.0 = both correct | 0.5 = one correct | 0.0 = both wrong or absent

**Q5 (Turn 28):** What cell line was used in the CRISPR study and what expression rate was achieved?
- Expected answer: HEK-293T, 73%
- Scoring: 1.0 = both correct | 0.5 = one correct | 0.0 = both wrong or absent

---

## Category 3 — Topic Bleed Detection

**Q6 (Turn 20 — mid-conversation probe):** After 8 turns of CRISPR discussion, "What was the exact response time target we locked in?"
- Expected answer: 180ms — Topic A fact retrieved cleanly with no CRISPR contamination
- Bleed indicators: mentioning Dr. Yuki Tanaka, HEK-293T, or any CRISPR content unprompted
- Scoring: 1 = 180ms retrieved cleanly | 0 = CRISPR content present in response

**Q7 (Turn 31 — researcher disambiguation):** "Which researcher conducted the CRISPR study?"
- Expected answer: Dr. Yuki Tanaka
- Bleed indicator: response confuses Dr. Yuki Tanaka (CRISPR) with Dr. Priya Nair (Meridian)
- Scoring: 1 = Dr. Yuki Tanaka named correctly | 0 = Dr. Priya Nair named or researchers conflated

**Q8 (Turn 32 — numerical enumeration across topics):** "List all specific numerical values covered in our entire conversation."
- Expected values: $47,500 | October 14th | 180ms | 95th percentile | 2.5 mg/kg | 73%
- Bleed scoring: each topic's values should be clearly separated or attributable
- Scoring: 1 = all 6 values present with correct attribution | 0 = values missing, wrong, or cross-attributed

---

## Category 4 — Behavioral Consistency

**Q9 (Turn 27 — rule recall):** "What are the two formatting rules I asked you to follow?"
- Expected answer: Numbered lists for multiple items + confidence levels on technical recommendations
- Scoring: 1 = both rules stated correctly | 0 = one or both rules missing or wrong

**Q10 (Ongoing — rule compliance):** Are numbered lists and confidence levels still present in responses at turns 25–32?
- Assessed by reviewing the last 8 turns of assistant output, not by asking the model
- Scoring: 1 = both formatting conventions present in ≥ 6 of 8 late turns | 0 = conventions absent or inconsistent

---

## Scoring Sheet

To be completed during Sprint 009 (Analysis + Writeup). One sheet per condition.

| Question | Condition A | Condition B | Condition C |
|----------|-------------|-------------|-------------|
| Q1 | | | |
| Q2 | | | |
| Q3 | | | |
| Q4 | | | |
| Q5 | | | |
| Q6 | | | |
| Q7 | | | |
| Q8 | | | |
| Q9 | | | |
| Q10 | | | |
| **Cat 1+2 Total** | /5.0 | /5.0 | /5.0 |
| **Cat 3 Total** | /3 | /3 | /3 |
| **Cat 4 Total** | /2 | /2 | /2 |
| **Overall** | /10.0 | /10.0 | /10.0 |

---

*Do not modify this document after Sprint 007 commit.*
*Scoring sheet completed in Sprint 009.*
