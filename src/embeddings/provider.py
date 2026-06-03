import os
import numpy as np
from llama_cpp import Llama

_MODEL = None


def _get_model() -> Llama:
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    model_path = os.environ.get("CDW_EMBEDDING_MODEL_PATH")
    if not model_path:
        raise EnvironmentError(
            "CDW_EMBEDDING_MODEL_PATH environment variable is not set. "
            "Set it to the absolute path of your Qwen3-Embedding-0.6B GGUF file."
        )

    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Embedding model not found at: {model_path}"
        )

    _MODEL = Llama(
        model_path=model_path,
        embedding=True,
        n_gpu_layers=0,
        n_ctx=512,
        verbose=False,
    )
    return _MODEL


def embed(text: str) -> np.ndarray:
    model = _get_model()
    vectors = model.embed(text)
    result = np.array(vectors, dtype=np.float32)
    return result.reshape(1024)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))
