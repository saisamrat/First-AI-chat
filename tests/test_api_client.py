import json

import httpx
import pytest

import api_client
from api_client import build_messages, stream_reply
from config import Config
from models import Conversation


def make_config(**overrides):
    defaults = dict(
        api_base_url="https://api.groq.test/openai/v1/chat/completions",
        api_model="test-model",
        api_key_env_var="TEST_GROQ_API_KEY",
        api_timeout_seconds=30,
        api_temperature=0.5,
        api_key="fake-key-value",
        chat_max_history_messages=20,
        chat_history_dir="data/history",
        autosave_enabled=True,
        logging_level="INFO",
        logging_file_path="logs/chat.log",
    )
    defaults.update(overrides)
    return Config(**defaults)


def sse_body(*events):
    lines = [f"data: {json.dumps(event)}\n\n" for event in events]
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def install_mock_transport(monkeypatch, handler):
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        return real_async_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(api_client.httpx, "AsyncClient", fake_async_client)


# --- build_messages -------------------------------------------------------


def test_build_messages_strips_timestamp():
    conversation = Conversation()
    conversation.add_message("user", "hi")

    result = build_messages(conversation, max_history_messages=20)

    assert result == [{"role": "user", "content": "hi"}]


def test_build_messages_trims_to_last_n():
    conversation = Conversation()
    for i in range(5):
        conversation.add_message("user" if i % 2 == 0 else "assistant", f"message {i}")

    result = build_messages(conversation, max_history_messages=2)

    assert result == [
        {"role": "assistant", "content": "message 3"},
        {"role": "user", "content": "message 4"},
    ]


def test_build_messages_keeps_everything_when_fewer_than_limit():
    conversation = Conversation()
    conversation.add_message("user", "only message")

    result = build_messages(conversation, max_history_messages=20)

    assert len(result) == 1


# --- stream_reply ----------------------------------------------------------


async def test_stream_reply_yields_concatenated_chunks(monkeypatch):
    async def handler(request):
        body = sse_body(
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " world"}}]},
        )
        return httpx.Response(200, content=body)

    install_mock_transport(monkeypatch, handler)

    conversation = Conversation()
    conversation.add_message("user", "hi")
    config = make_config()

    chunks = [chunk async for chunk in stream_reply(conversation, config)]

    assert chunks == ["Hello", " world"]


async def test_stream_reply_skips_events_without_content(monkeypatch):
    async def handler(request):
        body = sse_body(
            {"choices": [{"delta": {"role": "assistant"}}]},
            {"choices": [{"delta": {"content": "actual text"}}]},
        )
        return httpx.Response(200, content=body)

    install_mock_transport(monkeypatch, handler)

    conversation = Conversation()
    conversation.add_message("user", "hi")
    config = make_config()

    chunks = [chunk async for chunk in stream_reply(conversation, config)]

    assert chunks == ["actual text"]


async def test_stream_reply_sends_expected_request(monkeypatch):
    captured = {}

    async def handler(request):
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, content=sse_body({"choices": [{"delta": {"content": "hi"}}]}))

    install_mock_transport(monkeypatch, handler)

    conversation = Conversation()
    conversation.add_message("user", "hello")
    config = make_config(api_model="my-model", api_temperature=0.9, api_key="secret-token")

    [chunk async for chunk in stream_reply(conversation, config)]

    assert captured["method"] == "POST"
    assert captured["url"] == config.api_base_url
    assert captured["headers"]["authorization"] == "Bearer secret-token"
    assert captured["body"]["model"] == "my-model"
    assert captured["body"]["temperature"] == 0.9
    assert captured["body"]["stream"] is True
    assert captured["body"]["messages"] == [{"role": "user", "content": "hello"}]


async def test_stream_reply_raises_on_http_error(monkeypatch):
    async def handler(request):
        return httpx.Response(401, json={"error": "unauthorized"})

    install_mock_transport(monkeypatch, handler)

    conversation = Conversation()
    conversation.add_message("user", "hi")
    config = make_config()

    with pytest.raises(httpx.HTTPStatusError):
        [chunk async for chunk in stream_reply(conversation, config)]
