from src.observability.turn_record import TurnRecord


def _format_rule_detected(record: TurnRecord) -> str:
    if record.contains_rule and record.rule_summary:
        return f'Yes — "{record.rule_summary}"'
    return "No"


class TerminalPrinter:

    def print_turn(self, record: TurnRecord) -> None:
        sep_eq = "═" * 50
        sep_da = "─" * 50

        turn_num = f"{record.turn_number:02d}"
        topics = record.topic_count
        episodes = record.episode_count
        tokens = f"{record.estimated_tokens:,}"

        print(f"{sep_eq}")
        print(f"TURN {turn_num} | Topics: {topics} | Episodes: {episodes} | Tokens: ~{tokens}")
        print(f"{sep_eq}")

        user_truncated = self._truncate(record.user_message, 120)
        print(f"[USER] {user_truncated}")
        print()

        k_count = record.k_count
        n_count = record.n_count
        n_total = record.n_total_in_store
        k_only_count = len([ep for ep in record.k_episodes if ep.get("retrieval_type") == "K"])
        n_cap_label = "(cap)" if n_count >= 10 else ""
        print(f"[RETRIEVAL] K={k_count} above 0.50 | N={n_count} {n_cap_label} + {k_only_count} K-only | Store: {n_total} episodes")

        rule_detected_str = _format_rule_detected(record)
        print(f"[RULE STORE] {record.rule_store_count} rules pinned | Rule detected this turn: {rule_detected_str}")

        for ep in record.k_episodes:
            ep_id = self._truncate_id(ep.get("id", ""))
            sim = ep.get("sim_score", 0.0)
            decay = ep.get("decay_score", 0.0)
            topic = ep.get("topic_label", "")
            print(f"  → {ep_id} | sim: {sim:.2f} | decay: {decay:.2f} | topic: {topic}")

        topic_line = self._build_topic_line(record)
        print(f"[TOPIC LAYER] {topic_line}")

        self._print_consolidation(record)

        k_tok = f"{record.k_token_estimate:,}"
        n_tok = f"{record.n_token_estimate:,}"
        print(f"[CONTEXT BUILT] ~{record.estimated_tokens:,} tokens | K: ~{k_tok} | N: ~{n_tok}")

        if record.compaction_occurred:
            replaced = record.history_tokens_before_compaction or 0
            print(f"[COMPACTION] History compacted at turn {record.compaction_turn} | Replaced ~{replaced:,} tokens -> summary")

        gen_line = self._build_gen_line(record)
        print(f"[GENERATION] {gen_line}")

        storage_line = self._build_storage_line(record)
        print(f"[STORAGE] {storage_line}")

        n_count_for_decay = record.n_count
        print(f"[DECAY UPDATED] {n_count_for_decay} episodes updated")

        print(sep_da)

        if record.assistant_message:
            asst_truncated = self._truncate(record.assistant_message, 120)
            print(f"[ASSISTANT] {asst_truncated}")
        print(f"{sep_eq}")
        print()

    def _print_consolidation(self, record: TurnRecord) -> None:
        if not record.consolidation_occurred:
            return

        result = record.consolidation_result
        if result is None:
            return

        if result.pairs_merged == 0:
            print(f"[CONSOLIDATION] Episode {result.triggered_at_episode} trigger | No pairs above 0.60 | Topics unchanged: {result.topics_after}")
        else:
            print(f"[CONSOLIDATION] Episode {result.triggered_at_episode} trigger | Topics: {result.topics_before} → {result.topics_after} | Merged: {result.pairs_merged} pairs")
            for entry in result.merge_log:
                surviving = entry["surviving_label"]
                merged = entry["merged_label"]
                sim = entry["similarity"]
                reassigned = entry["episodes_reassigned"]
                print(f"  → {merged} + {surviving} (sim: {sim:.2f}) → {surviving} | {reassigned} episodes reassigned")

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def _truncate_id(self, ep_id: str) -> str:
        if not ep_id:
            return ep_id
        return ep_id[:8]

    def _build_topic_line(self, record: TurnRecord) -> str:
        parts = []

        if record.new_topic_created:
            label = record.new_topic_label or "unknown"
            parts.append(f"New topic: {label} created")
        else:
            parts.append("No new nodes")

        drifts = {k: v for k, v in record.centroid_drift.items() if v > 0}
        if drifts:
            drift_strs = [f"{label}={drift:.3f}" for label, drift in drifts.items()]
            parts.append(f"Centroid drift: {', '.join(drift_strs)}")

        return " | ".join(parts)

    def _build_gen_line(self, record: TurnRecord) -> str:
        if record.tokens_per_second is not None:
            tps = f"{record.tokens_per_second:.1f} tok/s"
        else:
            tps = "---"

        if record.time_to_first_token is not None:
            ttft = f"TTFT: {record.time_to_first_token:.2f}s"
        else:
            ttft = "---"

        if record.output_tokens is not None:
            out = f"Output: {record.output_tokens} tokens"
        else:
            out = "---"

        return f"{tps} | {ttft} | {out}"

    def _build_storage_line(self, record: TurnRecord) -> str:
        parts = []

        if record.stored_episode_id:
            ep_id = self._truncate_id(record.stored_episode_id)
            parts.append(f"{ep_id} stored")
        else:
            parts.append("Not stored")

        if record.stored_topic_label:
            parts.append(f"Topic: {record.stored_topic_label}")

        parts.append("Embedding: done")

        return " | ".join(parts)
