import argparse
import asyncio
import logging

import httpx
from api_client import stream_reply
from config import Config, load_config
from history import list_conversations, load_conversation, save_conversation
from logging_setup import setup_logging
from models import Conversation

def args_parse():
   
   parser = argparse.ArgumentParser(description="A simple AI chat CLI")
   parser.add_argument("--config", default="config.toml", help="Path to config")
   parser.add_argument("--resume", default=None, help="Conversation ID to resume") 
   return parser.parse_args()

async def main():
    args = args_parse()

    config = load_config(args.config)

    listener = setup_logging(config)

    if not args.resume:
        conversation = Conversation()
    else:
        conversation = await load_conversation(args.resume, config.chat_history_dir)

    pending_save_task = None
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        inputs = user_input.split(maxsplit=1)
        command = inputs[0]
        arg = inputs[1] if len(inputs) > 1 else None
        if command == "/quit":
            break
        elif command == "/history":
            for conv_id, title in list_conversations(config.chat_history_dir):
                print(f"{conv_id} {title}")
            continue
        elif command == "/save":
            await save_conversation(conversation, config.chat_history_dir)
            continue
        elif command == "/clear":
            print(f"starting new conversation")
            conversation = Conversation()
            continue
        elif command == "/load":      
            try:
                conversation = await load_conversation(arg, config.chat_history_dir)
                print(f"Conversation loaded {conversation.title}")
                continue
            except FileNotFoundError:
                print(f"No conversation found with id {arg}")
                continue
        elif command.startswith("/") :
            print(f"Unknown command {command}")
            continue

        conversation.add_message("user", user_input)
        full_reply = ""

        try:
            async for chunk in stream_reply(conversation, config):
                print(chunk, end="", flush=True)
                full_reply += chunk
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
            print(f"\n[error in talking to groq {e}]")
            logging.getLogger(__name__).error(f"Api Error: {e}")
            continue

        conversation.add_message("assistant", full_reply)

        if(config.autosave_enabled):
            pending_save_task = asyncio.create_task(save_conversation(conversation, config.chat_history_dir))


    if pending_save_task is not None and not pending_save_task.done():
        await pending_save_task

    listener.stop()






if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        print(f"command termainated...")



    

