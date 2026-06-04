import os

import numpy as np

from src.db.schema import init_db
from src.embeddings.provider import embed
from src.inference.provider import InferenceProvider
from src.memory.retrieval_engine import RetrievalEngine
from src.memory.topic_manager import TopicManager
from src.observability.observer import Observer
from src.observability.run_config import RunConfig
from src.observability.turn_record import TurnRecord
from src.runners.compaction_runner import CompactionRunner
from src.runners.full_context_runner import FullContextRunner
from src.runners.iterative_runner import IterativeRunner
from src.study.script_loader import load_script


class StudyRunner:

    CONDITION_ORDER = ["full_context", "compaction", "iterative"]
    RUBRIC_TURN_START = 25
    RUBRIC_TURN_END = 32

    def __init__(self, script_path: str, study_dir: str, run_id: str = "run_001"):
        self._check_env_vars()
        self.script = load_script(script_path)
        self.system_prompt = self.script["system_prompt"]
        self.turns = self.script["turns"]
        self.study_dir = study_dir
        self.run_id = run_id
        self._inference_provider = InferenceProvider()
        self._rubric_data = {}

    def _check_env_vars(self):
        required = [
            "CDW_INFERENCE_MODEL_PATH",
            "CDW_EMBEDDING_MODEL_PATH",
        ]
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"All five environment variables must be set before running the study."
            )

    def run(self) -> None:
        for condition in self.CONDITION_ORDER:
            self._run_condition(condition)

    def _run_condition(self, condition: str) -> None:
        output_dir = os.path.join(self.study_dir, self.run_id, condition)
        run_config = RunConfig(
            condition=condition,
            run_id=self.run_id,
            output_dir=output_dir,
            study_dir=self.study_dir,
        )

        observer = Observer(run_config)
        observer.init_run()

        runner = self._create_runner(condition, run_config, observer)
        previous_prompt = None
        rubric_responses = []

        for turn_data in self.turns:
            turn_number = turn_data["turn"]
            user_message = turn_data["user"]

            constructed_prompt, record = runner.build_context(user_message, turn_number)

            if condition == "iterative":
                full_prompt = f"{constructed_prompt}\n\nUser: {user_message}\nAssistant:"
            else:
                full_prompt = constructed_prompt

            record.constructed_prompt = full_prompt
            record.previous_context_window = previous_prompt

            result = self._inference_provider.complete(full_prompt)
            assistant_message = result.assistant_message

            record.tokens_per_second = result.tokens_per_second
            record.time_to_first_token = result.time_to_first_token
            record.output_tokens = result.output_tokens
            record.assistant_message = assistant_message

            if self.RUBRIC_TURN_START <= turn_number <= self.RUBRIC_TURN_END:
                rubric_responses.append({
                    "turn_number": turn_number,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                })

            if condition == "iterative":
                pair_text = f"User: {user_message}\nAssistant: {assistant_message}"
                embedding = embed(pair_text)
                assignment = runner.on_turn_complete(user_message, assistant_message, turn_number, embedding)
                record.stored_episode_id = assignment.topic_id
                record.stored_topic_label = assignment.topic_label
                record.new_topic_created = assignment.is_new_topic
                record.new_topic_label = assignment.topic_label if assignment.is_new_topic else None
                record.centroid_drift = {assignment.topic_label: assignment.centroid_drift}
                record.topic_count = runner._topic_manager.topic_count
                record.episode_count = runner._topic_manager.topic_count
            else:
                runner.on_turn_complete(user_message, assistant_message, turn_number)

            observer.flush_turn(record)
            previous_prompt = full_prompt

        if rubric_responses:
            self._write_rubric_responses(condition, rubric_responses)

    def _create_runner(self, condition: str, run_config: RunConfig, observer) -> object:
        if condition == "full_context":
            return FullContextRunner(self.system_prompt)
        elif condition == "compaction":
            return CompactionRunner(self.system_prompt, inference_provider=self._inference_provider)
        elif condition == "iterative":
            db_path = os.path.join(run_config.output_dir, "study.db")
            conn = init_db(db_path)
            topic_manager = TopicManager(conn)
            retrieval_engine = RetrievalEngine(conn)
            return IterativeRunner(conn, embed, topic_manager, retrieval_engine, observer)
        else:
            raise ValueError(f"Unknown condition: {condition}")

    def _write_rubric_responses(self, condition: str, rubric_responses: list) -> None:
        rubric_dir = os.path.join(self.study_dir, self.run_id, condition, "rubric")
        os.makedirs(rubric_dir, exist_ok=True)

        rubric_path = os.path.join(rubric_dir, "responses.md")
        with open(rubric_path, "w", encoding="utf-8") as f:
            f.write(f"# Rubric Responses — {condition}\n")
            f.write(f"**Run:** {self.run_id}\n")
            f.write(f"**Condition:** {condition}\n")
            f.write(f"**Scored by:** [TO BE FILLED — Sprint 009]\n")
            f.write(f"\n---\n")

            question_labels = {
                25: "Q1: Budget Cap",
                26: "Q4: Lead Engineer + Deadline",
                27: "Q7: Formatting Rules",
                28: "Q10: CRISPR Cell Line + Expression Rate",
                29: "Q13: CRISPR Dosage",
                30: "Q16: Performance Target",
                31: "Q19: Researcher Identity",
                32: "Q22: All Numerical Values",
            }

            for resp in rubric_responses:
                turn_num = resp["turn_number"]
                label = question_labels.get(turn_num, f"Turn {turn_num}")
                f.write(f"\n## Turn {turn_num} — {label}\n\n")
                f.write(f"**User:** {resp['user_message']}\n\n")
                f.write(f"**Assistant response:**\n{resp['assistant_message']}\n\n")
                f.write(f"**Score:** [  ] (1.0 / 0.5 / 0.0)\n")
                f.write(f"**Notes:**\n\n")
                f.write(f"---\n")
