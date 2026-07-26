

import os
import tomllib
from dataclasses import dataclass


@dataclass
class Config:
    api_base_url: str
    api_model: str
    api_key_env_var: str
    api_timeout_seconds: int
    api_temperature: float
    api_key: str

    chat_max_history_messages: int
    chat_history_dir: str

    autosave_enabled: bool

    logging_level: str
    logging_file_path: str


def load_config(path: str = "config.toml") -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    try:
        api = data["api"]
        chat = data["chat"]
        autosave = data["autosave"]
        logging_section = data["logging"]
    except KeyError as e:
        raise RuntimeError(f"Missing section {e} in {path}") from e

    key_env_var = api["key_env_var"]
    api_key = os.environ.get(key_env_var)
    if not api_key:
        raise RuntimeError(f"Environment variable {key_env_var} is not set")

    timeout_seconds = api["timeout_seconds"]
    if timeout_seconds <= 0:
        raise RuntimeError("api.timeout_seconds must be a positive number")

    max_history_messages = chat["max_history_messages"]
    if max_history_messages <= 0:
        raise RuntimeError("chat.max_history_messages must be a positive number")

    return Config(
        api_base_url=api["base_url"],
        api_model=api["model"],
        api_key_env_var=key_env_var,
        api_timeout_seconds=timeout_seconds,
        api_temperature=api["temperature"],
        api_key=api_key,
        chat_max_history_messages=max_history_messages,
        chat_history_dir=chat["history_dir"],
        autosave_enabled=autosave["enabled"],
        logging_level=logging_section["level"],
        logging_file_path=logging_section["file_path"],
    )
