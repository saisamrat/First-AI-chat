import asyncio
import json
import logging
from typing import Dict

from models import Conversation
import os



_save_lock = asyncio.Lock() 


async def save_conversation(conversation: Conversation, history_dir: str) -> None:
    json_path = f"{history_dir}/{conversation.id}.json"
    os.makedirs(history_dir, exist_ok=True)
    
    async with _save_lock:
        logging.getLogger(__name__).info(f"acquired lock for conversation {conversation.id} to path {json_path}")
        await asyncio.to_thread(write_json, json_path, conversation.to_dict())
    
    logging.getLogger(__name__).info(f"saved conversation {conversation.id} to path {json_path}")



def write_json(path:str, data:Dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    


async def load_conversation(id:str, history_dir:str) -> Conversation:

    data = []
    json_path = f"{history_dir}/{id}.json"
    async with _save_lock:
        logging.getLogger(__name__).info(f"acquired lock for loading {id} for path {history_dir}")
        data = await asyncio.to_thread(load_json, json_path)

    return Conversation.from_dict(data)



def load_json(path:str) -> Dict:
    with open(path) as p:
        return json.load(p)


def list_conversations(history_dir:str) -> list[tuple[str, str]]:

    if not history_dir:
        logging.getLogger(__name__).error("directory path is empty")
        return []
    if not os.path.isdir(history_dir):
        logging.getLogger(__name__).error(f"directory {history_dir} does not exist")
        return []

    files = [f for f in os.listdir(history_dir) if f.endswith(".json")]
    collection = []
    for file in files:
        c = Conversation.from_dict(load_json(f"{history_dir}/{file}"))
        t = (c.id, c.title)
        collection.append(t)

    return collection
 
