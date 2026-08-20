"""可替换的结构化 AI Provider 边界；默认 Mock，测试不依赖外部 API。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


@dataclass(slots=True)
class AIUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(slots=True)
class AIResponse:
    data: dict[str, Any]
    usage: AIUsage = field(default_factory=AIUsage)


class AIExtractedFactModel(BaseModel):
    """模型输出的最小结构；任何不符合此结构的结果都会被丢弃。"""

    entity_type: str = Field(min_length=1, max_length=64)
    entity_key: str = Field(default="project", max_length=255)
    field_name: str = Field(min_length=1, max_length=64)
    raw_value: str | int | float | None = None
    unit: str | None = None
    source_location: dict[str, Any] = Field(default_factory=dict)
    source_text: str = ""


class AIProvider:
    name = "base"
    model_name: str | None = None

    def generate_structured_output(self, system_prompt: str, user_content: str) -> AIResponse:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    name = "mock"
    model_name = "mock-structured-v1"

    def generate_structured_output(self, system_prompt: str, user_content: str) -> AIResponse:
        # Mock 不执行资料中的指令，也不猜测缺失字段；从受控 Project Facts 生成可审计的固定章节结果。
        if "<section_instructions>" not in user_content:
            return AIResponse(data={"facts": []}, usage=AIUsage())
        section_match = __import__("re").search(r"章节：([^\n]+)", user_content)
        title = section_match.group(1).strip() if section_match else "章节"
        facts_block = user_content.split("<project_facts>", 1)[-1].split("</project_facts>", 1)[0]
        facts = __import__("re").findall(r"\[(P\d+)\]\s*(.+)", facts_block)
        knowledge_block = user_content.split("<knowledge_sources>", 1)[-1].split("</knowledge_sources>", 1)[0]
        knowledge = __import__("re").findall(r"\[(K\d+)\]\s*(.+)", knowledge_block)
        content_lines = [f"{title}。"]
        if facts:
            content_lines.append("；".join(item[1] for item in facts[:8]))
        elif "knowledge_sources" in user_content:
            content_lines.append("根据所提供的专业知识来源整理本章节内容。")
        citations = [{"source_id": source_id, "claim": text[:120]} for source_id, text in (facts[:2] + knowledge[:3])]
        return AIResponse(data={"content": "\n".join(content_lines), "citations": citations, "missing_information": [], "warnings": [], "used_project_facts": [item[0] for item in facts], "used_knowledge_sources": [item[0] for item in knowledge]}, usage=AIUsage())


class OpenAICompatibleProvider(AIProvider):
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model_name: str, timeout: float, max_retries: int, json_mode: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.json_mode = json_mode

    def generate_structured_output(self, system_prompt: str, user_content: str) -> AIResponse:
        payload = {
            "model": self.model_name,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=self.timeout,
                    # Local development environments may export malformed proxy
                    # variables (for example an IPv6 NO_PROXY token).  The
                    # OpenCode endpoint is reachable directly, so avoid letting
                    # those variables break URL parsing before the request is sent.
                    trust_env=False,
                )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                data = _parse_json_content(content)
                usage = body.get("usage") or {}
                return AIResponse(
                    data=data,
                    usage=AIUsage(usage.get("prompt_tokens"), usage.get("completion_tokens")),
                )
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 4))
        raise RuntimeError("AI Provider 调用失败") from last_error


def _parse_json_content(content: Any) -> dict[str, Any]:
    """Parse strict JSON while tolerating common model markdown wrappers."""
    if isinstance(content, list):
        content = "".join(str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in content)
    if not isinstance(content, str):
        raise ValueError("AI 返回内容不是文本")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip() if len(lines) >= 2 else ""
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("AI 返回 JSON 必须是对象")
    return value


def get_ai_provider() -> AIProvider:
    provider = settings.ai_provider.lower()
    if provider == "mock":
        return MockAIProvider()
    if provider in {"openai", "openai_compatible"}:
        if not settings.ai_base_url or not settings.ai_api_key or not settings.ai_model:
            raise RuntimeError("AI Provider 配置不完整")
        return OpenAICompatibleProvider(
            settings.ai_base_url,
            settings.ai_api_key.get_secret_value(),
            settings.ai_model,
            settings.ai_timeout,
            settings.ai_max_retries,
            settings.ai_json_mode,
        )
    raise RuntimeError(f"不支持的 AI Provider：{settings.ai_provider}")
