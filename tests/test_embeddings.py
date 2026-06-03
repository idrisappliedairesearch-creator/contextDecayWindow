import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.embeddings.provider import cosine_similarity


class TestCosineSimilarity:
    def test_identical_vectors_return_one(self):
        a = np.random.rand(1024).astype(np.float32)
        result = cosine_similarity(a, a)
        assert abs(result - 1.0) < 1e-6

    def test_orthogonal_vectors_return_near_zero(self):
        a = np.zeros(1024, dtype=np.float32)
        a[0] = 1.0
        b = np.zeros(1024, dtype=np.float32)
        b[1] = 1.0
        result = cosine_similarity(a, b)
        assert abs(result) < 1e-6

    def test_opposite_vectors_return_near_negative_one(self):
        a = np.random.rand(1024).astype(np.float32)
        b = -a
        result = cosine_similarity(a, b)
        assert abs(result - (-1.0)) < 1e-6

    def test_returns_value_in_range(self):
        a = np.random.rand(1024).astype(np.float32)
        b = np.random.rand(1024).astype(np.float32)
        result = cosine_similarity(a, b)
        assert -1.0 <= result <= 1.0

    def test_zero_vector_returns_zero(self):
        a = np.zeros(1024, dtype=np.float32)
        b = np.ones(1024, dtype=np.float32)
        result = cosine_similarity(a, b)
        assert result == 0.0

    def test_accepts_list_input(self):
        a = [1.0, 0.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0, 0.0]
        result = cosine_similarity(a, b)
        assert abs(result - 1.0) < 1e-6


class TestEmbed:
    def test_returns_shape_1024(self):
        from src.embeddings.provider import embed
        result = embed("hello world")
        assert result.shape == (1024,)

    def test_returns_dtype_float32(self):
        from src.embeddings.provider import embed
        result = embed("hello world")
        assert result.dtype == np.float32

    def test_different_text_different_embedding(self):
        from src.embeddings.provider import embed
        a = embed("hello world")
        b = embed("goodbye world")
        assert not np.allclose(a, b)


class TestEnvVarMissing:
    def test_raises_error_when_model_path_missing(self):
        saved = os.environ.pop("CDW_EMBEDDING_MODEL_PATH", None)
        try:
            from src.embeddings import provider
            provider._MODEL = None
            import importlib
            importlib.reload(provider)
            with pytest.raises(EnvironmentError, match="CDW_EMBEDDING_MODEL_PATH"):
                provider.embed("test")
        finally:
            if saved is not None:
                os.environ["CDW_EMBEDDING_MODEL_PATH"] = saved
            provider._MODEL = None
            importlib.reload(provider)


import pytest
