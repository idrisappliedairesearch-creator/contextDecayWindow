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


class MockInferenceProvider:
    def complete(self, prompt: str) -> MockInferenceResult:
        return MockInferenceResult(
            assistant_message="Mock assistant response.",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
        )
