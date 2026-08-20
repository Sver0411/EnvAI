from __future__ import annotations

import hashlib
import time
import math
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(ABC):
    name = "base"
    model = "base"
    version = "v1"
    dimension = 0

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    name = "mock"
    model = settings.embedding_model
    version = "hash-v1"
    dimension = settings.embedding_dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            seed = hashlib.sha256(text.encode("utf-8")).digest()
            values = []
            for index in range(self.dimension):
                digest = hashlib.sha256(seed + index.to_bytes(4, "big")).digest()
                values.append((int.from_bytes(digest[:4], "big") / 2**31) - 1.0)
            norm = math.sqrt(sum(value * value for value in values)) or 1.0
            vectors.append([round(value / norm, 8) for value in values])
        return vectors


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embedding provider for OpenAI-compatible ``/embeddings`` APIs.

    The API is intentionally kept behind the same small interface as the local
    deterministic provider.  This lets local development keep using Mock while
    a staging/production environment switches to a real model without changing
    retrieval or indexing code.
    """

    name = "openai_compatible"
    version = "openai-compatible-v1"

    def __init__(self, base_url: str, api_key: str, model: str, dimension: int, timeout: float, max_retries: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.timeout = timeout
        self.max_retries = max_retries

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self.model, "input": texts}
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=self.timeout,
                    trust_env=False,
                )
                response.raise_for_status()
                body = response.json()
                rows = body.get("data")
                if not isinstance(rows, list) or len(rows) != len(texts):
                    raise EmbeddingError("Embedding 返回数量与输入不一致")
                ordered = sorted(rows, key=lambda item: int(item.get("index", 0)))
                vectors = [item.get("embedding") for item in ordered]
                if any(not isinstance(vector, list) or not vector for vector in vectors):
                    raise EmbeddingError("Embedding 返回向量为空")
                if any(len(vector) != self.dimension for vector in vectors):
                    raise EmbeddingError(
                        f"Embedding 维度不匹配：配置为 {self.dimension}，接口返回 {len(vectors[0])}"
                    )
                return [[float(value) for value in vector] for vector in vectors]
            except EmbeddingError:
                # A malformed response or dimension mismatch is deterministic;
                # retrying it only hides the actionable configuration problem.
                raise
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 4))
        raise EmbeddingError("Embedding Provider 调用失败") from last_error


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider == "mock":
        return MockEmbeddingProvider()
    if provider in {"openai", "openai_compatible"}:
        if not settings.embedding_base_url or not settings.embedding_api_key or not settings.embedding_model:
            raise EmbeddingError("Embedding Provider 配置不完整")
        return OpenAICompatibleEmbeddingProvider(
            settings.embedding_base_url,
            settings.embedding_api_key.get_secret_value(),
            settings.embedding_model,
            settings.embedding_dimension,
            settings.embedding_timeout,
            settings.embedding_max_retries,
        )
    raise EmbeddingError(f"不支持的 Embedding Provider：{settings.embedding_provider}")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0
