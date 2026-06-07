# Study 002 — Filled Rubric
**Locked:** Sprint S2_007
**Do not modify after S2_007 commit.**

---

## Planted Facts Reference

### Early Position — Topic A: Halcyon Crossing (turns 3–5)
| Fact | Value | Turn planted |
|------|-------|-------------|
| Project name | Halcyon Crossing | Turn 3 |
| Span length | 847 meters | Turn 3 |
| Lead engineer | Dr. Anara Bekova | Turn 3 |
| Steel grade | S460ML | Turn 4 |
| Max load rating | 92.4 metric tons per axle | Turn 4 |

### Middle Position — Topic B: The Annunciation of Forlì (turns 55–60)
| Fact | Value | Turn planted |
|------|-------|-------------|
| Artwork title | The Annunciation of Forlì | Turn 55 |
| Artist | Melozzo da Forlì | Turn 55 |
| Patron | Cardinal Giuliano della Rovere | Turn 55 |
| Completion year | 1483 | Turn 55 |
| Pigment technique | Lead white ground with ultramarine glaze | Turn 56 |

### Late Position — Topic D: Vampyroteuthis infernalis (turns 100–110)
| Fact | Value | Turn planted |
|------|-------|-------------|
| Species | Vampyroteuthis infernalis | Turn 100 |
| Researcher | Dr. Kenji Watanabe | Turn 100 |
| Depth range | 600–900 meters | Turn 100 |
| Bioluminescence organ | Photophores along mantle margin | Turn 101 |
| Feeding behavior | Marine snow particle aggregation | Turn 102 |

### Behavioral Rules (turns 1–2)
| Rule | Description |
|------|-------------|
| Rule 1 | Technical specifications listed as numbered list |
| Rule 2 | Engineering recommendations conclude with (Risk: Low/Medium/High) |

---

## Category 1 — Early Plant Survival (Q1–Q3, turns 112–113)

**Q1 (Turn 112):** What is the exact main span length of Halcyon Crossing and its steel grade?
- Expected: 847 meters, S460ML
- Scoring: 1.0 = both correct | 0.5 = one correct | 0.0 = both wrong or absent

**Q2 (Turn 113):** Who is the lead engineer and what is the maximum load rating?
- Expected: Dr. Anara Bekova, 92.4 metric tons per axle
- Scoring: 1.0 = both correct | 0.5 = one correct | 0.0 = both wrong or absent

**Q3 (Turn 114):** State both formatting rules precisely.
- Expected: Numbered lists for technical specifications + Risk classification on engineering recommendations
- Scoring: 1.0 = both correct | 0.5 = one correct | 0.0 = both wrong or absent

---

## Category 2 — Middle Plant Survival (Q4–Q6, turns 115–117)

**Primary test of Study 002. Full context expected to fail here.**

**Q4 (Turn 115):** Name the painting, its artist, patron, and completion year.
- Expected: The Annunciation of Forlì, Melozzo da Forlì, Cardinal Giuliano della Rovere, 1483
- Scoring: 1.0 = all four correct | 0.5 = two or three correct | 0.0 = one or zero correct

**Q5 (Turn 116):** Name the specific pigment technique — ground and glaze.
- Expected: Lead white ground, ultramarine glaze
- Scoring: 1.0 = both correct | 0.5 = one correct | 0.0 = both wrong or absent

**Q6 (Turn 117):** After monetary policy and marine biology discussion, identify Cardinal Giuliano della Rovere's role and why his identity is significant.
- Expected: Patron of The Annunciation of Forlì, later became Pope Julius II
- Bleed indicator: monetary policy content (Taylor Rule, inflation) or marine biology content in response
- Scoring: 1 = clean retrieval of Renaissance content | 0 = cross-topic contamination or fact absent

---

## Category 3 — Late Plant Survival (Q7–Q8, turns 118–119)

**Q7 (Turn 118):** Name the organism, researcher, depth range, and feeding behavior.
- Expected: Vampyroteuthis infernalis, Dr. Kenji Watanabe, 600–900 meters, marine snow particle aggregation
- Scoring: 1.0 = all four correct | 0.5 = two or three correct | 0.0 = one or zero correct

