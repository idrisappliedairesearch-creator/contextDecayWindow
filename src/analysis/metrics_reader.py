import csv
import os


def read_model_performance(run_dir: str) -> dict:
    """
    Reads model_performance.csv.
    Returns: avg_tokens_per_second, avg_output_tokens, total_output_tokens,
             peak_estimated_tokens (max context size across all turns),
             peak_turn (turn number where peak occurred).
    """
    path = os.path.join(run_dir, "metrics", "model_performance.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    if not rows:
        return {
            "avg_tokens_per_second": 0,
            "avg_output_tokens": 0,
            "total_output_tokens": 0,
            "peak_estimated_tokens": 0,
            "peak_turn": 0,
        }

    tps_values = [float(r["tokens_per_second"]) for r in rows]
    output_tokens = [int(r["output_tokens"]) for r in rows]
    estimated_tokens = [int(r["estimated_tokens"]) for r in rows]
    turns = [int(r["turn"]) for r in rows]

    peak_idx = estimated_tokens.index(max(estimated_tokens))

    return {
        "avg_tokens_per_second": round(sum(tps_values) / len(tps_values), 1),
        "avg_output_tokens": round(sum(output_tokens) / len(output_tokens), 1),
        "total_output_tokens": sum(output_tokens),
        "peak_estimated_tokens": max(estimated_tokens),
        "peak_turn": turns[peak_idx],
    }


def read_memory_store(run_dir: str) -> dict:
    """
    Reads memory_store.csv.
    Returns: final_topic_count, final_episode_count, topic counts at specific turns,
             compaction_events (list of turns where compaction fired).
    """
    path = os.path.join(run_dir, "metrics", "memory_store.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    if not rows:
        return {
            "final_topic_count": 0,
            "final_episode_count": 0,
            "topics_at_turn_10": 0,
            "topics_at_turn_60": 0,
            "topics_at_turn_120": 0,
            "compaction_events": [],
        }

    final = rows[-1]
    compaction_events = [
        int(r["turn"]) for r in rows if r.get("compaction_occurred", "").lower() == "true"
    ]

    turn_topics = {}
    for r in rows:
        turn_topics[int(r["turn"])] = int(r["topic_count"])

    return {
        "final_topic_count": int(final["topic_count"]),
        "final_episode_count": int(final["episode_count"]),
        "topics_at_turn_10": turn_topics.get(10, 0),
        "topics_at_turn_60": turn_topics.get(60, 0),
        "topics_at_turn_120": turn_topics.get(120, 0),
        "compaction_events": compaction_events,
    }


def read_k_values(run_dir: str) -> dict:
    """
    Reads K_values.csv.
    Returns: avg_k_per_turn, max_k_per_turn, turns_with_zero_k (count),
             total_retrieval_events.
    """
    path = os.path.join(run_dir, "metrics", "K_values.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    if not rows:
        return {
            "avg_k_per_turn": 0,
            "max_k_per_turn": 0,
            "turns_with_zero_k": 0,
            "total_retrieval_events": 0,
        }

    k_counts = [int(r["k_count"]) for r in rows]
    total_events = len(rows)

    turn_k_counts = {}
    for r in rows:
        turn = int(r["turn"])
        if turn not in turn_k_counts:
            turn_k_counts[turn] = 0
        turn_k_counts[turn] += int(r["k_count"])

    turns_with_zero = sum(1 for v in turn_k_counts.values() if v == 0)
    avg_k = round(sum(turn_k_counts.values()) / len(turn_k_counts), 1) if turn_k_counts else 0
    max_k = max(turn_k_counts.values()) if turn_k_counts else 0

    return {
        "avg_k_per_turn": avg_k,
        "max_k_per_turn": max_k,
        "turns_with_zero_k": turns_with_zero,
        "total_retrieval_events": total_events,
    }


def read_token_growth(run_dir: str) -> list:
    """
    Reads model_performance.csv.
    Returns per-turn token estimates as list of dicts for growth curve comparison.
    """
    path = os.path.join(run_dir, "metrics", "model_performance.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    return [
        {
            "turn": int(r["turn"]),
            "estimated_tokens": int(r["estimated_tokens"]),
            "output_tokens": int(r["output_tokens"]),
            "tokens_per_second": float(r["tokens_per_second"]),
        }
        for r in rows
    ]


def read_k_activity(run_dir: str) -> dict:
    """
    Reads K_values.csv and retrieval_events.csv.
    Returns K retrieval activity metrics.
    """
    k_path = os.path.join(run_dir, "metrics", "K_values.csv")
    ret_path = os.path.join(run_dir, "metrics", "retrieval_events.csv")

    if not os.path.exists(k_path):
        return {
            "k_events_total": 0,
            "k_events_per_turn": [],
            "k_only_episodes_total": 0,
            "first_k_fire_turn": 0,
            "k_zero_turns": 0,
        }

    k_rows = list(csv.DictReader(open(k_path, encoding="utf-8")))
    if not k_rows:
        return {
            "k_events_total": 0,
            "k_events_per_turn": [],
            "k_only_episodes_total": 0,
            "first_k_fire_turn": 0,
            "k_zero_turns": 0,
        }

    turn_k_counts = {}
    for r in k_rows:
        turn = int(r["turn"])
        kc = int(r["k_count"])
        if turn not in turn_k_counts:
            turn_k_counts[turn] = kc
        else:
            turn_k_counts[turn] = max(turn_k_counts[turn], kc)

    k_events_total = sum(turn_k_counts.values())
    all_turns = set(range(1, 121))
    active_turns = set(turn_k_counts.keys())
    k_zero_turns = len(all_turns - active_turns)
    first_k_fire = min(active_turns) if active_turns else 0

    k_only_total = 0
    if os.path.exists(ret_path):
        ret_rows = list(csv.DictReader(open(ret_path, encoding="utf-8")))
        k_only_total = sum(
            1 for r in ret_rows if r.get("retrieval_type", "") == "K"
        )

    sorted_turns = sorted(active_turns)
    k_events_per_turn = [turn_k_counts[t] for t in sorted_turns]

    return {
        "k_events_total": k_events_total,
        "k_events_per_turn": k_events_per_turn,
        "k_only_episodes_total": k_only_total,
        "first_k_fire_turn": first_k_fire,
        "k_zero_turns": k_zero_turns,
    }


def read_consolidation_activity(run_dir: str) -> dict:
    """
    Reads consolidation_events.csv and memory_store.csv.
    Returns topic consolidation metrics.
    """
    cons_path = os.path.join(run_dir, "metrics", "consolidation_events.csv")
    mem = read_memory_store(run_dir)

    consolidation_passes = 0
    total_pairs_merged = 0

    if os.path.exists(cons_path):
        cons_rows = list(csv.DictReader(open(cons_path, encoding="utf-8")))
        consolidation_passes = len(cons_rows)
        for r in cons_rows:
            total_pairs_merged += int(r.get("pairs_merged", 0))

    return {
        "consolidation_passes": consolidation_passes,
        "total_pairs_merged": total_pairs_merged,
        "topics_at_turn_10": mem["topics_at_turn_10"],
        "topics_at_turn_60": mem["topics_at_turn_60"],
        "topics_at_turn_120": mem["topics_at_turn_120"],
        "final_topic_count": mem["final_topic_count"],
    }


def read_rule_detection(run_dir: str) -> dict:
    """
    Reads rule_detection.csv.
    Returns rule detection accuracy metrics.
    """
    path = os.path.join(run_dir, "metrics", "rule_detection.csv")

    if not os.path.exists(path):
        return {
            "total_detections": 0,
            "ground_truth_turns": [1, 2],
            "recall": 0.0,
            "estimated_false_positives": 0,
        }

    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows:
        return {
            "total_detections": 0,
            "ground_truth_turns": [1, 2],
            "recall": 0.0,
            "estimated_false_positives": 0,
        }

    ground_truth_turns = [1, 2]
    total_detections = sum(
        1 for r in rows if r.get("contains_rule_detected", "").strip().lower() == "true"
    )

    gt_turns_with_detection = sum(
        1 for r in rows
        if int(r["turn_number"]) in ground_truth_turns
        and r.get("true_positive", "").strip().lower() == "true"
    )

    recall = gt_turns_with_detection / len(ground_truth_turns) if ground_truth_turns else 0.0

    fps = sum(
        1 for r in rows if r.get("false_positive", "").strip().lower() == "true"
    )

    return {
        "total_detections": total_detections,
        "ground_truth_turns": ground_truth_turns,
        "recall": round(recall, 2),
        "estimated_false_positives": fps,
    }


def read_token_efficiency(iterative_dir: str, full_context_dir: str) -> dict:
    """
    Compares token growth between iterative and full context.
    Returns efficiency metrics.
    """
    iter_growth = read_token_growth(iterative_dir)
    fc_growth = read_token_growth(full_context_dir)

    iter_peak = max((r["estimated_tokens"] for r in iter_growth), default=0)
    fc_peak = max((r["estimated_tokens"] for r in fc_growth), default=0)

    efficiency_ratio = round(iter_peak / fc_peak, 4) if fc_peak > 0 else 0.0

    fc_by_turn = {r["turn"]: r["estimated_tokens"] for r in fc_growth}
    iter_by_turn = {r["turn"]: r["estimated_tokens"] for r in iter_growth}

    violations = [
        t for t in iter_by_turn
        if iter_by_turn[t] > fc_by_turn.get(t, 0)
    ]

    cap_saturation_turn = 0
    for r in iter_growth:
        if r["estimated_tokens"] >= 10000:
            cap_saturation_turn = r["turn"]
            break

    return {
        "iterative_peak": iter_peak,
        "full_context_peak": fc_peak,
        "efficiency_ratio": efficiency_ratio,
        "turns_where_iterative_exceeds": violations,
        "cap_saturation_turn": cap_saturation_turn,
    }
