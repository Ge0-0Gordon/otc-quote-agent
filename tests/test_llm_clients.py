import json

import httpx

from otc_quote_agent.llm import OllamaClient, OpenAICompatibleClient


def test_openai_compatible_client_parses_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"coupon_rate": "15%"})}}
                ]
            },
        )

    client = OpenAICompatibleClient(
        "https://example.test/v1",
        "secret",
        "model",
        transport=httpx.MockTransport(handler),
    )

    assert client.complete_json([])["coupon_rate"] == "15%"


def test_ollama_client_sends_schema() -> None:
    schema = {"type": "object"}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["format"] == schema
        return httpx.Response(
            200,
            json={"message": {"content": '{"option_type":"call"}'}},
        )

    client = OllamaClient(
        "http://ollama.test",
        "qwen",
        transport=httpx.MockTransport(handler),
    )

    assert client.complete_json([], schema)["option_type"] == "call"
