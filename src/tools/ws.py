import json
import logging
from functools import partial
from itertools import chain

from typing import Optional, List, Dict, Callable


from fastapi import HTTPException, WebSocket


from src.prompt_storage.api.storage import StorageApi
from src.repository.chat import ChatRepository
from src.repository.message import MessageRepository

from src.schemas.ws_message import WSMessageOut, RespTypes

from src.tools.chatgpt import stream_completion
from src.tools.auth_deps import Identity

from src.schemas.chat import (
    ChatInDB,
    # ChatCreate,
    # ChatUpdate,
)
from src.schemas.message import (
    MessageCreate,
)


async def process_chat(
    message_repository: MessageRepository,
    storage_api: StorageApi,
    identity: Identity,
    chat_id: int,
    topic: str,
    body: Optional[MessageCreate] = None,
):
    message_history = await message_repository.get_all(chat_id)
    if not message_history:
        message_history = list()
    # message_history=[
    #     message.message_history_for_chat_gpt()
    #     for message
    #     in message_history
    # ]
    message_history = list(
        chain.from_iterable(
            (
                message.message_history_for_chat_gpt()
                if isinstance(message.message_history_for_chat_gpt(), list)
                else [message.message_history_for_chat_gpt()]
            )
            for message in message_history
        )
    )
    # message_history = [
    #     item for item in message_history
    # ]
    if body:
        user_message = (
            await message_repository.create(
                chat_id,
                identity.profile.user_id,
                body,
            )
        ).message_history_for_chat_gpt()
    else:
        user_message = None
    prompt = (await storage_api.get_prompt(topic)).model_dump(exclude="topic")
    return message_history, user_message, None, prompt


async def on_stream_create(
    repository: MessageRepository,
    chat_id: int,
    user_uid: str,
    role: str,
    image_urls: Optional[List[str]] = None,
    content: Optional[List[str]] = None,
    tool_calls: Optional = None,
):
    return await repository.create(
        chat_id,
        user_uid,
        MessageCreate(
            role=role,
            content="".join(content),
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
            image_urls=image_urls,
        ),
    )


async def process_message(
    websocket: WebSocket,
    chat: ChatInDB,
    identity: Identity,
    storage_api: StorageApi,
    chat_repository: ChatRepository,
    message_repository: MessageRepository,
    body: Optional[MessageCreate] = None,
    toolkit: Optional[Dict[str, Callable]] = None,
):
    import logging

    (
        message_history,
        user_message,
        assistant_message,
        prompt,
    ) = await process_chat(
        message_repository,
        storage_api,
        identity,
        chat.id,
        chat.topic,
        body,
    )

    if user_message:
        await websocket.send_text(
            WSMessageOut(
                type=RespTypes.object,
                body=user_message,
            ).model_dump_json()
        )
    async for chunk in stream_completion(
        **prompt,
        message_history=message_history,
        user_prompt=[user_message] if user_message else [],
        on_stream_complete=partial(
            on_stream_create,
            message_repository,
            chat.id,
            identity.profile.user_id,
            "assistant",
        ),
        toolkit=toolkit,
    ):
        await websocket.send_json(
            {
                "type": "message_part",
                "body": {
                    "chat_id": chat.id,
                    # "message_id": ...,
                    "text": chunk,
                },
            }
        )
