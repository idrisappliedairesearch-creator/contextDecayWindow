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
    Returns: final_topic_count, final_episode_count,
             compaction_events (list of turns where compaction fired).
    """
    path = os.path.join(run_dir, "metrics", "memory_store.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    if not rows:
        return {
            "final_topic_count": 0,
            "final_episode_count": 0,
            "compaction_events": [],
        }

    final = rows[-1]
    compaction_events = [
        int(r["turn"]) for r in rows if r.get("compaction_occurred", "").lower() == "true"
    ]

    return {
        "final_topic_count": int(final["topic_count"]),
        "final_episode_count": int(final["episode_count"]),
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
