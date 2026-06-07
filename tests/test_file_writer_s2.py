import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability.run_config import RunConfig
from src.observability.file_writer import FileWriter
from src.observability.turn_record import TurnRecord, ConsolidationResult


class TestFileWriterS2Setup:

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

    def _teardown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "iterative",
            "user_message": "Test message",
            "contains_rule": False,
            "rule_summary": None,
            "rule_store_count": 2,
            "rule_token_estimate": 500,
            "k_count": 2,
            "n_count": 3,
            "n_total_in_store": 15,
            "k_only_count": 1,
            "total_in_context": 4,
            "k_episodes": [
                {"id": "ep_k001", "sim_score": 0.85, "decay_score": 0.9, "topic_label": "topic_1", "retrieval_type": "K"},
                {"id": "ep_kn002", "sim_score": 0.72, "decay_score": 0.8, "topic_label": "topic_2", "retrieval_type": "KN"},
            ],
            "n_episodes": [
                {"id": "ep_n001", "decay_score": 0.9, "topic_label": "topic_1", "retrieval_type": "N"},
                {"id": "ep_n002", "decay_score": 0.8, "topic_label": "topic_2", "retrieval_type": "N"},
                {"id": "ep_n003", "decay_score": 0.5, "topic_label": "topic_1", "retrieval_type": "N"},
            ],
            "estimated_tokens": 500,
            "k_token_estimate": 200,
            "n_token_estimate": 300,
            "topic_count": 2,
            "episode_count": 5,
            "new_topic_created": False,
            "new_topic_label": None,
            "centroid_drift": {"topic_1": 0.015},
            "consolidation_occurred": False,
            "consolidation_result": None,
            "tokens_per_second": 50.0,
            "time_to_first_token": 0.25,
            "output_tokens": 150,
            "assistant_message": "Response text",
            "stored_episode_id": "ep_s001",
            "stored_topic_label": "topic_1",
            "previous_context_window": None,
            "constructed_prompt": "System prompt\n--- HISTORY ---",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)


class TestFileWriterS2CSVColumns(TestFileWriterS2Setup):

    def test_k_values_csv_has_k_only_column(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "K_values.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
            assert "k_only" in headers
        finally:
            self._teardown()

    def test_n_values_csv_has_n_total_in_store_column(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "N_values.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
            assert "n_total_in_store" in headers
        finally:
            self._teardown()

    def test_rule_detection_csv_present(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "rule_detection.csv")
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
            assert "turn_number" in headers
            assert "contains_rule_detected" in headers
        finally:
            self._teardown()

    def test_consolidation_events_csv_present(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "consolidation_events.csv")
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
            assert "turn_number" in headers
            assert "topics_before" in headers
            assert "topics_after" in headers
            assert "pairs_merged" in headers
        finally:
            self._teardown()

    def test_all_eight_csv_files_created(self):
        self._setup()
        try:
            self.writer.init_run()
            expected = [
                "model_performance.csv",
                "memory_store.csv",
                "K_values.csv",
                "N_values.csv",
                "topic_events.csv",
                "retrieval_events.csv",
                "rule_detection.csv",
                "consolidation_events.csv",
            ]
            for fname in expected:
                fpath = os.path.join(self.output_dir, "metrics", fname)
                assert os.path.isfile(fpath), f"Missing CSV: {fname}"
        finally:
            self._teardown()


class TestFileWriterS2TurnFields(TestFileWriterS2Setup):

    def test_turns_jsonl_includes_k_only_count(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(k_only_count=3)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert data["k_only_count"] == 3
        finally:
            self._teardown()

    def test_turns_jsonl_includes_rule_fields(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(
                contains_rule=True,
                rule_summary="Budget cap",
                rule_store_count=2,
                rule_token_estimate=500,
            )
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert data["contains_rule"] is True
            assert data["rule_summary"] == "Budget cap"
            assert data["rule_store_count"] == 2
            assert data["rule_token_estimate"] == 500
        finally:
            self._teardown()

    def test_rule_detection_csv_populated(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(contains_rule=True, rule_summary="Formatting rules")
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "rule_detection.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            assert reader[1][0] == "1"
            assert reader[1][1] == "True"
            assert reader[1][2] == "Formatting rules"
        finally:
            self._teardown()

    def test_consolidation_csv_populated(self):
        self._setup()
        try:
            self.writer.init_run()
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
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "consolidation_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            assert reader[1][2] == "5"
            assert reader[1][3] == "4"
            assert reader[1][4] == "1"
        finally:
            self._teardown()

    def test_consolidation_csv_not_written_when_no_consolidation(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(consolidation_occurred=False, consolidation_result=None)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "consolidation_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 1
        finally:
            self._teardown()


class TestFileWriterS2Snapshots(TestFileWriterS2Setup):

    def test_snapshot_includes_rule_store_count(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(rule_store_count=3)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json")
            with open(fpath) as f:
                data = json.load(f)
            assert "rule_store_count" in data
            assert data["rule_store_count"] == 3
        finally:
            self._teardown()

    def test_snapshot_includes_topic_consolidation_count(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(consolidation_occurred=True)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json")
            with open(fpath) as f:
                data = json.load(f)
            assert "topic_consolidation_count" in data
            assert data["topic_consolidation_count"] == 1
        finally:
            self._teardown()

    def test_snapshot_consolidation_count_zero_when_no_consolidation(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(consolidation_occurred=False)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json")
            with open(fpath) as f:
                data = json.load(f)
            assert data["topic_consolidation_count"] == 0
        finally:
            self._teardown()


class TestFileWriterS2KValuesKOnly(TestFileWriterS2Setup):

    def test_k_only_true_for_k_type_episodes(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(k_episodes=[
                {"id": "ep_k001", "sim_score": 0.8, "decay_score": 0.9, "topic_label": "topic_1", "retrieval_type": "K"},
            ])
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "K_values.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            assert reader[1][5] == "True"
        finally:
            self._teardown()

    def test_k_only_false_for_kn_type_episodes(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(k_episodes=[
                {"id": "ep_kn001", "sim_score": 0.8, "decay_score": 0.9, "topic_label": "topic_1", "retrieval_type": "KN"},
            ])
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "K_values.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            assert reader[1][5] == "False"
        finally:
            self._teardown()


class TestFileWriterS2NValuesTotalInStore(TestFileWriterS2Setup):

    def test_n_total_in_store_written_per_row(self):
        self._setup()
        try:
            self.writer.init_run()
            record = self._make_record(n_total_in_store=47)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "N_values.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 4
            for row in reader[1:]:
                assert row[5] == "47"
        finally:
            self._teardown()
