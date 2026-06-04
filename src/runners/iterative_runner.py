import sqlite3
import numpy as np

from src.db.episode import store_episode
from src.memory.retrieval_engine import RetrievalEngine
from src.memory.topic_manager import TopicManager
from src.memory.context_builder import build_prompt, estimate_tokens
from src.observability.turn_record import TurnRecord, AssignmentResult
from src.runners.base_runner import BaseRunner


class IterativeRunner(BaseRunner):

    condition = "iterative"

    def __init__(
        self,
        conn: sqlite3.Connection,
        embedding_provider,
        topic_manager: TopicManager,
        retrieval_engine: RetrievalEngine,
        observer=None,
    ):
        self._conn = conn
        self._embedding_provider = embedding_provider
        self._topic_manager = topic_manager
        self._retrieval_engine = retrieval_engine
        self._observer = observer

    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        retrieval_result = self._retrieval_engine.retrieve(user_message, turn_number)

        episodes_for_prompt = []
        for ep in retrieval_result.episodes:
            episodes_for_prompt.append({
                "turn_number": ep["turn_number"],
                "user_message": ep["user_message"],
                "assistant_message": ep["assistant_message"],
            })

        system_prompt = "You are a helpful assistant."
        constructed_prompt = build_prompt(episodes_for_prompt, system_prompt)

        k_episodes = []
        n_episodes = []

        k_set = set(retrieval_result.k_episode_ids)
        n_set = set(retrieval_result.n_episode_ids)

        for ep in retrieval_result.episodes:
            ep_id = ep["id"]
            sim_score = retrieval_result.k_scores.get(ep_id, 0.0)
            decay_score = retrieval_result.n_scores.get(ep_id, 0.0)

            ep_dict = {
                "id": ep_id,
                "turn_number": ep["turn_number"],
                "user_message": ep["user_message"],
                "assistant_message": ep["assistant_message"],
                "sim_score": sim_score,
                "decay_score": decay_score,
                "topic_label": ep.get("topic_id", ""),
                "retrieval_type": "KN" if (ep_id in k_set and ep_id in n_set) else ("K" if ep_id in k_set else "N"),
            }

            if ep_id in k_set:
                k_episodes.append(ep_dict)
            if ep_id in n_set and ep_id not in k_set:
                n_episodes.append(ep_dict)

        k_token_estimate = 0
        n_token_estimate = 0
        for ep in k_episodes:
            k_token_estimate += estimate_tokens(f"User: {ep['user_message']}\nAssistant: {ep['assistant_message']}")
        for ep in n_episodes:
            n_token_estimate += estimate_tokens(f"User: {ep['user_message']}\nAssistant: {ep['assistant_message']}")

        record = TurnRecord(
            turn_number=turn_number,
            condition=self.condition,
            user_message=user_message,
            k_count=retrieval_result.k_count,
            n_count=retrieval_result.n_count,
            total_in_context=retrieval_result.total_episodes_in_context,
            k_episodes=k_episodes,
            n_episodes=n_episodes,
            estimated_tokens=retrieval_result.estimated_tokens,
            k_token_estimate=k_token_estimate,
            n_token_estimate=n_token_estimate,
            topic_count=self._topic_manager.topic_count,
            episode_count=retrieval_result.total_episodes_in_context,
            constructed_prompt=constructed_prompt,
        )

        return (constructed_prompt, record)

    def on_turn_complete(
        self,
        user_message: str,
        assistant_message: str,
        turn_number: int,
        embedding: np.ndarray = None,
    ) -> AssignmentResult:
        if embedding is None:
            pair_text = f"User: {user_message}\nAssistant: {assistant_message}"
            embedding = self._embedding_provider.embed(pair_text)

        episode_id = store_episode(
            self._conn,
            user_message,
            assistant_message,
            embedding,
            turn_number,
        )

        assignment = self._topic_manager.assign(episode_id, embedding)

        return assignment

    @property
    def history_token_estimate(self) -> int:
        return 0
