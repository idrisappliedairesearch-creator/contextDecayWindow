import os
import time
from dataclasses import dataclass

from llama_cpp import Llama


@dataclass
class InferenceResult:
    assistant_message: str
    tokens_per_second: float
    time_to_first_token: float
    output_tokens: int


class InferenceProvider:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        model_path = os.environ.get("CDW_INFERENCE_MODEL_PATH")
        if not model_path:
            raise EnvironmentError(
                "CDW_INFERENCE_MODEL_PATH environment variable is not set. "
                "Set it to the absolute path of your Qwen3.6 27B Q6_K GGUF file."
            )

        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Inference model not found at: {model_path}"
            )

        n_gpu_layers = int(os.environ.get("CDW_INFERENCE_N_GPU_LAYERS", "-1"))
        n_ctx = int(os.environ.get("CDW_INFERENCE_N_CTX", "32768"))

        self._llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
        )
        self._initialized = True

    def complete(self, prompt: str) -> InferenceResult:
        start = time.perf_counter()
        response = self._llm(
            prompt,
            max_tokens=1024,
            echo=False,
            stream=False,
        )
        elapsed = time.perf_counter() - start

        assistant_message = response["choices"][0]["text"]
        output_tokens = response["usage"]["completion_tokens"]
        tokens_per_second = output_tokens / elapsed if elapsed > 0 else 0.0
        time_to_first_token = elapsed / output_tokens if output_tokens > 0 else elapsed

        return InferenceResult(
            assistant_message=assistant_message,
            tokens_per_second=tokens_per_second,
            time_to_first_token=time_to_first_token,
            output_tokens=output_tokens,
        )
