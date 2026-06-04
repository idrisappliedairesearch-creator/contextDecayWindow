import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.study.script_loader import load_script
from src.runners.full_context_runner import FullContextRunner
from src.runners.compaction_runner import CompactionRunner
from src.runners.iterative_runner import IterativeRunner
from tests.conftest import MockInferenceProvider


def _create_mini_script(tmpdir: str) -> str:
    turns = [{"turn": i, "user": f"Question number {i}"} for i in range(1, 31)]
    script = {
        "study": "test_mini",
        "condition_note": "Mini script for testing",
        "system_prompt": "You are a test assistant.",
        "turns": turns,
    }
    path = os.path.join(tmpdir, "script.json")
    with open(path, "w") as f:
        json.dump(script, f)
    return path


class TestScriptLoader:

    def test_loads_valid_script(self):
        tmpdir = tempfile.mkdtemp()
        path = _create_mini_script(tmpdir)
        script = load_script(path)
        assert script["study"] == "test_mini"
        assert len(script["turns"]) == 30
        assert script["system_prompt"] == "You are a test assistant."

    def test_raises_missing_system_prompt(self):
        tmpdir = tempfile.mkdtemp()
        script = {"turns": [{"turn": 1, "user": "Hello"}]}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "system_prompt" in str(e)

    def test_raises_empty_system_prompt(self):
        tmpdir = tempfile.mkdtemp()
        script = {"system_prompt": "", "turns": [{"turn": 1, "user": "Hello"}]}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "system_prompt" in str(e)

    def test_raises_missing_turns(self):
        tmpdir = tempfile.mkdtemp()
        script = {"system_prompt": "Hello"}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "turns" in str(e)

    def test_raises_too_few_turns(self):
        tmpdir = tempfile.mkdtemp()
        script = {"system_prompt": "Hello", "turns": [{"turn": 1, "user": "Hi"}]}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "30" in str(e)

    def test_raises_non_sequential_turns(self):
        tmpdir = tempfile.mkdtemp()
        turns = [{"turn": i, "user": f"Msg {i}"} for i in range(30)]
        turns.insert(1, {"turn": 1.5, "user": "Extra"})
        script = {"system_prompt": "Hello", "turns": turns}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "sequential" in str(e).lower() or "Expected" in str(e)

    def test_raises_missing_turn_key(self):
        tmpdir = tempfile.mkdtemp()
        turns = [{"user": f"Msg {i}"} for i in range(1, 31)]
        script = {"system_prompt": "Hello", "turns": turns}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "turn" in str(e)

    def test_raises_missing_user_key(self):
        tmpdir = tempfile.mkdtemp()
        turns = [{"turn": i} for i in range(1, 31)]
        script = {"system_prompt": "Hello", "turns": turns}
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump(script, f)
        try:
            load_script(path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "user" in str(e)


class TestFullContextRunnerWithMock:

    def setup_method(self):
        self.runner = FullContextRunner("System prompt.")

    def test_three_turn_sequence(self):
        for i in range(1, 4):
            prompt, record = self.runner.build_context(f"Q{i}", i)
            assert record.turn_number == i
            assert record.condition == "full_context"
            self.runner.on_turn_complete(f"Q{i}", f"A{i}", i)
        assert len(self.runner._history) == 3


class TestCompactionRunnerWithMock:

    def setup_method(self):
        self.runner = CompactionRunner("System prompt.", inference_provider=MockInferenceProvider())

    def test_compaction_produces_mock_summary(self):
        long = "X" * 6000
        self.runner.on_turn_complete(long, long, 1)
        _, record = self.runner.build_context("Next", 2)
        assert record.compaction_occurred is True
        assert self.runner._summary == "Mock assistant response."


class TestIterativeRunnerWithMock:

    def setup_method(self):
        import tempfile
        import numpy as np
        from src.db.schema import init_db
        from src.memory.topic_manager import TopicManager
        from src.memory.retrieval_engine import RetrievalEngine

        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.conn = init_db(self.db_path)

        class MockEp:
            def embed(self, text):
                vec = np.zeros(1024, dtype=np.float32)
                vec[0] = 1.0
                return vec

        self.mock_ep = MockEp()
        self.topic_manager = TopicManager(self.conn)
        self.retrieval_engine = RetrievalEngine(self.conn)
        self.runner = IterativeRunner(
            self.conn, self.mock_ep, self.topic_manager, self.retrieval_engine
        )

    def test_three_turn_sequence(self):
        for i in range(1, 4):
            prompt, record = self.runner.build_context(f"Q{i}", i)
            assert record.turn_number == i
            assert record.condition == "iterative"

            embedding = self.mock_ep.embed(f"User: Q{i}\nAssistant: A{i}")
            assignment = self.runner.on_turn_complete(f"Q{i}", f"A{i}", i, embedding)
            assert assignment is not None


class TestStudyRunnerEnvCheck:

    def test_raises_when_inference_model_not_set(self):
        saved = os.environ.pop("CDW_INFERENCE_MODEL_PATH", None)
        try:
            try:
                from src.study.runner import StudyRunner
                StudyRunner(
                    script_path="nonexistent.json",
                    study_dir="/tmp/test",
                )
                assert False, "Should have raised EnvironmentError"
            except EnvironmentError as e:
                assert "CDW_INFERENCE_MODEL_PATH" in str(e)
            except FileNotFoundError:
                pass
        finally:
            if saved is not None:
                os.environ["CDW_INFERENCE_MODEL_PATH"] = saved
