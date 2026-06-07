import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability.run_config import RunConfig
from src.observability.observer import Observer
from src.observability.turn_record import TurnRecord


class TestObserverInitRun:

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
        self.observer = Observer(self.config)

    def _teardown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_run_creates_directory_structure(self):
        self._setup()
        try:
            self.observer.init_run()
            assert os.path.isdir(self.output_dir)
            assert os.path.isdir(os.path.join(self.output_dir, "logs"))
            assert os.path.isdir(os.path.join(self.output_dir, "metrics"))
            assert os.path.isdir(os.path.join(self.output_dir, "snapshots"))
            assert os.path.isdir(os.path.join(self.output_dir, "rubric"))
            assert os.path.isdir(os.path.join(self.output_dir, "constructed_prompts"))
        finally:
            self._teardown()

    def test_init_run_creates_jsonl_files(self):
        self._setup()
        try:
            self.observer.init_run()
            for fname in ["turns.jsonl", "retrieval.jsonl", "context_windows.jsonl", "context_diffs.jsonl"]:
                assert os.path.isfile(os.path.join(self.output_dir, "logs", fname))
        finally:
            self._teardown()

    def test_init_run_creates_csv_files(self):
        self._setup()
        try:
            self.observer.init_run()
            for fname in [
                "model_performance.csv", "memory_store.csv", "K_values.csv",
                "N_values.csv", "topic_events.csv", "retrieval_events.csv",
            ]:
                assert os.path.isfile(os.path.join(self.output_dir, "metrics", fname))
        finally:
            self._teardown()

    def test_init_run_creates_rubric_placeholders(self):
        self._setup()
        try:
            self.observer.init_run()
            assert os.path.isfile(os.path.join(self.output_dir, "rubric", "responses.md"))
            assert os.path.isfile(os.path.join(self.output_dir, "rubric", "scores.md"))
        finally:
            self._teardown()


class TestObserverFlushTurn:

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
        self.observer = Observer(self.config)
        self.observer.init_run()

    def _teardown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_record(self, **overrides):
        defaults = {
            "turn_number": 1,
            "condition": "iterative",
            "user_message": "Hello, what is the budget cap?",
            "k_count": 2,
            "n_count": 3,
            "total_in_context": 3,
            "k_episodes": [
                {"id": "ep_a001", "sim_score": 0.85, "decay_score": 0.9, "topic_label": "topic_1"},
                {"id": "ep_b002", "sim_score": 0.72, "decay_score": 0.8, "topic_label": "topic_2"},
            ],
            "n_episodes": [
                {"id": "ep_a001", "decay_score": 0.9, "topic_label": "topic_1"},
                {"id": "ep_b002", "decay_score": 0.8, "topic_label": "topic_2"},
                {"id": "ep_c003", "decay_score": 0.5, "topic_label": "topic_1"},
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
            "assistant_message": "The budget cap is $47,500.",
            "stored_episode_id": "ep_d004",
            "stored_topic_label": "topic_1",
            "previous_context_window": None,
            "constructed_prompt": "You are a helpful assistant.\n--- RETRIEVED CONVERSATION HISTORY ---",
        }
        defaults.update(overrides)
        return TurnRecord(**defaults)

    def test_flush_turn_prints_to_terminal(self, capsys):
        self._setup()
        try:
            record = self._make_record()
            self.observer.flush_turn(record)
            out = capsys.readouterr().out
            assert "TURN 001" in out
            assert "[USER]" in out
            assert "[RETRIEVAL]" in out
            assert "[TOPIC LAYER]" in out
        finally:
            self._teardown()

    def test_flush_turn_writes_all_files(self):
        self._setup()
        try:
            record = self._make_record()
            self.observer.flush_turn(record)

            assert os.path.isfile(os.path.join(self.output_dir, "logs", "turns.jsonl"))
            assert os.path.isfile(os.path.join(self.output_dir, "logs", "retrieval.jsonl"))
            assert os.path.isfile(os.path.join(self.output_dir, "logs", "context_windows.jsonl"))
            assert os.path.isfile(os.path.join(self.output_dir, "logs", "context_diffs.jsonl"))

            assert os.path.isfile(os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json"))
            assert os.path.isfile(os.path.join(self.output_dir, "constructed_prompts", "turn_001.txt"))
        finally:
            self._teardown()

    def test_flush_turn_fully_populated_record(self, capsys):
        self._setup()
        try:
            record = self._make_record()
            self.observer.flush_turn(record)
            out = capsys.readouterr().out

            assert "50.0 tok/s" in out
            assert "~TTFT: 0.25s" in out
            assert "Output: 150 tokens" in out
            assert "[ASSISTANT] The budget cap is $47,500." in out
        finally:
            self._teardown()

    def test_flush_turn_partial_record_generation_none(self, capsys):
        self._setup()
        try:
            record = self._make_record(
                tokens_per_second=None,
                time_to_first_token=None,
                output_tokens=None,
                assistant_message=None,
                stored_episode_id=None,
                stored_topic_label=None,
            )
            self.observer.flush_turn(record)
            out = capsys.readouterr().out
            assert "---" in out
        finally:
            self._teardown()

    def test_flush_turn_new_topic_created(self, capsys):
        self._setup()
        try:
            record = self._make_record(
                new_topic_created=True,
                new_topic_label="topic_3",
                topic_count=3,
            )
            self.observer.flush_turn(record)
            out = capsys.readouterr().out
            assert "New node: Yes" in out
        finally:
            self._teardown()

    def test_flush_turn_multiple_turns(self):
        self._setup()
        try:
            self.observer.flush_turn(self._make_record(turn_number=1))
            self.observer.flush_turn(self._make_record(turn_number=2, previous_context_window="prev prompt"))

            fpath = os.path.join(self.output_dir, "logs", "turns.jsonl")
            with open(fpath) as f:
                lines = f.readlines()
            assert len(lines) == 2

            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            assert data1["turn_number"] == 1
            assert data2["turn_number"] == 2
        finally:
            self._teardown()

    def test_flush_turn_constructed_prompt_saved(self):
        self._setup()
        try:
            prompt_text = "Custom prompt for turn 1."
            record = self._make_record(constructed_prompt=prompt_text)
            self.observer.flush_turn(record)

            fpath = os.path.join(self.output_dir, "constructed_prompts", "turn_001.txt")
            with open(fpath) as f:
                saved = f.read()
            assert saved == prompt_text
        finally:
            self._teardown()

    def test_flush_turn_snapshot_has_no_raw_vectors(self):
        self._setup()
        try:
            record = self._make_record()
            self.observer.flush_turn(record)

            fpath = os.path.join(self.output_dir, "snapshots", "turn_001_db_state.json")
            with open(fpath) as f:
                content = f.read()
            assert "embedding_dim" in content
            assert "centroid_dim" in content
        finally:
            self._teardown()
