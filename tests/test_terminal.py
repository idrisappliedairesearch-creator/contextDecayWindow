import os
import sys
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability.terminal import TerminalPrinter
from src.observability.turn_record import TurnRecord


class TestTerminalPrinterFormat:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 4,
            "condition": "iterative",
            "user_message": "We agreed the budget cap was $47,500...",
            "k_count": 3,
            "n_count": 7,
            "total_in_context": 7,
            "k_episodes": [
                {"id": "ep_a3f2b901", "sim_score": 0.84, "decay_score": 0.92, "topic_label": "topic_1"},
                {"id": "ep_b901c412", "sim_score": 0.79, "decay_score": 0.88, "topic_label": "topic_1"},
                {"id": "ep_c412d333", "sim_score": 0.71, "decay_score": 0.61, "topic_label": "topic_2"},
            ],
            "n_episodes": [
                {"id": "ep_a3f2b901", "decay_score": 0.92, "topic_label": "topic_1"},
                {"id": "ep_b901c412", "decay_score": 0.88, "topic_label": "topic_1"},
                {"id": "ep_c412d333", "decay_score": 0.61, "topic_label": "topic_2"},
            ],
            "estimated_tokens": 4832,
            "k_token_estimate": 1203,
            "n_token_estimate": 1644,
            "topic_count": 3,
            "episode_count": 7,
            "new_topic_created": False,
            "new_topic_label": None,
            "centroid_drift": {"topic_1": 0.023},
            "tokens_per_second": 47.2,
            "time_to_first_token": 0.31,
            "output_tokens": 312,
            "assistant_message": "The agreed budget cap was $47,500...",
            "stored_episode_id": "ep_d771e888",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "prompt text",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_prints_turn_header(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "TURN 04" in out
        assert "Topics: 3" in out
        assert "Episodes: 7" in out
        assert "~4,832" in out

    def test_prints_user_message(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(user_message="Hello world")
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[USER] Hello world" in out

    def test_prints_retrieval_info(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[RETRIEVAL] K=3 above 0.50" in out
        assert "N=7" in out
        assert "K-only" in out

    def test_prints_episode_details(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "ep_a3f2b" in out
        assert "sim: 0.84" in out
        assert "decay: 0.92" in out
        assert "topic: topic_1" in out

    def test_prints_topic_layer_no_new(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(new_topic_created=False, centroid_drift={"topic_1": 0.023})
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "No new nodes" in out
        assert "Centroid drift: topic_1=0.023" in out

    def test_prints_topic_layer_new_topic(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(new_topic_created=True, new_topic_label="topic_4", centroid_drift={})
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "New topic: topic_4 created" in out

    def test_prints_context_built(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "~4,832 tokens" in out
        assert "K: ~1,203" in out
        assert "N: ~1,644" in out

    def test_prints_generation_full(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(tokens_per_second=47.2, time_to_first_token=0.31, output_tokens=312)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "47.2 tok/s" in out
        assert "TTFT: 0.31s" in out
        assert "Output: 312 tokens" in out

    def test_generation_none_renders_dashes(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(
            tokens_per_second=None,
            time_to_first_token=None,
            output_tokens=None,
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "---" in out

    def test_prints_storage_line(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(stored_episode_id="ep_d771e888", stored_topic_label="topic_1")
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "ep_d771e stored" in out
        assert "Topic: topic_1" in out

    def test_prints_decay_updated(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(n_count=7)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[DECAY UPDATED] 7 episodes updated" in out

    def test_prints_assistant_message(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(assistant_message="The answer is 42")
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[ASSISTANT] The answer is 42" in out

    def test_no_assistant_when_none(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(assistant_message=None)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[ASSISTANT]" not in out


class TestTerminalTruncation:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "full_context",
            "user_message": "x" * 200,
            "k_episodes": [],
            "n_episodes": [],
            "topic_count": 1,
            "episode_count": 1,
            "estimated_tokens": 100,
            "k_token_estimate": 50,
            "n_token_estimate": 50,
            "assistant_message": "y" * 200,
            "stored_episode_id": "ep_12345678",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_truncates_user_message_at_120_chars(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(user_message="a" * 200)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[USER] " + "a" * 120 + "..." in out

    def test_truncates_assistant_message_at_120_chars(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(assistant_message="b" * 200)
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[ASSISTANT] " + "b" * 120 + "..." in out

    def test_does_not_truncate_short_messages(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(user_message="Short msg", assistant_message="Also short")
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[USER] Short msg" in out
        assert "[ASSISTANT] Also short" in out

    def test_truncates_episode_id_to_8_chars(self, capsys):
        printer = TerminalPrinter()
        long_id = "ep_a1b2c3d4e5f6g7h8"
        record = self._make_record(
            k_episodes=[{"id": long_id, "sim_score": 0.8, "decay_score": 0.9, "topic_label": "topic_1"}],
            stored_episode_id=long_id,
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "ep_a1b2c" in out


class TestTerminalCentroidDrift:

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "iterative",
            "user_message": "Test",
            "k_episodes": [],
            "n_episodes": [],
            "topic_count": 2,
            "episode_count": 3,
            "estimated_tokens": 100,
            "k_token_estimate": 50,
            "n_token_estimate": 50,
            "stored_episode_id": "ep_12345678",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_zero_drift_topics_suppressed(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(
            new_topic_created=False,
            centroid_drift={"topic_1": 0.0, "topic_2": 0.0},
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "Centroid drift:" not in out
        assert "No new nodes" in out

    def test_only_nonzero_drift_shown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(
            new_topic_created=False,
            centroid_drift={"topic_1": 0.0, "topic_2": 0.045},
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "topic_2=0.045" in out
        assert "topic_1=" not in out

    def test_multiple_drifts_shown(self, capsys):
        printer = TerminalPrinter()
        record = self._make_record(
            new_topic_created=False,
            centroid_drift={"topic_1": 0.012, "topic_2": 0.034},
        )
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "topic_1=0.012" in out
        assert "topic_2=0.034" in out
