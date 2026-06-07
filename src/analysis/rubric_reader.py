import re


CATEGORY_MAP = {
    "cat_1": ["Q1", "Q2", "Q3"],
    "cat_2": ["Q4", "Q5", "Q6"],
    "cat_3": ["Q7", "Q8"],
    "cat_4": ["Q9", "Q10", "Q11"],
    "cat_5": ["Q12", "Q13"],
}


def read_scores(scores_path: str) -> dict:
    """
    Parses scores.md and returns structured scores:
    {
        "condition": str,
        "scores": {"Q1": float, ..., "Q13": float},
        "cat_1": float,  -- out of 3.0
        "cat_2": float,  -- out of 3.0
        "cat_3": float,  -- out of 2.0
        "cat_4": int,    -- out of 3
        "cat_5": int,    -- out of 2
        "overall": float, -- out of 13.0
        "notes": {"Q1": str, ..., "Q13": str},
    }
    """
    with open(scores_path, encoding="utf-8") as f:
        content = f.read()

    condition_match = re.search(r"# Rubric Scores \u2014 (.+)", content)
    condition = condition_match.group(1).strip() if condition_match else "unknown"

    table_match = re.search(r"\| Question \| Score \| Notes \|(.+?)(?=\n\n|\*\*Category)", content, re.DOTALL)
    if not table_match:
        raise ValueError(f"No score table found in {scores_path}")

    table_lines = table_match.group(1).strip().split("\n")

    all_questions = [f"Q{i}" for i in range(1, 14)]

    scores = {}
    notes = {}

    for line in table_lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        question = parts[1]
        score_str = parts[2]
        note = parts[3] if len(parts) > 3 else ""

        for qkey in all_questions:
            if qkey in question:
                try:
                    scores[qkey] = float(score_str)
                except ValueError:
                    scores[qkey] = 0.0
                notes[qkey] = note.strip()
                break

    cat_matches = {}
    for cat_label, pattern in [
        ("cat_1", r"\*\*Category 1 Total.*?\*\*\s*([\d.]+)\s*/\s*3\.0"),
        ("cat_2", r"\*\*Category 2 Total.*?\*\*\s*([\d.]+)\s*/\s*3\.0"),
        ("cat_3", r"\*\*Category 3 Total.*?\*\*\s*([\d.]+)\s*/\s*2\.0"),
        ("cat_4", r"\*\*Category 4 Total.*?\*\*\s*([\d])\s*/\s*3"),
        ("cat_5", r"\*\*Category 5 Total.*?\*\*\s*([\d])\s*/\s*2"),
        ("overall", r"\*\*Overall:\*\*\s*([\d.]+)\s*/\s*13\.0"),
    ]:
        m = re.search(pattern, content)
        if m:
            val = m.group(1)
            cat_matches[cat_label] = int(val) if cat_label in ("cat_4", "cat_5") else float(val)

    cat1 = cat_matches.get("cat_1", sum(scores.get(q, 0) for q in CATEGORY_MAP["cat_1"]))
    cat2 = cat_matches.get("cat_2", sum(scores.get(q, 0) for q in CATEGORY_MAP["cat_2"]))
    cat3 = cat_matches.get("cat_3", sum(scores.get(q, 0) for q in CATEGORY_MAP["cat_3"]))
    cat4 = cat_matches.get("cat_4", sum(scores.get(q, 0) for q in CATEGORY_MAP["cat_4"]))
    cat5 = cat_matches.get("cat_5", sum(scores.get(q, 0) for q in CATEGORY_MAP["cat_5"]))
    overall = cat_matches.get("overall", cat1 + cat2 + cat3 + cat4 + cat5)

    return {
        "condition": condition,
        "scores": scores,
        "notes": notes,
        "cat_1": cat1,
        "cat_2": cat2,
        "cat_3": cat3,
        "cat_4": cat4,
        "cat_5": cat5,
        "overall": overall,
    }
