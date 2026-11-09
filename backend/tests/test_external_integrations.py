import asyncio
from types import SimpleNamespace

from backend.app.agent import groq_client
from backend.app.database.schema import init_db
from backend.app.hindsight.client_wrapper import HindsightClientWrapper


def test_groq_request_uses_bearer_api_key(monkeypatch):
    sent_requests = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "Groq response"}}]}

    class FakeHttpClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, headers, json):
            sent_requests.append({"url": url, "headers": headers, "payload": json})
            return FakeResponse()

    monkeypatch.setattr(groq_client, "get_setting", lambda key, default="": {
        "groq_api_key": "test-key",
        "groq_model": "openai/gpt-oss-120b",
        "simulation_mode": "false",
    }.get(key, default))
    monkeypatch.setattr(groq_client.httpx, "AsyncClient", lambda timeout: FakeHttpClient())

    result = asyncio.run(groq_client.GroqClient().generate_completion([
        {"role": "user", "content": "Check the deployment"}
    ]))

    assert result["provider"] == "Groq Cloud (openai/gpt-oss-120b)"
    assert sent_requests[0]["headers"]["Authorization"] == "Bearer test-key"


def test_hindsight_sdk_responses_are_adapted():
    init_db()
    wrapper = HindsightClientWrapper()
    remote = SimpleNamespace(
        retain=lambda **kwargs: SimpleNamespace(success=True),
        recall=lambda **kwargs: SimpleNamespace(results=[
            SimpleNamespace(
                id="remote-memory-1",
                text="A verified database connection fix.",
                metadata={"fix_succeeded": "true"},
                scores=SimpleNamespace(final=0.8),
                mentioned_at="2026-01-01T00:00:00Z",
                occurred_start=None,
            )
        ]),
        reflect=lambda **kwargs: SimpleNamespace(text="Use the verified database secret."),
    )
    wrapper.remote_client = remote

    retained = wrapper.retain(
        "Database timeout incident",
        metadata={"fix_succeeded": True},
    )
    recalled = wrapper.recall("database timeout")
    reflection = wrapper.reflect("database timeout")

    assert retained["remote_synced"] is True
    assert recalled[0]["content"] == "A verified database connection fix."
    assert recalled[0]["metadata"]["fix_succeeded"] is True
    assert recalled[0]["similarity_score"] == 0.8
    assert reflection["synthesis"] == "Use the verified database secret."
    assert wrapper.get_status()["is_connected_to_cloud"] is True
