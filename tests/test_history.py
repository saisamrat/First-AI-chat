import asyncio
import json

import pytest

from history import list_conversations, load_conversation, save_conversation
from models import Conversation


async def test_save_conversation_writes_file(tmp_path):
    conversation = Conversation(title="First chat")
    conversation.add_message("user", "hi")

    await save_conversation(conversation, str(tmp_path))

    saved_path = tmp_path / f"{conversation.id}.json"
    assert saved_path.exists()
    assert json.loads(saved_path.read_text()) == conversation.to_dict()


async def test_save_conversation_creates_missing_directory(tmp_path):
    history_dir = tmp_path / "does" / "not" / "exist"
    conversation = Conversation(title="Fresh dir")

    await save_conversation(conversation, str(history_dir))

    assert (history_dir / f"{conversation.id}.json").exists()


async def test_load_conversation_round_trip(tmp_path):
    original = Conversation(title="Round trip")
    original.add_message("user", "hello")
    original.add_message("assistant", "hi there")
    await save_conversation(original, str(tmp_path))

    loaded = await load_conversation(original.id, str(tmp_path))

    assert loaded == original


async def test_load_conversation_missing_id_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        await load_conversation("does-not-exist", str(tmp_path))


async def test_list_conversations_returns_id_title_pairs(tmp_path):
    first = Conversation(title="First chat")
    second = Conversation(title="Second chat")
    await save_conversation(first, str(tmp_path))
    await save_conversation(second, str(tmp_path))

    result = list_conversations(str(tmp_path))

    assert set(result) == {(first.id, first.title), (second.id, second.title)}


async def test_list_conversations_ignores_non_json_files(tmp_path):
    conversation = Conversation(title="Only real one")
    await save_conversation(conversation, str(tmp_path))
    (tmp_path / ".DS_Store").write_text("not json")

    result = list_conversations(str(tmp_path))

    assert result == [(conversation.id, conversation.title)]


def test_list_conversations_missing_directory_returns_empty_list(tmp_path):
    result = list_conversations(str(tmp_path / "missing"))

    assert result == []


def test_list_conversations_empty_string_returns_empty_list():
    assert list_conversations("") == []


async def test_concurrent_saves_do_not_corrupt_the_file(tmp_path):
    conversation = Conversation(title="Concurrent test")
    conversation.add_message("user", "hi")

    await asyncio.gather(
        *(save_conversation(conversation, str(tmp_path)) for _ in range(10))
    )

    saved_path = tmp_path / f"{conversation.id}.json"
    assert json.loads(saved_path.read_text()) == conversation.to_dict()
