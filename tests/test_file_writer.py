import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability.run_config import RunConfig
from src.observability.file_writer import FileWriter
from src.observability.turn_record import TurnRecord


class TestFileWriterInitRun:

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

    def test_creates_output_directory(self):
        self._setup()
        try:
            self.writer.init_run()
            assert os.path.isdir(self.output_dir)
        finally:
            self._teardown()

    def test_creates_logs_subdirectory(self):
        self._setup()
        try:
            self.writer.init_run()
            assert os.path.isdir(os.path.join(self.output_dir, "logs"))
        finally:
            self._teardown()

    def test_creates_metrics_subdirectory(self):
        self._setup()
        try:
            self.writer.init_run()
            assert os.path.isdir(os.path.join(self.output_dir, "metrics"))
        finally:
            self._teardown()

    def test_creates_snapshots_subdirectory(self):
        self._setup()
        try:
            self.writer.init_run()
            assert os.path.isdir(os.path.join(self.output_dir, "snapshots"))
        finally:
            self._teardown()

    def test_creates_rubric_subdirectory(self):
        self._setup()
        try:
            self.writer.init_run()
            assert os.path.isdir(os.path.join(self.output_dir, "rubric"))
        finally:
            self._teardown()

    def test_creates_constructed_prompts_subdirectory(self):
        self._setup()
        try:
            self.writer.init_run()
            assert os.path.isdir(os.path.join(self.output_dir, "constructed_prompts"))
        finally:
            self._teardown()

    def test_creates_jsonl_log_files(self):
        self._setup()
        try:
            self.writer.init_run()
            for fname in ["turns.jsonl", "retrieval.jsonl", "context_windows.jsonl", "context_diffs.jsonl"]:
                fpath = os.path.join(self.output_dir, "logs", fname)
                assert os.path.isfile(fpath)
                assert os.path.getsize(fpath) == 0
        finally:
            self._teardown()

    def test_creates_csv_files(self):
        self._setup()
        try:
            self.writer.init_run()
            for fname in [
                "model_performance.csv", "memory_store.csv", "K_values.csv",
                "N_values.csv", "topic_events.csv", "retrieval_events.csv",
            ]:
                assert os.path.isfile(os.path.join(self.output_dir, "metrics", fname))
        finally:
            self._teardown()

    def test_csv_model_performance_headers(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "model_performance.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["turn", "tokens_per_second", "time_to_first_token", "output_tokens", "estimated_tokens"]
        finally:
            self._teardown()

    def test_csv_memory_store_headers(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "memory_store.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["turn", "topic_count", "episode_count", "new_topic_created", "new_topic_label", "compaction_occurred", "compaction_turn"]
        finally:
            self._teardown()

    def test_csv_k_values_headers(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "K_values.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["turn", "k_count", "episode_id", "similarity_score", "topic_label", "k_only"]
        finally:
            self._teardown()

    def test_csv_n_values_headers(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "N_values.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["turn", "n_count", "episode_id", "decay_score", "topic_label", "n_total_in_store"]
        finally:
            self._teardown()

    def test_csv_topic_events_headers(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "topic_events.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["turn", "event_type", "topic_label", "centroid_drift"]
        finally:
            self._teardown()

    def test_csv_retrieval_events_headers(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "metrics", "retrieval_events.csv")
            with open(fpath) as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["turn", "episode_id", "similarity_score", "decay_score", "retrieval_type"]
        finally:
            self._teardown()

    def test_creates_rubric_responses_md(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "rubric", "responses.md")
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                content = f.read()
            assert "# Responses" in content
        finally:
            self._teardown()

    def test_creates_rubric_scores_md(self):
        self._setup()
        try:
            self.writer.init_run()
            fpath = os.path.join(self.output_dir, "rubric", "scores.md")
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                content = f.read()
            assert "# Scores" in content
        finally:
            self._teardown()


class TestFileWriterWriteTurn:

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
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "iterative",
            "user_message": "Test message",
            "k_count": 2,
            "n_count": 3,
            "total_in_context": 3,
            "k_episodes": [
                {"id": "ep_k001", "sim_score": 0.85, "decay_score": 0.9, "topic_label": "topic_1"},
                {"id": "ep_k002", "sim_score": 0.72, "decay_score": 0.8, "topic_label": "topic_2"},
            ],
            "n_episodes": [
                {"id": "ep_k001", "decay_score": 0.9, "topic_label": "topic_1"},
                {"id": "ep_k002", "decay_score": 0.8, "topic_label": "topic_2"},
                {"id": "ep_n003", "decay_score": 0.5, "topic_label": "topic_1"},
            ],
            "estimated_tokens": 500,
            "k_token_estimate": 200,
            "n_token_estimate": 300,
            "topic_count": 2,
            "episode_count": 5,
            "new_topic_created": False,
            "new_topic_label": None,
            "centroid_drift": {"topic_1": 0.015},
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

    def test_turns_jsonl_receives_record(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["turn_number"] == 1
            assert data["condition"] == "iterative"
            assert data["user_message"] == "Test message"
        finally:
            self._teardown()

    def test_turns_jsonl_excludes_constructed_prompt(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert "constructed_prompt" not in data
            assert "constructed_prompt_path" in data
        finally:
            self._teardown()

    def test_retrieval_jsonl_receives_k_and_n_data(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "retrieval.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert data["k_count"] == 2
            assert data["n_count"] == 3
            assert len(data["k_episodes"]) == 2
            assert len(data["n_episodes"]) == 3
        finally:
            self._teardown()

    def test_context_windows_jsonl_written(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "context_windows.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert data["turn_number"] == 1
            assert data["estimated_tokens"] == 500
        finally:
            self._teardown()

    def test_context_diffs_first_turn_no_diff(self):
        self._setup()
        try:
            record = self._make_record(previous_context_window=None)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "context_diffs.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert data["turn"] == 1
            assert "first turn, no diff" in data["note"]
        finally:
            self._teardown()

    def test_context_diffs_computes_diff(self):
        self._setup()
        try:
            old_prompt = "System\nLine A\nLine B"
            new_prompt = "System\nLine A\nLine C\nLine D"
            record = self._make_record(
                previous_context_window=old_prompt,
                constructed_prompt=new_prompt,
            )
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "logs", "context_diffs.jsonl")
            with open(fpath) as f:
                data = json.loads(f.read().strip())
            assert data["turn_number"] == 1
            assert data["lines_added"] > 0
            assert data["lines_removed"] > 0
        finally:
            self._teardown()

    def test_model_performance_csv_written(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "model_performance.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            row = reader[1]
            assert row[0] == "1"
            assert float(row[1]) == 50.0
            assert float(row[2]) == 0.25
            assert int(row[3]) == 150
        finally:
            self._teardown()

    def test_model_performance_csv_none_as_dash(self):
        self._setup()
        try:
            record = self._make_record(
                tokens_per_second=None,
                time_to_first_token=None,
                output_tokens=None,
            )
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "model_performance.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            row = reader[1]
            assert row[1] == "---"
            assert row[2] == "---"
            assert row[3] == "---"
        finally:
            self._teardown()

    def test_memory_store_csv_written(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "memory_store.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            row = reader[1]
            assert row[0] == "1"
            assert row[1] == "2"
            assert row[2] == "5"
            assert row[5] == "False"
            assert row[6] == "---"
        finally:
            self._teardown()

    def test_k_values_csv_one_row_per_k_match(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "K_values.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 3
            assert reader[1][1] == "2"
            assert reader[2][1] == "2"
        finally:
            self._teardown()

    def test_n_values_csv_one_row_per_episode(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "N_values.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 4
        finally:
            self._teardown()

    def test_topic_events_new_node(self):
        self._setup()
        try:
            record = self._make_record(
                new_topic_created=True,
                new_topic_label="topic_3",
                centroid_drift={},
            )
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "topic_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            assert reader[1][1] == "new_node"
            assert reader[1][2] == "topic_3"
        finally:
            self._teardown()

    def test_topic_events_centroid_update(self):
        self._setup()
        try:
            record = self._make_record(
                new_topic_created=False,
                new_topic_label=None,
                centroid_drift={"topic_1": 0.025},
            )
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "topic_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 2
            assert reader[1][1] == "centroid_update"
            assert reader[1][2] == "topic_1"
            assert float(reader[1][3]) == 0.025
        finally:
            self._teardown()

    def test_retrieval_events_csv_written(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "metrics", "retrieval_events.csv")
            with open(fpath) as f:
                reader = list(csv.reader(f))
            assert len(reader) == 3
        finally:
            self._teardown()

    def test_snapshot_created(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json")
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                data = json.load(f)
            assert data["turn_number"] == 1
            assert data["topic_count"] == 2
        finally:
            self._teardown()

    def test_snapshot_excludes_raw_vectors(self):
        self._setup()
        try:
            record = self._make_record()
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json")
            with open(fpath) as f:
                content = f.read()
            assert "embedding_dim" in content
            assert "centroid_dim" in content
        finally:
            self._teardown()

    def test_constructed_prompt_saved(self):
        self._setup()
        try:
            prompt = "Exact prompt text here."
            record = self._make_record(constructed_prompt=prompt)
            self.writer.write_turn(record)
            fpath = os.path.join(self.output_dir, "constructed_prompts", "turn_001.txt")
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                assert f.read() == prompt
        finally:
            self._teardown()

    def test_turn_number_zero_padded(self):
        self._setup()
        try:
            record = self._make_record(turn_number=5)
            self.writer.write_turn(record)
            assert os.path.isfile(os.path.join(self.output_dir, "constructed_prompts", "turn_005.txt"))
            assert os.path.isfile(os.path.join(self.output_dir, "snapshots", "turn_005_db_state.json"))
        finally:
            self._teardown()

    def test_multiple_turns_append(self):
        self._setup()
        try:
            self.writer.write_turn(self._make_record(turn_number=1))
            self.writer.write_turn(self._make_record(turn_number=2))
            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                lines = f.readlines()
            assert len(lines) == 2
        finally:
            self._teardown()
