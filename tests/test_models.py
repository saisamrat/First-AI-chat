from models import Conversation, Message


def test_message_to_dict_has_role_content_timestamp():
    message = Message(role="user", content="hi")
    data = message.to_dict()

    assert data == {
        "role": "user",
        "content": "hi",
        "timestamp": message.timestamp,
    }


def test_message_from_dict_round_trip():
    original = Message(role="assistant", content="hello there")
    rebuilt = Message.from_dict(original.to_dict())

    assert rebuilt == original


def test_message_default_timestamp_is_unique_per_instance():
    first = Message(role="user", content="a")
    second = Message(role="user", content="b")

    assert first.timestamp != second.timestamp or first is not second


def test_conversation_default_has_id_and_title():
    conversation = Conversation()

    assert conversation.id
    assert conversation.title == "New conversation"
    assert conversation.messages == []


def test_conversation_ids_are_unique():
    first = Conversation()
    second = Conversation()

    assert first.id != second.id


def test_add_message_appends_and_returns_message():
    conversation = Conversation()

    added = conversation.add_message("user", "hello")

    assert added.role == "user"
    assert added.content == "hello"
    assert conversation.messages == [added]


def test_conversation_to_dict_serializes_all_messages():
    conversation = Conversation(title="Test chat")
    conversation.add_message("user", "hi")
    conversation.add_message("assistant", "hello")

    data = conversation.to_dict()

    assert data["id"] == conversation.id
    assert data["title"] == "Test chat"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_conversation_from_dict_round_trip():
    original = Conversation(title="Round trip")
    original.add_message("user", "hello")
    original.add_message("assistant", "hi there")

    rebuilt = Conversation.from_dict(original.to_dict())

    assert rebuilt == original
