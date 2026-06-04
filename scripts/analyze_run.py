import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analysis.rubric_reader import read_scores
from src.analysis.metrics_reader import (
    read_model_performance,
    read_memory_store,
    read_k_values,
    read_token_growth,
)
from src.analysis.criteria_evaluator import evaluate_criteria

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DIR = os.path.join(BASE, "experiments", "study_001", "runs", "run_001")
STUDY_DIR = os.path.join(BASE, "experiments", "study_001")

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
    print_header("STUDY 001 ANALYSIS -- contextDecayWindow")
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
        f"{'Category 1+2 (det)':22s} "
        f"{scores['full_context']['category_1_2_total']:>10.1f} / 5.0   "
        f"{scores['compaction']['category_1_2_total']:>10.1f} / 5.0   "
        f"{scores['iterative']['category_1_2_total']:>10.1f} / 5.0"
    )
    print(
        f"{'Category 3 (bleed)':22s} "
        f"{scores['full_context']['category_3_total']:>9.0f} / 3       "
        f"{scores['compaction']['category_3_total']:>9.0f} / 3       "
        f"{scores['iterative']['category_3_total']:>9.0f} / 3"
    )
    print(
        f"{'Category 4 (behav)':22s} "
        f"{scores['full_context']['category_4_total']:>9.0f} / 2       "
        f"{scores['compaction']['category_4_total']:>9.0f} / 2       "
        f"{scores['iterative']['category_4_total']:>9.0f} / 2"
    )
    print(
        f"{'Overall':22s} "
        f"{scores['full_context']['overall']:>9.1f} / 10.0  "
        f"{scores['compaction']['overall']:>9.1f} / 10.0  "
        f"{scores['iterative']['overall']:>9.1f} / 10.0"
    )

    # Evaluate criteria
    criteria = evaluate_criteria(scores)

    print_section("SUCCESS CRITERIA")

    b1 = criteria["bar_1"]
    print(f"Bar 1 -- Detail Fidelity (Cat1+2, C vs B, >=15pp):  {'PASS' if b1['passed'] else 'FAIL'}")
    print(
        f"  Condition C: {b1['condition_c_score']:.1f}  |  "
        f"Condition B: {b1['condition_b_score']:.1f}  |  "
        f"delta: {b1['difference']:.2f}pp (threshold: {b1['threshold']:.2f})"
    )
    print()

    b2 = criteria["bar_2"]
    print(f"Bar 2 -- Topic Bleed (Cat3, C <= A):                {'PASS' if b2['passed'] else 'FAIL'}")
    print(f"  Condition C: {b2['condition_c_bleed']:.0f}/3  |  Condition A: {b2['condition_a_bleed']:.0f}/3")
    print()

    b3 = criteria["bar_3"]
    print(f"Bar 3 -- Behavioral Consistency (Cat4, C >= B):     {'PASS' if b3['passed'] else 'FAIL'}")
    print(f"  Condition C: {b3['condition_c_score']:.0f}/2  |  Condition B: {b3['condition_b_score']:.0f}/2")
    print()

    print(f"OVERALL RESULT: {criteria['overall']}")

    # Token growth
    print_section("TOKEN GROWTH")

    for cond_key, cond_label in CONDITIONS.items():
        mp = read_model_performance(os.path.join(RUN_DIR, cond_key))
        ms = read_memory_store(os.path.join(RUN_DIR, cond_key))
        compaction_info = ""
        if ms["compaction_events"]:
            compaction_info = f" ({len(ms['compaction_events'])} compaction events)"
        print(
            f"{cond_label.capitalize()} peak:     ~{mp['peak_estimated_tokens']:,} tokens (turn {mp['peak_turn']}{compaction_info})"
        )

    # Condition C retrieval summary
    print_section("CONDITION C -- RETRIEVAL SUMMARY")

    kvals = read_k_values(os.path.join(RUN_DIR, "iterative"))
    memstore = read_memory_store(os.path.join(RUN_DIR, "iterative"))
    print(f"Avg K per turn:      {kvals['avg_k_per_turn']} episodes")
    print(f"Max K per turn:      {kvals['max_k_per_turn']} episodes")
    print(f"Total retrieval events: {kvals['total_retrieval_events']}")
    print(f"Final topic count:   {memstore['final_topic_count']}")
    print(f"Final episode count: {memstore['final_episode_count']}")

    # Write summary
    summary_lines = []
    summary_lines.append("STUDY 001 ANALYSIS SUMMARY")
    summary_lines.append("=" * WIDTH)
    summary_lines.append("")

    for cond_key, cond_label in CONDITIONS.items():
        s = scores[cond_key]
        summary_lines.append(f"{cond_label}:")
        summary_lines.append(f"  Cat1+2: {s['category_1_2_total']:.1f}/5.0")
        summary_lines.append(f"  Cat3:   {s['category_3_total']:.0f}/3")
        summary_lines.append(f"  Cat4:   {s['category_4_total']:.0f}/2")
        summary_lines.append(f"  Overall: {s['overall']:.1f}/10.0")
        summary_lines.append("")

    summary_lines.append("SUCCESS CRITERIA:")
    summary_lines.append(f"  Bar 1 (Detail Fidelity):  {'PASS' if b1['passed'] else 'FAIL'} (delta: {b1['difference']:.2f}, threshold: {b1['threshold']:.2f})")
    summary_lines.append(f"  Bar 2 (Topic Bleed):      {'PASS' if b2['passed'] else 'FAIL'}")
    summary_lines.append(f"  Bar 3 (Behavioral):       {'PASS' if b3['passed'] else 'FAIL'}")
    summary_lines.append(f"  Overall: {criteria['overall']}")
    summary_lines.append("")

    for cond_key, cond_label in CONDITIONS.items():
        mp = read_model_performance(os.path.join(RUN_DIR, cond_key))
        summary_lines.append(f"{cond_label} peak tokens: ~{mp['peak_estimated_tokens']:,} (turn {mp['peak_turn']})")

    summary_lines.append("")
    summary_lines.append(f"Condition C avg K: {kvals['avg_k_per_turn']}")
    summary_lines.append(f"Condition C topics: {memstore['final_topic_count']}")
    summary_lines.append(f"Condition C episodes: {memstore['final_episode_count']}")

    summary_path = os.path.join(STUDY_DIR, "analysis_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print_section("PROTOCOL NOTES")
    print("[See experiments/study_001/README.md for full protocol notes]")
    print("=" * WIDTH)
    print(f"\nSummary written to: {summary_path}")


if __name__ == "__main__":
    run_analysis()