**Q8 (Turn 119):** Name the bioluminescent organ and its location.
- Expected: Photophores along mantle margin
- Scoring: 1.0 = both organ type and location correct | 0.5 = one correct | 0.0 = wrong or absent

---

## Category 4 — Topic Bleed Detection (Q9–Q11)

**Q9 (Turn 117 — cross-topic probe):** Asked about Cardinal Giuliano della Rovere after extensive monetary policy and marine biology discussion.
- Bleed indicators: Taylor Rule, Dr. Priya Mehta, inflation threshold, Vampyroteuthis, Dr. Kenji Watanabe
- Scoring: 1 = clean Renaissance retrieval | 0 = contamination from Topics C or D

**Q10 (Turn 118 — researcher disambiguation):** Three named researchers in the study: Dr. Anara Bekova (engineering), Dr. Priya Mehta (economics), Dr. Kenji Watanabe (marine biology).
- Expected: Dr. Kenji Watanabe correctly identified with Vampyroteuthis
- Bleed indicator: confusion between researchers or incorrect attribution
- Scoring: 1 = correct attribution | 0 = researchers conflated

**Q11 (Turn 120 — full enumeration):** List all numerical values, named entities, and technical specifications across all four topics.
- Expected values: 847m | S460ML | 92.4 MT/axle | 1483 | 600–900m | 2.3% | 2%
- Expected entities: Halcyon Crossing | Dr. Anara Bekova | The Annunciation of Forlì | Melozzo da Forlì | Cardinal Giuliano della Rovere | Federal Reserve | Taylor Rule | Dr. Priya Mehta | Vampyroteuthis infernalis | Dr. Kenji Watanabe
- Scoring: 1 = ≥ 80% of values and entities present with correct attribution | 0 = < 80% or significant cross-attribution

---

## Category 5 — Behavioral Consistency / Rule Pinning (Q12–Q13)

**Q12 (Turn 114 — rule recall):** State both rules precisely.
- Expected: Numbered list rule + Risk classification rule
- Scoring: 1 = both stated correctly | 0 = one or both missing or wrong

**Q13 (Ongoing — rule compliance, turns 112–120):** Are both rules applied in late-turn responses?
- Rule 1 compliance: numbered lists present when specifications are listed
- Rule 2 compliance: (Risk: X) present when engineering recommendations are made
- Note: Turn 112–120 are probe turns, not engineering advice turns. Rule 2 may not be testable if no engineering recommendations are requested. If no opportunity arises, score Rule 2 as N/A and apply Rule 1 only.
- Scoring: 1 = applicable rules honored in ≥ 5 of 9 late turns | 0 = rules absent or inconsistent

---

## Scoring Sheet

To be completed in Sprint S2_009. One sheet per condition.

| Question | Full Context | Compaction | Iterative |
|----------|-------------|------------|-----------|
| Q1 (early numerical) | | | |
| Q2 (early entity) | | | |
| Q3 (early rule recall) | | | |
| Q4 (middle multi-fact) | | | |
| Q5 (middle technique) | | | |
| Q6 (middle bleed probe) | | | |
| Q7 (late multi-fact) | | | |
| Q8 (late bioluminescence) | | | |
| Q9 (topic bleed A→C/D) | | | |
| Q10 (researcher disambiguation) | | | |
| Q11 (full enumeration) | | | |
| Q12 (rule recall) | | | |
| Q13 (rule compliance) | | | |
| **Cat 1 Total** | /3.0 | /3.0 | /3.0 |
| **Cat 2 Total** | /3.0 | /3.0 | /3.0 |
| **Cat 3 Total** | /2.0 | /2.0 | /2.0 |
| **Cat 4 Total** | /3 | /3 | /3 |
| **Cat 5 Total** | /2 | /2 | /2 |
| **Overall** | /13.0 | /13.0 | /13.0 |

---

*Do not modify this document after S2_007 commit.*
*Scoring sheet completed in Sprint S2_009.*