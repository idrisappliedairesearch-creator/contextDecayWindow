def evaluate_criteria(scores: dict, metrics: dict) -> dict:
    """
    Evaluates four pre-registered success criteria for Study 002.

    Bar 1: Cat 2 (middle plant) — Condition C >= Condition A
    Bar 2: Token efficiency — Condition C < Condition A at every turn
    Bar 3: Cat 5 (behavioral) — Condition C > Study 001 score (1/2)
    Bar 4: Topic bleed (Cat 4) — Condition C <= Condition A (C >= A numerically)
    """
    a = scores.get("full_context", {})
    c = scores.get("iterative", {})

    cat2_a = a.get("cat_2", 0)
    cat2_c = c.get("cat_2", 0)

    cat4_a = a.get("cat_4", 0)
    cat4_c = c.get("cat_4", 0)

    cat5_c = c.get("cat_5", 0)

    token_eff = metrics.get("token_efficiency", {})
    violations = token_eff.get("turns_where_iterative_exceeds", [])

    # Bar 1: Middle Plant Survival — C >= A on Cat 2
    bar1_passed = cat2_c >= cat2_a

    # Bar 2: Token Efficiency — zero violations
    bar2_passed = len(violations) == 0

    # Bar 3: Behavioral Consistency — C Cat 5 > Study 001 baseline (1/2)
    bar3_passed = cat5_c > 1

    # Bar 4: Topic Bleed — C <= A bleed rate (C >= A numerically)
    bar4_passed = cat4_c >= cat4_a

    passed_count = sum([bar1_passed, bar2_passed, bar3_passed, bar4_passed])
    if passed_count == 4:
        overall = "VALIDATED"
    elif passed_count == 3:
        overall = "PARTIAL"
    else:
        overall = "INVALIDATED"

    return {
        "bar_1": {
            "passed": bar1_passed,
            "condition_c_score": cat2_c,
            "condition_a_score": cat2_a,
            "difference": cat2_c - cat2_a,
            "description": "Middle Plant Survival (Cat 2, C >= A)",
        },
        "bar_2": {
            "passed": bar2_passed,
            "iterative_peak": token_eff.get("iterative_peak", 0),
            "full_context_peak": token_eff.get("full_context_peak", 0),
            "violations": len(violations),
            "description": "Token Efficiency (C < A every turn)",
        },
        "bar_3": {
            "passed": bar3_passed,
            "condition_c_score": cat5_c,
            "study001_baseline": 1,
            "description": "Rule Pinning (Cat 5, C > Study 001 baseline 1/2)",
        },
        "bar_4": {
            "passed": bar4_passed,
            "condition_c_score": cat4_c,
            "condition_a_score": cat4_a,
            "description": "Topic Bleed (Cat 4, C >= A)",
        },
        "overall": overall,
    }
