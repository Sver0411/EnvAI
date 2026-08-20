import httpx
import pytest

from app.services.embedding import EmbeddingError, OpenAICompatibleEmbeddingProvider


def test_openai_compatible_embedding_orders_vectors(monkeypatch):
    provider = OpenAICompatibleEmbeddingProvider(
        "https://embedding.example/v1",
        "test-key",
        "test-embedding",
        dimension=3,
        timeout=2,
        max_retries=0,
    )

    def fake_post(url, *, headers, json, timeout, trust_env):
        assert url == "https://embedding.example/v1/embeddings"
        assert headers["Authorization"] == "Bearer test-key"
        assert json == {"model": "test-embedding", "input": ["a", "b"]}
        assert timeout == 2
        assert trust_env is False
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    assert provider.embed_texts(["a", "b"]) == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_openai_compatible_embedding_rejects_dimension_mismatch(monkeypatch):
    provider = OpenAICompatibleEmbeddingProvider(
        "https://embedding.example/v1", "test-key", "test-embedding", dimension=3, timeout=2, max_retries=0
    )

    def fake_post(url, **_kwargs):
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(EmbeddingError, match="维度不匹配"):
        provider.embed_texts(["a"])
