import csv
import json
import os
import shutil
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.schema import init_db
from src.db.episode import store_episode
from src.db.topic import get_all_topics
from src.memory.topic_manager import TopicManager
from src.observability.run_config import RunConfig
from src.observability.file_writer import FileWriter
from src.observability.terminal import TerminalPrinter
from src.observability.turn_record import TurnRecord, AssignmentResult, ConsolidationResult


def _make_embedding(value: float = 1.0) -> np.ndarray:
    return np.full(1024, value, dtype=np.float32)


class TestConsolidationIntegrationAssignFlow:
    def _setup_db(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def _teardown_db(self):
        self.conn.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_full_assign_flow_triggers_consolidation_at_10(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            for i in range(10):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)

            assert isinstance(result, AssignmentResult)
            assert result.consolidation is not None
            assert isinstance(result.consolidation, ConsolidationResult)
            assert result.consolidation.triggered_at_episode == 10
        finally:
            self._teardown_db()

    def test_full_assign_flow_no_consolidation_at_9(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            for i in range(9):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)

            assert result.consolidation is None
        finally:
            self._teardown_db()

    def test_full_assign_flow_triggers_at_10_and_20(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            results = []
            for i in range(20):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                results.append(tm.assign(episode_id, emb))

            r9 = results[9]
            assert r9.consolidation is not None
            assert r9.consolidation.triggered_at_episode == 10

            r19 = results[19]
            assert r19.consolidation is not None
            assert r19.consolidation.triggered_at_episode == 20

            r10 = results[10]
            assert r10.consolidation is None
        finally:
            self._teardown_db()

    def test_full_flow_with_similar_topics_consolidates(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            emb1 = np.zeros(1024, dtype=np.float32)
            emb1[:600] = 1.0
            emb1[600:724] = 0.5

            emb2 = np.zeros(1024, dtype=np.float32)
            emb2[:600] = 1.0
            emb2[724:848] = 0.5

            for i in range(5):
                episode_id = store_episode(self.conn, f"msg1_{i}", f"reply{i}", emb1, i + 1)
                tm.assign(episode_id, emb1)
            for i in range(5):
                episode_id = store_episode(self.conn, f"msg2_{i}", f"reply{i}", emb2, i + 6)
                result = tm.assign(episode_id, emb2)

            assert result.consolidation is not None
            assert isinstance(result.consolidation, ConsolidationResult)
            assert result.consolidation.triggered_at_episode == 10
            assert tm.topic_count == result.consolidation.topics_after
        finally:
            self._teardown_db()

    def test_full_flow_dissimilar_topics_not_consolidated(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)

            emb1 = np.array([1.0] + [0.0] * 1023, dtype=np.float32)
            emb2 = np.array([0.0, 1.0] + [0.0] * 1022, dtype=np.float32)

            for i in range(5):
                episode_id = store_episode(self.conn, f"msg1_{i}", f"reply{i}", emb1, i + 1)
                tm.assign(episode_id, emb1)
            for i in range(5):
                episode_id = store_episode(self.conn, f"msg2_{i}", f"reply{i}", emb2, i + 6)
                result = tm.assign(episode_id, emb2)

            assert tm.topic_count == 2
            assert result.consolidation is not None
            assert result.consolidation.pairs_merged == 0
            assert result.consolidation.topics_before == 2
            assert result.consolidation.topics_after == 2
        finally:
            self._teardown_db()

    def test_multiple_consolidation_passes_across_30_episodes(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            consolidation_results = []

            for i in range(30):
                emb = _make_embedding(1.0)
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)
                if result.consolidation is not None:
                    consolidation_results.append(result.consolidation)

            assert len(consolidation_results) == 3
            assert consolidation_results[0].triggered_at_episode == 10
            assert consolidation_results[1].triggered_at_episode == 20
            assert consolidation_results[2].triggered_at_episode == 30
        finally:
            self._teardown_db()

    def test_reload_continues_consolidation_correctly(self):
        self._setup_db()
        try:
            tm = TopicManager(self.conn)
            emb = _make_embedding(1.0)

            for i in range(10):
                episode_id = store_episode(self.conn, f"msg{i}", f"reply{i}", emb, i + 1)
                result = tm.assign(episode_id, emb)

            assert result.consolidation is not None

            new_tm = TopicManager(self.conn)
            assert new_tm._episode_count == 10

            for i in range(10):
                episode_id = store_episode(self.conn, f"msg_r{i}", f"reply{i}", emb, i + 11)
                result = new_tm.assign(episode_id, emb)

            assert result.consolidation is not None
            assert result.consolidation.triggered_at_episode == 20
        finally:
            self._teardown_db()


class TestConsolidationTerminalOutput:
    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 10,
            "condition": "iterative",
            "user_message": "Test message",
            "k_episodes": [],
            "n_episodes": [],
            "topic_count": 2,
            "episode_count": 10,
            "estimated_tokens": 500,
            "k_token_estimate": 200,
            "n_token_estimate": 300,
            "stored_episode_id": "ep_12345678",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_consolidation_line_shown_when_occurred(self, capsys):
        consolidation = ConsolidationResult(
            triggered_at_episode=10,
            topics_before=4,
            topics_after=2,
            pairs_merged=2,
            merge_log=[
                {"surviving_label": "topic_1", "merged_label": "topic_3", "similarity": 0.68, "episodes_reassigned": 2},
                {"surviving_label": "topic_2", "merged_label": "topic_4", "similarity": 0.62, "episodes_reassigned": 1},
            ],
        )
        record = self._make_record(
            consolidation_occurred=True,
            consolidation_result=consolidation,
        )
        printer = TerminalPrinter()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" in out
        assert "Episode 10 trigger" in out
        assert "Topics: 4" in out
        assert "Merged: 2 pairs" in out
        assert "topic_3" in out
        assert "topic_1" in out
        assert "sim: 0.68" in out
        assert "2 episodes reassigned" in out

    def test_consolidation_no_pairs_line(self, capsys):
        consolidation = ConsolidationResult(
            triggered_at_episode=20,
            topics_before=2,
            topics_after=2,
            pairs_merged=0,
            merge_log=[],
        )
        record = self._make_record(
            consolidation_occurred=True,
            consolidation_result=consolidation,
            topic_count=2,
        )
        printer = TerminalPrinter()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" in out
        assert "No pairs above 0.60" in out
        assert "Topics unchanged: 2" in out

    def test_no_consolidation_line_when_not_occurred(self, capsys):
        record = self._make_record(
            consolidation_occurred=False,
            consolidation_result=None,
        )
        printer = TerminalPrinter()
        printer.print_turn(record)
        out = capsys.readouterr().out
        assert "[CONSOLIDATION]" not in out


class TestConsolidationFileWriter:
    def _setup(self):
        self.tmpdir = tempfile.mkdtemp()
        self.study_dir = self.tmpdir
        self.output_dir = os.path.join(self.tmpdir, "run_001_iterative")
        self.config = RunConfig(
            condition="iterative",
            run_id="run_001",
            output_dir=self.output_dir,
            study_dir=self.study_dir,
        )
        self.writer = FileWriter(self.config)
        self.writer.init_run()

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 10,
            "condition": "iterative",
            "user_message": "Test message",
            "k_episodes": [],
            "n_episodes": [],
            "topic_count": 2,
            "episode_count": 10,
            "estimated_tokens": 500,
            "k_token_estimate": 200,
            "n_token_estimate": 300,
            "stored_episode_id": "ep_12345678",
            "stored_topic_label": "topic_1",
            "constructed_prompt": "",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_consolidation_events_csv_created(self):
        self._setup()
        try:
            fpath = os.path.join(self.output_dir, "metrics", "consolidation_events.csv")
            assert os.path.isfile(fpath)

            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == [
                    "episode_count_at_trigger", "turn_number", "topics_before", "topics_after",
                    "pairs_merged", "surviving_labels", "merged_labels", "similarities", "episodes_reassigned"
                ]
        finally:
            self._teardown()

    def test_consolidation_events_csv_written_on_consolidation(self):
        self._setup()
        try:
            consolidation = ConsolidationResult(
                triggered_at_episode=10,
                topics_before=4,
                topics_after=2,
                pairs_merged=2,
                merge_log=[
                    {"surviving_label": "topic_1", "merged_label": "topic_3", "similarity": 0.68, "episodes_reassigned": 2},
                    {"surviving_label": "topic_2", "merged_label": "topic_4", "similarity": 0.62, "episodes_reassigned": 1},
                ],
            )
            record = self._make_record(
                consolidation_occurred=True,
                consolidation_result=consolidation,
            )
            self.writer.write_turn(record)

            fpath = os.path.join(self.output_dir, "metrics", "consolidation_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            row = reader[1]
            assert row[0] == "10"
            assert row[1] == "10"
            assert row[2] == "4"
            assert row[3] == "2"
            assert row[4] == "2"
        finally:
            self._teardown()

    def test_consolidation_events_csv_not_written_when_no_consolidation(self):
        self._setup()
        try:
            record = self._make_record(
                consolidation_occurred=False,
                consolidation_result=None,
            )
            self.writer.write_turn(record)

            fpath = os.path.join(self.output_dir, "metrics", "consolidation_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 1
        finally:
            self._teardown()

    def test_turns_jsonl_includes_consolidation_result(self):
        self._setup()
        try:
            consolidation = ConsolidationResult(
                triggered_at_episode=10,
                topics_before=3,
                topics_after=2,
                pairs_merged=1,
                merge_log=[
                    {"surviving_label": "topic_1", "merged_label": "topic_2", "similarity": 0.70, "episodes_reassigned": 3},
                ],
            )
            record = self._make_record(
                consolidation_occurred=True,
                consolidation_result=consolidation,
            )
            self.writer.write_turn(record)

            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert "consolidation_occurred" in data
            assert data["consolidation_occurred"] is True
            assert "consolidation_result" in data
            assert data["consolidation_result"]["topics_before"] == 3
            assert data["consolidation_result"]["topics_after"] == 2
        finally:
            self._teardown()

    def test_turns_jsonl_no_consolidation_when_none(self):
        self._setup()
        try:
            record = self._make_record(
                consolidation_occurred=False,
                consolidation_result=None,
            )
            self.writer.write_turn(record)

            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert "consolidation_occurred" in data
            assert data["consolidation_occurred"] is False
            assert "consolidation_result" not in data
        finally:
            self._teardown()
