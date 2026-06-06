import os
import sys
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability.terminal import TerminalPrinter
from src.observability.turn_record import TurnRecord, ConsolidationResult


class TestTerminalConditionC:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 47,
            "condition": "iterative",
            "user_message": "In the context of Keynesian monetary theory, what specific mechanisms...",
            "contains_rule": False,
            "rule_summary": None,
            "rule_store_count": 2,
            "rule_token_estimate": 3400,
            "k_count": 4,
            "n_count": 10,
            "n_total_in_store": 47,
            "k_only_count": 2,
            "total_in_context": 12,
            "k_episodes": [
                {"id": "ep_a3f2b901", "sim_score": 0.81, "decay_score": 0.94, "topic_label": "topic_3", "retrieval_type": "KN"},
                {"id": "ep_c7d1e445", "sim_score": 0.74, "decay_score": 0.88, "topic_label": "topic_3", "retrieval_type": "KN"},
                {"id": "ep_f902aa31", "sim_score": 0.67, "decay_score": 0.41, "topic_label": "topic_1", "retrieval_type": "K"},
                {"id": "ep_b210cc77", "sim_score": 0.51, "decay_score": 0.29, "topic_label": "topic_1", "retrieval_type": "K"},
            ],
            "n_episodes": [
                {"id": "ep_n001", "decay_score": 0.99, "topic_label": "topic_1", "retrieval_type": "N"},
                {"id": "ep_n002", "decay_score": 0.98, "topic_label": "topic_1", "retrieval_type": "N"},
                {"id": "ep_n003", "decay_score": 0.97, "topic_label": "topic_2", "retrieval_type": "N"},
                {"id": "ep_n004", "decay_score": 0.96, "topic_label": "topic_2", "retrieval_type": "N"},
                {"id": "ep_n005", "decay_score": 0.95, "topic_label": "topic_3", "retrieval_type": "N"},
                {"id": "ep_n006", "decay_score": 0.93, "topic_label": "topic_3", "retrieval_type": "N"},
                {"id": "ep_n007", "decay_score": 0.91, "topic_label": "topic_4", "retrieval_type": "N"},
                {"id": "ep_n008", "decay_score": 0.89, "topic_label": "topic_4", "retrieval_type": "N"},
            ],
            "estimated_tokens": 18240,
            "k_token_estimate": 6800,
            "n_token_estimate": 8040,
            "topic_count": 8,
            "episode_count": 47,
            "new_topic_created": False,
            "new_topic_label": None,
            "centroid_drift": {"topic_3": 0.031},
            "consolidation_occurred": False,
            "consolidation_result": None,
            "tokens_per_second": 44.1,
            "time_to_first_token": 0.02,
            "output_tokens": 1487,
            "assistant_message": "Drawing on Keynesian monetary theory, the transmission mechanisms...",
            "stored_episode_id": "ep_d771f300",
            "stored_topic_label": "topic_3",
            "constructed_prompt": "prompt text",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_header_3digit_turn_and_condition(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "TURN 047" in out
        assert "Condition: iterative" in out
        assert "Topics: 8" in out
        assert "Store: 47" in out
        assert "~18,240" in out

    def test_rule_store_line_with_tokens(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[RULE STORE] 2 rules pinned (~3,400 tokens)" in out
        assert "Rule detected this turn: No" in out

    def test_rule_store_line_rule_detected(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(contains_rule=True, rule_summary="Budget cap")
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert 'Rule detected this turn: Yes — "Budget cap"' in out

    def test_retrieval_line_with_cap(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[RETRIEVAL] K=4 above 0.50" in out
        assert "N=10 (cap)" in out
        assert "+ 2 K-only" in out
        assert "Store: 47 episodes" in out

    def test_retrieval_line_without_cap(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(n_count=7, k_episodes=[])
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "N=7 " in out
        assert "(cap)" not in out

    def test_episode_detail_lines_with_type(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "ep_a3f2b" in out
        assert "sim: 0.81" in out
        assert "decay: 0.94" in out
        assert "type: KN  " in out
        assert "topic: topic_3" in out

    def test_n_only_summary_line(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "(+ 8 N-only episodes not shown" in out
        assert "see retrieval.jsonl" in out

    def test_no_n_only_line_when_empty(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(n_episodes=[])
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "N-only episodes not shown" not in out

    def test_topic_layer_full(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[TOPIC LAYER] Topics: 8" in out
        assert "New node: No" in out
        assert "Centroid drift: topic_3=0.031" in out

    def test_topic_layer_new_node_yes(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(new_topic_created=True, new_topic_label="topic_9")
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "New node: Yes" in out

    def test_context_built_with_breakdown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "~18,240 tokens" in out
        assert "Rules: ~3,400" in out
        assert "K: ~6,800" in out
        assert "N: ~8,040" in out

    def test_generation_line_with_tilde_ttft(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "44.1 tok/s" in out
        assert "~TTFT: 0.02s" in out
        assert "Output: 1487 tokens" in out

    def test_storage_line(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "ep_d771f stored" in out
        assert "Topic: topic_3" in out
        assert "Embedding: done" in out

    def test_decay_updated_count(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[DECAY UPDATED] 12 episodes updated" in out

    def test_assistant_message_after_dash(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assistant_line = None
        for i, line in enumerate(lines):
            if "[ASSISTANT]" in line:
                assistant_line = i
                break
        assert assistant_line is not None
        assert "─" * 62 in lines[assistant_line - 1]

    def test_consolidation_present_when_occurred(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(
            consolidation_occurred=True,
            consolidation_result=ConsolidationResult(
                triggered_at_episode=20,
                topics_before=5,
                topics_after=4,
                pairs_merged=1,
                merge_log=[
                    {
                        "surviving_label": "topic_1",
                        "merged_label": "topic_2",
                        "similarity": 0.72,
                        "episodes_reassigned": 3,
                    }
                ],
            ),
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" in out
        assert "Topics: 5" in out
        assert "4" in out
        assert "Merged: 1 pairs" in out
        assert "topic_2 + topic_1 (sim: 0.72)" in out

    def test_consolidation_absent_when_not_occurred(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(consolidation_occurred=False, consolidation_result=None)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" not in out

    def test_consolidation_no_merge(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(
            consolidation_occurred=True,
            consolidation_result=ConsolidationResult(
                triggered_at_episode=15,
                topics_before=3,
                topics_after=3,
                pairs_merged=0,
                merge_log=[],
            ),
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" in out
        assert "No pairs above 0.60" in out


class TestTerminalConditionA:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 5,
            "condition": "full_context",
            "user_message": "Test message",
            "contains_rule": False,
            "rule_summary": None,
            "rule_store_count": 0,
            "rule_token_estimate": 0,
            "k_count": 0,
            "n_count": 0,
            "n_total_in_store": 0,
            "k_only_count": 0,
            "total_in_context": 0,
            "k_episodes": [],
            "n_episodes": [],
            "estimated_tokens": 5000,
            "k_token_estimate": 0,
            "n_token_estimate": 0,
            "topic_count": 0,
            "episode_count": 0,
            "new_topic_created": False,
            "new_topic_label": None,
            "centroid_drift": {},
            "consolidation_occurred": False,
            "consolidation_result": None,
            "tokens_per_second": 40.0,
            "time_to_first_token": 0.15,
            "output_tokens": 300,
            "assistant_message": "Response",
            "stored_episode_id": None,
            "stored_topic_label": None,
            "constructed_prompt": "prompt",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_condition_a_header(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "Condition: full_context" in out

    def test_condition_a_rule_store_shown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[RULE STORE] 0 rules pinned (~0 tokens)" in out

    def test_condition_a_retrieval_na(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "N/A (full context condition)" in out

    def test_condition_a_topic_layer_na(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        na_count = out.count("N/A (full context condition)")
        assert na_count >= 2

    def test_condition_a_context_built_no_breakdown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONTEXT BUILT] ~5,000 tokens" in out
        assert "Rules:" not in out.split("[CONTEXT BUILT]")[1].split("\n")[0]

    def test_condition_a_decay_zero(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[DECAY UPDATED] 0 episodes updated" in out

    def test_condition_a_no_consolidation(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" not in out


class TestTerminalConditionB:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 10,
            "condition": "compaction",
            "user_message": "Test message",
            "contains_rule": False,
            "rule_summary": None,
            "rule_store_count": 0,
            "rule_token_estimate": 0,
            "k_count": 0,
            "n_count": 0,
            "n_total_in_store": 0,
            "k_only_count": 0,
            "total_in_context": 0,
            "k_episodes": [],
            "n_episodes": [],
            "estimated_tokens": 3500,
            "k_token_estimate": 0,
            "n_token_estimate": 0,
            "topic_count": 0,
            "episode_count": 0,
            "new_topic_created": False,
            "new_topic_label": None,
            "centroid_drift": {},
            "consolidation_occurred": False,
            "consolidation_result": None,
            "tokens_per_second": 35.0,
            "time_to_first_token": 0.2,
            "output_tokens": 250,
            "assistant_message": "Response",
            "stored_episode_id": None,
            "stored_topic_label": None,
            "compaction_occurred": True,
            "compaction_turn": 10,
            "history_tokens_before_compaction": 3000,
            "constructed_prompt": "prompt",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_condition_b_header(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "Condition: compaction" in out

    def test_condition_b_retrieval_na(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "N/A (full context condition)" in out

    def test_condition_b_compaction_shown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[COMPACTION]" in out
        assert "Replaced ~3,000 tokens" in out

    def test_condition_b_no_consolidation(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" not in out


class TestTerminalZeroPadding:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "iterative",
            "user_message": "Test",
            "k_episodes": [],
            "n_episodes": [],
            "topic_count": 1,
            "episode_count": 1,
            "estimated_tokens": 100,
            "k_token_estimate": 50,
            "n_token_estimate": 50,
            "rule_store_count": 0,
            "rule_token_estimate": 0,
            "stored_episode_id": "ep_12345678",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_turn_1_zero_padded_to_3_digits(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(turn_number=1)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "TURN 001" in out

    def test_turn_99_zero_padded(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(turn_number=99)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "TURN 099" in out

    def test_turn_120_not_padded(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(turn_number=120)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "TURN 120" in out


class TestTerminalKOnlyEpisodesSuppressed:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "iterative",
            "user_message": "Test",
            "k_count": 2,
            "n_count": 10,
            "n_total_in_store": 20,
            "k_episodes": [
                {"id": "ep_k001", "sim_score": 0.8, "decay_score": 0.9, "topic_label": "topic_1", "retrieval_type": "K"},
            ],
            "n_episodes": [
                {"id": "ep_n001", "decay_score": 0.99, "topic_label": "topic_1", "retrieval_type": "N"},
                {"id": "ep_n002", "decay_score": 0.98, "topic_label": "topic_1", "retrieval_type": "N"},
            ],
            "estimated_tokens": 500,
            "k_token_estimate": 200,
            "n_token_estimate": 300,
            "topic_count": 1,
            "episode_count": 5,
            "rule_store_count": 0,
            "rule_token_estimate": 0,
            "stored_episode_id": "ep_12345678",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_only_k_episodes_shown_in_detail(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "ep_k001" in out
        assert "ep_n001" not in out
        assert "ep_n002" not in out

    def test_n_only_count_shown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "(+ 2 N-only episodes not shown" in out

    def test_all_n_only_no_k_detail(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(k_count=0, k_episodes=[], n_count=10, n_total_in_store=15)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "K=0 above 0.50" in out
        assert "(+ 2 N-only episodes not shown" in out
