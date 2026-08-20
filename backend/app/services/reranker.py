from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RerankerProvider(ABC):
    """可替换的候选重排接口；Phase 4 默认不调用外部模型。"""

    name = "base"

    @abstractmethod
    def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError


class NoopReranker(RerankerProvider):
    name = "noop"

    def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for candidate in candidates:
            candidate["rerank_score"] = None
        return candidates


def get_reranker() -> RerankerProvider:
    return NoopReranker()
