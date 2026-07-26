import json
import os
import sys

import pytest

import main as main_module

CONFIG_TEMPLATE = """
[api]
base_url = "https://api.groq.com/openai/v1/chat/completions"
model = "llama-3.3-70b-versatile"
key_env_var = "GROQ_API_KEY"
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

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="requires a real GROQ_API_KEY in the environment",
)
async def test_full_chat_flow_against_real_groq_api(monkeypatch, tmp_path, capsys):
    """End-to-end: real network call, real streaming parse, real autosave to disk.
    Nothing about api_client or history is mocked here - only input() is scripted,
    so this exercises the exact code path a real user hitting Enter would trigger."""
    history_dir = tmp_path / "history"
    log_path = tmp_path / "logs" / "chat.log"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        CONFIG_TEMPLATE.format(history_dir=str(history_dir), log_path=str(log_path))
    )

    monkeypatch.setattr(sys, "argv", ["main.py", "--config", str(config_path)])

    scripted_inputs = iter(["Reply with exactly the single word: acknowledged", "/quit"])

    def fake_input(prompt=""):
        try:
            return next(scripted_inputs)
        except StopIteration:
            raise EOFError("no more scripted input")

    monkeypatch.setattr("builtins.input", fake_input)

    await main_module.main()

    output = capsys.readouterr().out
    assert "acknowledged" in output.lower()

    saved_files = list(history_dir.glob("*.json"))
    assert len(saved_files) == 1

    saved_data = json.loads(saved_files[0].read_text())
    roles = [message["role"] for message in saved_data["messages"]]
    assert roles == ["user", "assistant"]
    assert saved_data["messages"][1]["content"].strip() != ""
