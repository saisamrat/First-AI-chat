import json
from typing import AsyncIterator

import httpx

from config import Config
from models import Conversation


def build_messages(conversation : Conversation, max_history_messages: int) -> list[dict]:
    messages = conversation.messages[-max_history_messages:]
    output_messages = []
    for message in messages:
        d = message.to_dict()
        d.pop("timestamp")
        output_messages.append(d)

    return output_messages


async def stream_reply(conversation: Conversation, config: Config) -> AsyncIterator[str]:
    messages = build_messages(conversation, config.chat_max_history_messages)
    payload = {
        "messages": messages,
        "model": config.api_model,
        "temperature": config.api_temperature,
        "stream": True,
    }

    headers = {"Authorization": f"Bearer {config.api_key}", "content-type": "application/json"}

    ### output data: {"choices":[{"delta":{"content":"Hello"}}]}

    async with httpx.AsyncClient(timeout=config.api_timeout_seconds) as client:
        async with client.stream("POST", config.api_base_url, json=payload, headers= headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip(): continue

                if not line.startswith("data: "): continue

                payload_str = line[len("data: "):]
                if payload_str.strip() == "[DONE]": return
                parsed = json.loads(payload_str)
                content = parsed["choices"][0]["delta"].get("content")
                if content: yield content



