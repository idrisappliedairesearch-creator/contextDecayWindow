import re


def read_scores(scores_path: str) -> dict:
    """
    Parses scores.md and returns structured scores:
    {
        "condition": str,
        "scores": {"Q1": float, ..., "Q10": float},
        "category_1_2_total": float,
        "category_3_total": float,
        "category_4_total": float,
        "overall": float,
        "notes": {"Q1": str, ..., "Q10": str},
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

    question_map = {
        "Q1": "Q1",
        "Q2": "Q2",
        "Q3": "Q3",
        "Q4": "Q4",
        "Q5": "Q5",
        "Q6": "Q6",
        "Q7": "Q7",
        "Q8": "Q8",
        "Q9": "Q9",
        "Q10": "Q10",
    }

    scores = {}
    notes = {}

    for line in table_lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        question = parts[1]
        score_str = parts[2]
        note = parts[3] if len(parts) > 3 else ""

        for qkey in question_map:
            if qkey in question:
                try:
                    scores[qkey] = float(score_str)
                except ValueError:
                    scores[qkey] = 0.0
                notes[qkey] = note.strip()
                break

    cat1_2_match = re.search(r"\*\*Category 1\+2 Total:\*\*\s*([\d.]+)\s*/\s*5\.0", content)
    cat3_match = re.search(r"\*\*Category 3 Total:\*\*\s*([\d.]+)\s*/\s*3", content)
    cat4_match = re.search(r"\*\*Category 4 Total:\*\*\s*([\d.]+)\s*/\s*2", content)
    overall_match = re.search(r"\*\*Overall:\*\*\s*([\d.]+)\s*/\s*10\.0", content)

    cat1_2 = float(cat1_2_match.group(1)) if cat1_2_match else sum(scores.get(f"Q{i}", 0) for i in range(1, 6))
    cat3 = float(cat3_match.group(1)) if cat3_match else sum(scores.get(f"Q{i}", 0) for i in range(6, 9))
    cat4 = float(cat4_match.group(1)) if cat4_match else sum(scores.get(f"Q{i}", 0) for i in range(9, 11))
    overall = float(overall_match.group(1)) if overall_match else cat1_2 + cat3 + cat4

    return {
        "condition": condition,
        "scores": scores,
        "notes": notes,
        "category_1_2_total": cat1_2,
        "category_3_total": cat3,
        "category_4_total": cat4,
        "overall": overall,
    }
