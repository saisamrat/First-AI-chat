import pytest

from config import load_config

VALID_TOML = """
[api]
base_url = "https://api.groq.com/openai/v1/chat/completions"
model = "llama-3.3-70b-versatile"
key_env_var = "TEST_GROQ_API_KEY"
timeout_seconds = 30
temperature = 0.7

[chat]
max_history_messages = 20
history_dir = "data/history"

[autosave]
enabled = true

[logging]
level = "INFO"
file_path = "logs/chat.log"
"""


def write_config(tmp_path, content):
    config_path = tmp_path / "config.toml"
    config_path.write_text(content)
    return str(config_path)


def test_load_config_success(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_API_KEY", "fake-key-value")
    config_path = write_config(tmp_path, VALID_TOML)

    config = load_config(config_path)

    assert config.api_base_url == "https://api.groq.com/openai/v1/chat/completions"
    assert config.api_model == "llama-3.3-70b-versatile"
    assert config.api_key_env_var == "TEST_GROQ_API_KEY"
    assert config.api_key == "fake-key-value"
    assert config.api_timeout_seconds == 30
    assert config.api_temperature == 0.7
    assert config.chat_max_history_messages == 20
    assert config.chat_history_dir == "data/history"
    assert config.autosave_enabled is True
    assert config.logging_level == "INFO"
    assert config.logging_file_path == "logs/chat.log"


def test_load_config_missing_env_var_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_GROQ_API_KEY", raising=False)
    config_path = write_config(tmp_path, VALID_TOML)

    with pytest.raises(RuntimeError, match="TEST_GROQ_API_KEY"):
        load_config(config_path)


def test_load_config_missing_section_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_API_KEY", "fake-key-value")
    toml_without_chat_section = VALID_TOML.replace(
        "[chat]\nmax_history_messages = 20\nhistory_dir = \"data/history\"\n", ""
    )
    config_path = write_config(tmp_path, toml_without_chat_section)

    with pytest.raises(RuntimeError):
        load_config(config_path)


def test_load_config_non_positive_timeout_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_API_KEY", "fake-key-value")
    bad_toml = VALID_TOML.replace("timeout_seconds = 30", "timeout_seconds = 0")
    config_path = write_config(tmp_path, bad_toml)

    with pytest.raises(RuntimeError):
        load_config(config_path)


def test_load_config_non_positive_max_history_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_API_KEY", "fake-key-value")
    bad_toml = VALID_TOML.replace("max_history_messages = 20", "max_history_messages = 0")
    config_path = write_config(tmp_path, bad_toml)

    with pytest.raises(RuntimeError):
        load_config(config_path)
