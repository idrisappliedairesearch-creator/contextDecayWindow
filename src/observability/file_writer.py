import csv
import difflib
import json
import os
import sqlite3
from pathlib import Path

import numpy as np

from src.observability.run_config import RunConfig
from src.observability.turn_record import TurnRecord


class FileWriter:

    def __init__(self, config: RunConfig):
        self.config = config

    def init_run(self) -> None:
        logs_dir = os.path.join(self.config.output_dir, "logs")
        metrics_dir = os.path.join(self.config.output_dir, "metrics")
        snapshots_dir = os.path.join(self.config.output_dir, "snapshots")
        rubric_dir = os.path.join(self.config.output_dir, "rubric")
        prompts_dir = os.path.join(self.config.output_dir, "constructed_prompts")

        for d in [logs_dir, metrics_dir, snapshots_dir, rubric_dir, prompts_dir]:
            os.makedirs(d, exist_ok=True)

        os.makedirs(self.config.output_dir, exist_ok=True)

        for fname in ["turns.jsonl", "retrieval.jsonl", "context_windows.jsonl", "context_diffs.jsonl"]:
            open(os.path.join(logs_dir, fname), "w", encoding="utf-8").close()

        self._create_csv_headers(metrics_dir)

        with open(os.path.join(rubric_dir, "responses.md"), "w", encoding="utf-8") as f:
            f.write("# Responses\n\n")

        with open(os.path.join(rubric_dir, "scores.md"), "w", encoding="utf-8") as f:
            f.write("# Scores\n\n")

    def _create_csv_headers(self, metrics_dir: str) -> None:
        csv_files = {
            "model_performance.csv": ["turn", "tokens_per_second", "time_to_first_token", "output_tokens", "estimated_tokens"],
            "memory_store.csv": ["turn", "topic_count", "episode_count", "new_topic_created", "new_topic_label", "compaction_occurred", "compaction_turn"],
            "K_values.csv": ["turn", "k_count", "episode_id", "similarity_score", "topic_label", "k_only"],
            "N_values.csv": ["turn", "n_count", "episode_id", "decay_score", "topic_label", "n_total_in_store"],
            "topic_events.csv": ["turn", "event_type", "topic_label", "centroid_drift"],
            "retrieval_events.csv": ["turn", "episode_id", "similarity_score", "decay_score", "retrieval_type"],
            "rule_detection.csv": ["turn_number", "contains_rule_detected", "rule_summary", "parse_error", "ground_truth", "true_positive", "false_positive"],
            "consolidation_events.csv": ["episode_count_at_trigger", "turn_number", "topics_before", "topics_after", "pairs_merged", "surviving_labels", "merged_labels", "similarities", "episodes_reassigned"],
        }

        for fname, headers in csv_files.items():
            fpath = os.path.join(metrics_dir, fname)
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def write_turn(self, record: TurnRecord) -> None:
        self._write_turns_jsonl(record)
        self._write_retrieval_jsonl(record)
        self._write_context_windows_jsonl(record)
        self._write_context_diffs_jsonl(record)
        self._write_model_performance_csv(record)
        self._write_memory_store_csv(record)
        self._write_k_values_csv(record)
        self._write_n_values_csv(record)
        self._write_topic_events_csv(record)
        self._write_retrieval_events_csv(record)
        self._write_rule_detection_csv(record)
        self._write_consolidation_events_csv(record)
        self._write_snapshot(record)
        self._write_constructed_prompt(record)

    def _write_turns_jsonl(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "logs", "turns.jsonl")
        data = {
            "turn_number": record.turn_number,
            "condition": record.condition,
            "user_message": record.user_message,
            "k_count": record.k_count,
            "n_count": record.n_count,
            "n_total_in_store": record.n_total_in_store,
            "total_in_context": record.total_in_context,
            "k_episodes": record.k_episodes,
            "n_episodes": record.n_episodes,
            "estimated_tokens": record.estimated_tokens,
            "k_token_estimate": record.k_token_estimate,
            "n_token_estimate": record.n_token_estimate,
            "topic_count": record.topic_count,
            "episode_count": record.episode_count,
            "new_topic_created": record.new_topic_created,
            "new_topic_label": record.new_topic_label,
            "centroid_drift": record.centroid_drift,
            "consolidation_occurred": record.consolidation_occurred,
            "compaction_occurred": record.compaction_occurred,
            "compaction_turn": record.compaction_turn,
            "history_tokens_before_compaction": record.history_tokens_before_compaction,
            "tokens_per_second": record.tokens_per_second,
            "time_to_first_token": record.time_to_first_token,
            "output_tokens": record.output_tokens,
            "assistant_message": record.assistant_message,
            "stored_episode_id": record.stored_episode_id,
            "stored_topic_label": record.stored_topic_label,
            "constructed_prompt_path": f"constructed_prompts/turn_{record.turn_number:03d}.txt",
        }
        if record.consolidation_result is not None:
            res = record.consolidation_result
            data["consolidation_result"] = {
                "triggered_at_episode": res.triggered_at_episode,
                "topics_before": res.topics_before,
                "topics_after": res.topics_after,
                "pairs_merged": res.pairs_merged,
                "merge_log": res.merge_log,
            }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def _write_retrieval_jsonl(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "logs", "retrieval.jsonl")
        data = {
            "turn_number": record.turn_number,
            "k_count": record.k_count,
            "n_count": record.n_count,
            "k_episodes": record.k_episodes,
            "n_episodes": record.n_episodes,
        }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def _write_context_windows_jsonl(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "logs", "context_windows.jsonl")
        data = {
            "turn_number": record.turn_number,
            "estimated_tokens": record.estimated_tokens,
            "constructed_prompt_path": f"constructed_prompts/turn_{record.turn_number:03d}.txt",
        }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def _write_context_diffs_jsonl(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "logs", "context_diffs.jsonl")

        if record.previous_context_window is None:
            data = {"turn": record.turn_number, "note": "first turn, no diff"}
            with open(fpath, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
            return

        old_lines = record.previous_context_window.splitlines(keepends=True)
        new_lines = record.constructed_prompt.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
        lines_added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        lines_removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

        data = {
            "turn_number": record.turn_number,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "diff": "\n".join(diff),
        }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def _write_model_performance_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "model_performance.csv")
        row = [
            record.turn_number,
            self._none_to_dash(record.tokens_per_second),
            self._none_to_dash(record.time_to_first_token),
            self._none_to_dash(record.output_tokens),
            record.estimated_tokens,
        ]
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def _write_memory_store_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "memory_store.csv")
        row = [
            record.turn_number,
            record.topic_count,
            record.episode_count,
            record.new_topic_created,
            self._none_to_dash(record.new_topic_label),
            record.compaction_occurred,
            self._none_to_dash(record.compaction_turn),
        ]
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def _write_k_values_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "K_values.csv")
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for ep in record.k_episodes:
                writer.writerow([
                    record.turn_number,
                    record.k_count,
                    ep.get("id", ""),
                    ep.get("sim_score", 0.0),
                    ep.get("topic_label", ""),
                    ep.get("retrieval_type") == "K",
                ])

    def _write_n_values_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "N_values.csv")
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for ep in record.n_episodes:
                writer.writerow([
                    record.turn_number,
                    record.n_count,
                    ep.get("id", ""),
                    ep.get("decay_score", 0.0),
                    ep.get("topic_label", ""),
                    record.n_total_in_store,
                ])

    def _write_topic_events_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "topic_events.csv")
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if record.new_topic_created:
                writer.writerow([
                    record.turn_number,
                    "new_node",
                    record.new_topic_label or "",
                    0.0,
                ])
            for label, drift in record.centroid_drift.items():
                if drift > 0:
                    writer.writerow([
                        record.turn_number,
                        "centroid_update",
                        label,
                        drift,
                    ])

    def _write_rule_detection_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "rule_detection.csv")
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                record.turn_number,
                record.contains_rule,
                record.rule_summary or "",
                "",
                "",
                "",
                "",
            ])

    def _write_consolidation_events_csv(self, record: TurnRecord) -> None:
        if not record.consolidation_occurred or record.consolidation_result is None:
            return

        result = record.consolidation_result
        fpath = os.path.join(self.config.output_dir, "metrics", "consolidation_events.csv")
        surviving_labels = ";".join(entry["surviving_label"] for entry in result.merge_log)
        merged_labels = ";".join(entry["merged_label"] for entry in result.merge_log)
        similarities = ";".join(f"{entry['similarity']:.2f}" for entry in result.merge_log)
        episodes_reassigned = ";".join(str(entry["episodes_reassigned"]) for entry in result.merge_log)

        with open(fpath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                result.triggered_at_episode,
                record.turn_number,
                result.topics_before,
                result.topics_after,
                result.pairs_merged,
                surviving_labels,
                merged_labels,
                similarities,
                episodes_reassigned,
            ])

    def _write_retrieval_events_csv(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "metrics", "retrieval_events.csv")
        with open(fpath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for ep in record.k_episodes:
                writer.writerow([
                    record.turn_number,
                    ep.get("id", ""),
                    ep.get("sim_score", 0.0),
                    ep.get("decay_score", 0.0),
                    ep.get("retrieval_type", "K"),
                ])

    def _write_snapshot(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "snapshots", f"turn_{record.turn_number:03d}_db_state.json")
        data = {
            "turn_number": record.turn_number,
            "turns": record.turn_number,
            "topic_count": record.topic_count,
            "episode_count": record.episode_count,
            "estimated_tokens": record.estimated_tokens,
            "topics": [
                {
                    "label": label,
                    "centroid_dim": 1024,
                }
                for label in set(
                    ep.get("topic_label", "") for ep in record.k_episodes + record.n_episodes if ep.get("topic_label")
                )
            ],
            "embedding_dim": 1024,
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _write_constructed_prompt(self, record: TurnRecord) -> None:
        fpath = os.path.join(self.config.output_dir, "constructed_prompts", f"turn_{record.turn_number:03d}.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(record.constructed_prompt)

    @staticmethod
    def _none_to_dash(value) -> str:
        if value is None:
            return "---"
        return value
