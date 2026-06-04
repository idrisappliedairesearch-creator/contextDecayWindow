def evaluate_criteria(scores: dict) -> dict:
    """
    Takes scores dict keyed by condition name (full_context, compaction, iterative).
    Evaluates three pre-registered success criteria.
    Returns structured evaluation with pass/fail for each bar and overall result.
    """
    a = scores.get("full_context", {})
    b = scores.get("compaction", {})
    c = scores.get("iterative", {})

    cat1_2_a = a.get("category_1_2_total", 0)
    cat1_2_b = b.get("category_1_2_total", 0)
    cat1_2_c = c.get("category_1_2_total", 0)

    cat3_a = a.get("category_3_total", 0)
    cat3_c = c.get("category_3_total", 0)

    cat4_b = b.get("category_4_total", 0)
    cat4_c = c.get("category_4_total", 0)

    # Bar 1: Condition C Cat1+2 >= 15pp above Condition B
    # Cat1+2 max is 5.0, so 15pp = 0.75 points on the 5.0 scale
    # Actually "15 percentage points" means on a 0-100% scale
    # Cat1+2 is out of 5.0, so percentage = score/5.0 * 100
    # 15pp = 0.15 * 5.0 = 0.75 points
    diff_cat1_2 = cat1_2_c - cat1_2_b
    bar1_threshold = 0.15 * 5.0
    bar1_passed = diff_cat1_2 >= bar1_threshold

    # Bar 2: Condition C topic bleed <= Condition A
    # Cat3 is scored as binary pass (1=good), so lower bleed = higher score
    # "equal or lower bleed rate" means C's Cat3 score >= A's Cat3 score
    bar2_passed = cat3_c >= cat3_a

    # Bar 3: Condition C Cat4 >= Condition B Cat4
    bar3_passed = cat4_c >= cat4_b

    passed_count = sum([bar1_passed, bar2_passed, bar3_passed])
    if passed_count == 3:
        overall = "VALIDATED"
    elif passed_count == 2:
        overall = "PARTIAL"
    else:
        overall = "INVALIDATED"

    return {
        "bar_1": {
            "passed": bar1_passed,
            "condition_c_score": cat1_2_c,
            "condition_b_score": cat1_2_b,
            "difference": diff_cat1_2,
            "threshold": bar1_threshold,
            "description": "Condition C Cat1+2 >= 15pp above Condition B",
        },
        "bar_2": {
            "passed": bar2_passed,
            "condition_c_bleed": cat3_c,
            "condition_a_bleed": cat3_a,
            "description": "Condition C topic bleed <= Condition A (Cat3 score C >= A)",
        },
        "bar_3": {
            "passed": bar3_passed,
            "condition_c_score": cat4_c,
            "condition_b_score": cat4_b,
            "description": "Condition C Cat4 >= Condition B Cat4",
        },
        "overall": overall,
    }
