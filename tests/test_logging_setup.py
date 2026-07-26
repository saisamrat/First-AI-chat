import logging

from config import Config
from logging_setup import setup_logging


def make_config(tmp_path, level="INFO"):
    log_path = tmp_path / "logs" / "chat.log"
    return Config(
        api_base_url="https://example.invalid",
        api_model="test-model",
        api_key_env_var="TEST_GROQ_API_KEY",
        api_timeout_seconds=30,
        api_temperature=0.7,
        api_key="fake-key",
        chat_max_history_messages=20,
        chat_history_dir=str(tmp_path / "history"),
        autosave_enabled=True,
        logging_level=level,
        logging_file_path=str(log_path),
    )


def test_setup_logging_creates_log_directory_and_file(tmp_path):
    config = make_config(tmp_path)

    listener = setup_logging(config)
    logging.getLogger("test").info("hello from test")
    listener.stop()

    assert (tmp_path / "logs" / "chat.log").exists()


def test_setup_logging_writes_formatted_message(tmp_path):
    config = make_config(tmp_path)

    listener = setup_logging(config)
    logging.getLogger("my.module").info("a specific message")
    listener.stop()

    contents = (tmp_path / "logs" / "chat.log").read_text()

    assert "[INFO]" in contents
    assert "my.module" in contents
    assert "a specific message" in contents


def test_setup_logging_filters_below_configured_level(tmp_path):
    config = make_config(tmp_path, level="INFO")

    listener = setup_logging(config)
    logging.getLogger("test").debug("this should be filtered out")
    logging.getLogger("test").info("this should appear")
    listener.stop()

    contents = (tmp_path / "logs" / "chat.log").read_text()

    assert "this should be filtered out" not in contents
    assert "this should appear" in contents


def test_listener_stop_flushes_pending_records(tmp_path):
    config = make_config(tmp_path)

    listener = setup_logging(config)
    for i in range(20):
        logging.getLogger("test").info(f"message {i}")
    listener.stop()

    contents = (tmp_path / "logs" / "chat.log").read_text()

    for i in range(20):
        assert f"message {i}" in contents
