import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analysis.rubric_reader import read_scores
from src.analysis.metrics_reader import (
    read_model_performance,
    read_memory_store,
    read_k_values,
    read_token_growth,
    read_k_activity,
    read_consolidation_activity,
    read_rule_detection,
    read_token_efficiency,
)
from src.analysis.criteria_evaluator import evaluate_criteria

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DIR = os.path.join(BASE, "experiments", "study_002", "runs", "run_001")
STUDY_DIR = os.path.join(BASE, "experiments", "study_002")

CONDITIONS = {
    "full_context": "Full Context",
    "compaction": "Compaction",
    "iterative": "Iterative",
}

WIDTH = 55


def print_header(text):
    print("=" * WIDTH)
    print(text)
    print("=" * WIDTH)


def print_section(title):
    print()
    print(title)
    print("-" * WIDTH)


def run_analysis():
    print_header("STUDY 002 ANALYSIS -- contextDecayWindow")
    print("Idris Applied AI Research")
    print("=" * WIDTH)

    # Load scores
    scores = {}
    for cond_key, cond_label in CONDITIONS.items():
        scores_path = os.path.join(RUN_DIR, cond_key, "rubric", "scores.md")
        scores[cond_key] = read_scores(scores_path)

    # Print rubric scores table
    print_section("RUBRIC SCORES")
    header = f"{'':22s} {'Full Context':>14s} {'Compaction':>14s} {'Iterative':>14s}"
    print(header)
    print(
        f"{'Cat 1 (early plant)':22s} "
        f"{scores['full_context']['cat_1']:>10.1f} / 3.0   "
        f"{scores['compaction']['cat_1']:>10.1f} / 3.0   "
        f"{scores['iterative']['cat_1']:>10.1f} / 3.0"
    )
    print(
        f"{'Cat 2 (middle plant) *':22s} "
        f"{scores['full_context']['cat_2']:>10.1f} / 3.0   "
        f"{scores['compaction']['cat_2']:>10.1f} / 3.0   "
        f"{scores['iterative']['cat_2']:>10.1f} / 3.0"
    )
    print(
        f"{'Cat 3 (late plant)':22s} "
        f"{scores['full_context']['cat_3']:>10.1f} / 2.0   "
        f"{scores['compaction']['cat_3']:>10.1f} / 2.0   "
        f"{scores['iterative']['cat_3']:>10.1f} / 2.0"
    )
    print(
        f"{'Cat 4 (bleed)':22s} "
        f"{scores['full_context']['cat_4']:>9.0f} / 3       "
        f"{scores['compaction']['cat_4']:>9.0f} / 3       "
        f"{scores['iterative']['cat_4']:>9.0f} / 3"
    )
    print(
        f"{'Cat 5 (rules)':22s} "
        f"{scores['full_context']['cat_5']:>9.0f} / 2       "
        f"{scores['compaction']['cat_5']:>9.0f} / 2       "
        f"{scores['iterative']['cat_5']:>9.0f} / 2"
    )
    print(
        f"{'Overall':22s} "
        f"{scores['full_context']['overall']:>9.1f} / 13.0  "
        f"{scores['compaction']['overall']:>9.1f} / 13.0  "
        f"{scores['iterative']['overall']:>9.1f} / 13.0"
    )
    print()
    print("* Primary test of Study 002")

    # Token efficiency
    iter_dir = os.path.join(RUN_DIR, "iterative")
    fc_dir = os.path.join(RUN_DIR, "full_context")
    token_eff = read_token_efficiency(iter_dir, fc_dir)

    # Evaluate criteria
    metrics = {"token_efficiency": token_eff}
    criteria = evaluate_criteria(scores, metrics)

    print_section("SUCCESS CRITERIA")

    b1 = criteria["bar_1"]
    print(f"Bar 1 -- Middle Plant (Cat2, C >= A):          {'PASS' if b1['passed'] else 'FAIL'}")
    print(
        f"  Condition C: {b1['condition_c_score']:.1f}  |  "
        f"Condition A: {b1['condition_a_score']:.1f}"
    )
    print()

    b2 = criteria["bar_2"]
    print(f"Bar 2 -- Token Efficiency (C < A every turn):  {'PASS' if b2['passed'] else 'FAIL'}")
    print(
        f"  Iterative peak: ~{b2['iterative_peak']:,}  |  "
        f"Full context peak: ~{b2['full_context_peak']:,}"
    )
    print(f"  Violations: {b2['violations']} turns")
    print()

    b3 = criteria["bar_3"]
    print(f"Bar 3 -- Rule Pinning (Cat5, C > Study001):    {'PASS' if b3['passed'] else 'FAIL'}")
    print(
        f"  Condition C: {b3['condition_c_score']:.0f}/2  |  "
        f"Study 001 baseline: {b3['study001_baseline']}/2"
    )
    print()

    b4 = criteria["bar_4"]
    print(f"Bar 4 -- Topic Bleed (Cat4, C >= A):           {'PASS' if b4['passed'] else 'FAIL'}")
    print(
        f"  Condition C: {b4['condition_c_score']:.0f}/3  |  "
        f"Condition A: {b4['condition_a_score']:.0f}/3"
    )
    print()

    print(f"OVERALL RESULT: {criteria['overall']}")

    # K Retrieval Activity
    print_section("K RETRIEVAL ACTIVITY (Condition C)")
    kact = read_k_activity(iter_dir)
    print(f"Total turns with K > 0:   {120 - kact['k_zero_turns']} / 120")
    print(f"Total K events:           {kact['k_events_total']}")
    print(f"K-only episodes total:    {kact['k_only_episodes_total']}")
    print(f"First K fire turn:        Turn {kact['first_k_fire_turn']}")
    print(f"K-zero turns:             {kact['k_zero_turns']}")
    print("(Study 001 comparison: K fired 1 time in 32 turns)")

    # Topic Consolidation
    print_section("TOPIC CONSOLIDATION (Condition C)")
    cons = read_consolidation_activity(iter_dir)
    print(f"Consolidation passes:     {cons['consolidation_passes']}")
    print(f"Total pairs merged:       {cons['total_pairs_merged']}")
    print(f"Topic count turn 10:      {cons['topics_at_turn_10']}")
    print(f"Topic count turn 60:      {cons['topics_at_turn_60']}")
    print(f"Topic count turn 120:     {cons['topics_at_turn_120']}")
    print(f"Final topic count:        {cons['final_topic_count']}")
    print(f"(Study 001 comparison: 30 topics / 30 episodes at end)")

    # Rule Detection
    print_section("RULE DETECTION")
    for cond_key, cond_label in CONDITIONS.items():
        rd = read_rule_detection(os.path.join(RUN_DIR, cond_key))
        print(f"{cond_label}: detections={rd['total_detections']}, "
              f"recall={rd['recall']:.2f}, "
              f"est. FP={rd['estimated_false_positives']}")
    print(f"Ground truth turns:       {rd['ground_truth_turns']}")

    # Token Growth
    print_section("TOKEN GROWTH")
    comp_dir = os.path.join(RUN_DIR, "compaction")
    for cond_key, cond_label in CONDITIONS.items():
        mp = read_model_performance(os.path.join(RUN_DIR, cond_key))
        print(
            f"{cond_label.capitalize()} peak:     ~{mp['peak_estimated_tokens']:,} tokens (turn {mp['peak_turn']})"
        )
    print(f"Cap saturation turn:      Turn {token_eff['cap_saturation_turn']} (N cap hit, K compensating)")

    # Write summary
    summary_lines = []
    summary_lines.append("STUDY 002 ANALYSIS SUMMARY")
    summary_lines.append("=" * WIDTH)
    summary_lines.append("")

    for cond_key, cond_label in CONDITIONS.items():
        s = scores[cond_key]
        summary_lines.append(f"{cond_label}:")
        summary_lines.append(f"  Cat 1 (early plant):  {s['cat_1']:.1f}/3.0")
        summary_lines.append(f"  Cat 2 (middle plant): {s['cat_2']:.1f}/3.0")
        summary_lines.append(f"  Cat 3 (late plant):   {s['cat_3']:.1f}/2.0")
        summary_lines.append(f"  Cat 4 (bleed):        {s['cat_4']:.0f}/3")
        summary_lines.append(f"  Cat 5 (rules):        {s['cat_5']:.0f}/2")
        summary_lines.append(f"  Overall:              {s['overall']:.1f}/13.0")
        summary_lines.append("")

    summary_lines.append("SUCCESS CRITERIA:")
    summary_lines.append(f"  Bar 1 (Middle Plant):     {'PASS' if b1['passed'] else 'FAIL'} (C: {b1['condition_c_score']:.1f}, A: {b1['condition_a_score']:.1f})")
    summary_lines.append(f"  Bar 2 (Token Efficiency): {'PASS' if b2['passed'] else 'FAIL'} (violations: {b2['violations']})")
    summary_lines.append(f"  Bar 3 (Rule Pinning):     {'PASS' if b3['passed'] else 'FAIL'} (C: {b3['condition_c_score']:.0f}/2, baseline: {b3['study001_baseline']}/2)")
    summary_lines.append(f"  Bar 4 (Topic Bleed):      {'PASS' if b4['passed'] else 'FAIL'} (C: {b4['condition_c_score']:.0f}/3, A: {b4['condition_a_score']:.0f}/3)")
    summary_lines.append(f"  Overall: {criteria['overall']}")
    summary_lines.append("")

    summary_lines.append("K RETRIEVAL (Condition C):")
    summary_lines.append(f"  Turns with K > 0: {120 - kact['k_zero_turns']}/120")
    summary_lines.append(f"  Total K events: {kact['k_events_total']}")
    summary_lines.append(f"  K-only episodes: {kact['k_only_episodes_total']}")
    summary_lines.append(f"  First K fire: Turn {kact['first_k_fire_turn']}")
    summary_lines.append("")

    summary_lines.append("TOPIC CONSOLIDATION (Condition C):")
    summary_lines.append(f"  Consolidation passes: {cons['consolidation_passes']}")
    summary_lines.append(f"  Pairs merged: {cons['total_pairs_merged']}")
    summary_lines.append(f"  Topics at turn 10: {cons['topics_at_turn_10']}")
    summary_lines.append(f"  Topics at turn 60: {cons['topics_at_turn_60']}")
    summary_lines.append(f"  Topics at turn 120: {cons['topics_at_turn_120']}")
    summary_lines.append(f"  Final topic count: {cons['final_topic_count']}")
    summary_lines.append("")

    summary_lines.append("RULE DETECTION:")
    for cond_key, cond_label in CONDITIONS.items():
        rd = read_rule_detection(os.path.join(RUN_DIR, cond_key))
        summary_lines.append(f"  {cond_label}: detections={rd['total_detections']}, recall={rd['recall']:.2f}, FP={rd['estimated_false_positives']}")
    summary_lines.append("")

    summary_lines.append("TOKEN GROWTH:")
    for cond_key, cond_label in CONDITIONS.items():
        mp = read_model_performance(os.path.join(RUN_DIR, cond_key))
        summary_lines.append(f"  {cond_label} peak: ~{mp['peak_estimated_tokens']:,} tokens (turn {mp['peak_turn']})")

    summary_path = os.path.join(STUDY_DIR, "analysis_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print_section("PROTOCOL NOTES")
    print("[See experiments/study_002/README.md for full protocol notes]")
    print("=" * WIDTH)
    print(f"\nSummary written to: {summary_path}")


if __name__ == "__main__":
    run_analysis()
