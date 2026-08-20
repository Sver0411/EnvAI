import httpx

from app.services.ai_provider import OpenAICompatibleProvider


def test_openai_compatible_provider_parses_markdown_wrapped_json(monkeypatch):
    provider = OpenAICompatibleProvider(
        "https://llm.example/v1",
        "test-key",
        "test-model",
        timeout=2,
        max_retries=0,
    )

    def fake_post(url, *, headers, json, timeout, trust_env):
        assert url == "https://llm.example/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key"
        assert json["response_format"] == {"type": "json_object"}
        assert timeout == 2
        assert trust_env is False
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "```json\n{\"content\": \"测试正文\"}\n```"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    response = provider.generate_structured_output("system", "user")
    assert response.data == {"content": "测试正文"}
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 8


def test_openai_compatible_provider_can_disable_json_mode(monkeypatch):
    provider = OpenAICompatibleProvider(
        "https://llm.example/v1",
        "test-key",
        "test-model",
        timeout=2,
        max_retries=0,
        json_mode=False,
    )

    def fake_post(url, *, headers, json, timeout, trust_env):
        assert "response_format" not in json
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"content":"兼容模式正文"}'}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    assert provider.generate_structured_output("system", "user").data == {"content": "兼容模式正文"}
