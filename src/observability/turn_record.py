from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class AssignmentResult:
    topic_id: str
    topic_label: str
    is_new_topic: bool
    centroid_drift: float


@dataclass
class TurnRecord:
    # Identity
    turn_number: int
    condition: str

    # User input
    user_message: str

    # Retrieval (populated by RetrievalEngine)
    k_count: int = 0
    n_count: int = 0
    n_total_in_store: int = 0
    total_in_context: int = 0
    k_episodes: list[dict] = field(default_factory=list)
    n_episodes: list[dict] = field(default_factory=list)
    estimated_tokens: int = 0
    k_token_estimate: int = 0
    n_token_estimate: int = 0

    # Topic layer (populated by TopicManager)
    topic_count: int = 0
    episode_count: int = 0
    new_topic_created: bool = False
    new_topic_label: Optional[str] = None
    centroid_drift: dict[str, float] = field(default_factory=dict)

    # Generation (populated by inference runner — Sprint 008)
    tokens_per_second: Optional[float] = None
    time_to_first_token: Optional[float] = None
    output_tokens: Optional[int] = None
    assistant_message: Optional[str] = None

    # Storage (populated after generation)
    stored_episode_id: Optional[str] = None
    stored_topic_label: Optional[str] = None

    # Compaction (populated by CompactionRunner)
    compaction_occurred: bool = False
    compaction_turn: Union[int, None] = None
    history_tokens_before_compaction: Union[int, None] = None

    # Rule detection (populated by InferenceProvider + RetrievalEngine)
    contains_rule: bool = False
    rule_summary: Optional[str] = None
    rule_store_count: int = 0
    rule_token_estimate: int = 0

    # Computed at flush time
    previous_context_window: Optional[str] = None
    constructed_prompt: str = ""
