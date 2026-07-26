import sys

import httpx
import pytest

import main as main_module
from history import save_conversation
from models import Conversation

CONFIG_TEMPLATE = """
[api]
base_url = "https://api.groq.test/openai/v1/chat/completions"
model = "test-model"
key_env_var = "TEST_GROQ_API_KEY"
timeout_seconds = 30
temperature = 0.7

[chat]
max_history_messages = 20
history_dir = "{history_dir}"

[autosave]
enabled = true

[logging]
level = "INFO"
file_path = "{log_path}"
"""


def write_config(tmp_path):
    history_dir = tmp_path / "history"
    log_path = tmp_path / "logs" / "chat.log"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        CONFIG_TEMPLATE.format(history_dir=str(history_dir), log_path=str(log_path))
    )
    return str(config_path), str(history_dir)


def install_cli_environment(monkeypatch, tmp_path, inputs):
    monkeypatch.setenv("TEST_GROQ_API_KEY", "fake-key-value")
    config_path, history_dir = write_config(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--config", config_path])

    input_iterator = iter(inputs)

    def fake_input(prompt=""):
        try:
            return next(input_iterator)
        except StopIteration:
            raise EOFError("no more scripted input")

    monkeypatch.setattr("builtins.input", fake_input)
    return history_dir


def make_fake_stream_reply(chunks):
    async def fake_stream_reply(conversation, config):
        for chunk in chunks:
            yield chunk

    return fake_stream_reply


def make_failing_stream_reply(exception):
    async def fake_stream_reply(conversation, config):
        raise exception
        yield  # pragma: no cover - makes this a generator function

    return fake_stream_reply


async def test_plain_chat_message_streams_reply_and_autosaves(monkeypatch, tmp_path, capsys):
    history_dir = install_cli_environment(monkeypatch, tmp_path, ["Hello there", "/quit"])
    monkeypatch.setattr(main_module, "stream_reply", make_fake_stream_reply(["Hi", " back"]))

    await main_module.main()

    output = capsys.readouterr().out
    assert "Hi back" in output

    saved_files = list((tmp_path / "history").glob("*.json"))
    assert len(saved_files) == 1


async def test_history_command_lists_saved_conversations(monkeypatch, tmp_path, capsys):
    history_dir = install_cli_environment(monkeypatch, tmp_path, ["/history", "/quit"])
    existing = Conversation(title="Existing chat")
    await save_conversation(existing, history_dir)
    monkeypatch.setattr(main_module, "stream_reply", make_fake_stream_reply([]))

    await main_module.main()

    output = capsys.readouterr().out
    assert existing.id in output
    assert "Existing chat" in output


async def test_save_command_saves_immediately(monkeypatch, tmp_path):
    history_dir = install_cli_environment(monkeypatch, tmp_path, ["hello", "/save", "/quit"])
    monkeypatch.setattr(main_module, "stream_reply", make_fake_stream_reply(["a reply"]))

    await main_module.main()

    saved_files = list((tmp_path / "history").glob("*.json"))
    assert len(saved_files) == 1


async def test_load_command_switches_conversation(monkeypatch, tmp_path, capsys):
    history_dir = install_cli_environment(monkeypatch, tmp_path, [])
    existing = Conversation(title="Loadable chat")
    existing.add_message("user", "hi")
    await save_conversation(existing, history_dir)

    history_dir = install_cli_environment(
        monkeypatch, tmp_path, [f"/load {existing.id}", "/quit"]
    )
    monkeypatch.setattr(main_module, "stream_reply", make_fake_stream_reply([]))

    await main_module.main()

    output = capsys.readouterr().out
    assert "Loadable chat" in output


async def test_load_command_with_unknown_id_prints_error(monkeypatch, tmp_path, capsys):
    install_cli_environment(monkeypatch, tmp_path, ["/load does-not-exist", "/quit"])
    monkeypatch.setattr(main_module, "stream_reply", make_fake_stream_reply([]))

    await main_module.main()

    output = capsys.readouterr().out
    assert "No conversation found with id does-not-exist" in output


async def test_unknown_command_does_not_reach_the_api(monkeypatch, tmp_path, capsys):
    calls = []

    async def tracking_stream_reply(conversation, config):
        calls.append(conversation)
        return
        yield  # pragma: no cover

    install_cli_environment(monkeypatch, tmp_path, ["/bogus", "/quit"])
    monkeypatch.setattr(main_module, "stream_reply", tracking_stream_reply)

    await main_module.main()

    output = capsys.readouterr().out
    assert "Unknown command /bogus" in output
    assert calls == []


async def test_api_error_is_reported_and_loop_continues(monkeypatch, tmp_path, capsys):
    install_cli_environment(monkeypatch, tmp_path, ["hello", "/quit"])
    monkeypatch.setattr(
        main_module,
        "stream_reply",
        make_failing_stream_reply(httpx.TimeoutException("timed out")),
    )

    await main_module.main()

    output = capsys.readouterr().out
    assert "error in talking to groq" in output
