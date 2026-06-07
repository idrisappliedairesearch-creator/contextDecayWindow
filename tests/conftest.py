import os
from dataclasses import dataclass

# Load .env from project root so tests pick up persisted config
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(dotenv_path):
    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

os.environ.setdefault("CDW_EMBEDDING_MODEL_PATH", r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf")


@dataclass
class MockInferenceResult:
    assistant_message: str
    tokens_per_second: float
    time_to_first_token: float
    output_tokens: int
    contains_rule: bool = False
    rule_summary: str = None


class MockInferenceProvider:
    def __init__(self):
        self._call_count = 0

    def complete(self, prompt: str, suppress_rule_detection: bool = False) -> MockInferenceResult:
        self._call_count += 1

        if suppress_rule_detection:
            return MockInferenceResult(
                assistant_message="Mock assistant response.",
                tokens_per_second=50.0,
                time_to_first_token=0.02,
                output_tokens=4,
                contains_rule=False,
                rule_summary=None,
            )

        if self._call_count == 1:
            return MockInferenceResult(
                assistant_message="Mock assistant response.",
                tokens_per_second=50.0,
                time_to_first_token=0.02,
                output_tokens=4,
                contains_rule=True,
                rule_summary="Always respond in bullet points.",
            )

        return MockInferenceResult(
            assistant_message="Mock assistant response.",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
            contains_rule=False,
            rule_summary=None,
        )
