import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from src.embeddings.provider import embed, cosine_similarity
from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    update_retrieval_metadata,
    log_retrieval_events_batch,
)
from src.memory.context_builder import build_prompt, estimate_tokens


DECAY_RATE = 0.1
K_SIMILARITY_THRESHOLD = 0.70


@dataclass
class RetrievalResult:
    episodes: list = field(default_factory=list)
    k_episode_ids: list = field(default_factory=list)
    k_scores: dict = field(default_factory=dict)
    n_episode_ids: list = field(default_factory=list)
    n_scores: dict = field(default_factory=dict)
    constructed_prompt: str = ""
    estimated_tokens: int = 0
    k_count: int = 0
    n_count: int = 0
    total_episodes_in_context: int = 0


class RetrievalEngine:

    def __init__(self, conn, embedding_provider=None):
        self.conn = conn

    def retrieve(self, user_message: str, turn_number: int) -> RetrievalResult:
        query_embedding = embed(user_message)
        all_episodes = get_all_episodes_with_embeddings(self.conn)

        deserialized_episodes = []
        for ep in all_episodes:
            ep_copy = dict(ep)
            if ep_copy["embedding"] is not None:
                ep_copy["embedding"] = np.frombuffer(ep_copy["embedding"], dtype=np.float32)
            deserialized_episodes.append(ep_copy)

        k_episode_ids, k_scores = self._k_retrieve(query_embedding, deserialized_episodes)
        n_episode_ids, n_scores = self._n_retrieve(deserialized_episodes)

        included_ids = set(k_episode_ids) | set(n_episode_ids)
        final_episodes = self._deduplicate_and_sort(deserialized_episodes, included_ids)

        retrieved_at = datetime.now(timezone.utc).isoformat()
        final_ids = [ep["id"] for ep in final_episodes]

        if final_ids:
            update_retrieval_metadata(self.conn, final_ids, retrieved_at)

            events = []
            k_set = set(k_episode_ids)
            n_set = set(n_episode_ids)
            for ep in final_episodes:
                eid = ep["id"]
                sim = k_scores.get(eid, 0.0)
                decay = n_scores.get(eid, 0.0)
                if eid in k_set and eid in n_set:
                    rtype = "KN"
                elif eid in k_set:
                    rtype = "K"
                else:
                    rtype = "N"
                events.append({
                    "turn_number": turn_number,
                    "episode_id": eid,
                    "similarity_score": sim,
                    "decay_score": decay,
                    "retrieval_type": rtype,
                })
            log_retrieval_events_batch(self.conn, events)

        clean_episodes = []
        for ep in final_episodes:
            ep_clean = {
                "id": ep["id"],
                "topic_id": ep["topic_id"],
                "user_message": ep["user_message"],
                "assistant_message": ep["assistant_message"],
                "turn_number": ep["turn_number"],
                "created_at": ep["created_at"],
                "last_retrieved_at": ep["last_retrieved_at"],
                "retrieval_count": ep["retrieval_count"],
            }
            clean_episodes.append(ep_clean)

        system_prompt = "You are a helpful assistant."
        constructed_prompt = build_prompt(clean_episodes, system_prompt)
        estimated_tokens = estimate_tokens(constructed_prompt)

        return RetrievalResult(
            episodes=clean_episodes,
            k_episode_ids=list(k_episode_ids),
            k_scores=dict(k_scores),
            n_episode_ids=list(n_episode_ids),
            n_scores=dict(n_scores),
            constructed_prompt=constructed_prompt,
            estimated_tokens=estimated_tokens,
            k_count=len(k_episode_ids),
            n_count=len(n_episode_ids),
            total_episodes_in_context=len(clean_episodes),
        )

    def _k_retrieve(
        self, query_embedding: np.ndarray, all_episodes: list
    ) -> tuple:
        k_episode_ids = []
        k_scores = {}
        for ep in all_episodes:
            ep_embedding = ep.get("embedding")
            if ep_embedding is None:
                continue
            sim = cosine_similarity(query_embedding, ep_embedding)
            if sim >= K_SIMILARITY_THRESHOLD:
                k_episode_ids.append(ep["id"])
                k_scores[ep["id"]] = sim
        return k_episode_ids, k_scores

    def _n_retrieve(self, all_episodes: list) -> tuple:
        n_scores = {}
        for ep in all_episodes:
            decay = self._compute_decay(ep.get("last_retrieved_at"))
            n_scores[ep["id"]] = decay
        n_episode_ids = sorted(n_scores.keys(), key=lambda eid: n_scores[eid], reverse=True)
        return n_episode_ids, n_scores

    def _compute_decay(self, last_retrieved_at):
        if last_retrieved_at is None:
            return 1.0
        last_dt = datetime.fromisoformat(last_retrieved_at)
        now_dt = datetime.now(timezone.utc)
        delta = now_dt - last_dt
        hours_since = delta.total_seconds() / 3600.0
        score = math.exp(-DECAY_RATE * hours_since)
        return score

    def _deduplicate_and_sort(self, all_episodes: list, included_ids: set) -> list:
        filtered = [ep for ep in all_episodes if ep["id"] in included_ids]
        filtered.sort(key=lambda ep: ep["turn_number"])
        return filtered
