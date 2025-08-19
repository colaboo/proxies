import asyncio
import logging
from typing import List, Optional, Dict, Awaitable, Tuple
from math import ceil

# import aiohttp


import openai

# from openai._streaming import AsyncStream
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

import tiktoken

from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat.chat_completion_tool_choice_option_param import (
    ChatCompletionToolChoiceOptionParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition

from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall


from src.core.configs import openai_client, configs

from src.schemas.message import MessageInDB

from src.tools.exceptions import (
    get_exception_id,
    ExceptionMessage,
)


MAX_DEFAULT_USER_INPUT = 3_000
IMAGE_DETAIL_LEVEL = "high"
IMAGE_DEFAULT_SIZE = (2800, 2800)


def get_per_item_token_amount(model_name: str) -> Tuple[int, int, int]:
    if model_name in {
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06",
    }:
        return (3, 1, 85)


def get_context_length(model_name: str) -> int:
    match model_name:
        case "gpt-4o-2024-08-06":
            return 128_000
        case "gpt-4o-mini-2024-07-18":
            return 128_000
        case "gpt-3.5-turbo-0125":
            return 16_385
        case "gpt-3.5-turbo-1106":
            return 16_385
        case _:
            return 16_385


def get_max_output_tokens(
    model_name: str,
) -> int:
    match model_name:
        case "gpt-4o-2024-08-06":
            return 16_384
        case "gpt-4o-mini-2024-07-18":
            return 16_384
        case "gpt-3.5-turbo-0125":
            return 4_096
        case "gpt-3.5-turbo-1106":
            return 4_096
        case _:
            return 1_000


# def proxy_response_


def create_message_tokenized_object(object):
    result = dict()
    if object.get("role"):
        result["role"] = object.get("role")
    if object.get("name"):
        result["name"] = object.get("name")
    if object.get("content"):
        if isinstance(object.get("content"), list):
            result["content"] = object.get("content")[0]["text"]
            result["image"] = object.get("content")[1]["image_url"]
        else:
            result["content"] = object.get("content")
    return result


def count_image_tokens_usage(image_url) -> int:
    if IMAGE_DETAIL_LEVEL == "high":
        tiles = (IMAGE_DEFAULT_SIZE[0] * IMAGE_DEFAULT_SIZE[1]) / (512 * 512)
        return ceil(tiles * 170)
    if IMAGE_DETAIL_LEVEL == "low":
        return 0


def count_tokens(
    messages,
    model="gpt-4o-mini-2024-07-18",
):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError as e:
        logging.exception(e)
        encoding = tiktoken.get_encoding("o200k_base")
    tokens_per_message, tokens_per_name, tokens_per_image = get_per_item_token_amount(
        model
    )
    num_tokens = 0
    for message in map(create_message_tokenized_object, messages):
        num_tokens += tokens_per_message
        for key, value in message.items():
            if not value:
                continue
            if key == "image":
                num_tokens += tokens_per_image
                num_tokens += count_image_tokens_usage(value)
                continue
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3
    return num_tokens


class TooSmallContextWindow(Exception):
    pass


class ContextOutOfBounds(Exception):
    pass


class ChatComplitionCommonError(Exception):
    pass


def merge_and_shrink_context_if_needed(
    model: str,
    prompt_rules: List[Dict[str, str]],
    user_prompt: Dict[str, str],
    message_history: Optional[List[Dict[str, str]]] = None,
    max_tokens: Optional[int] = None,
    max_input_tokens: Optional[int] = None,
) -> List[Dict[str, str]]:
    if not max_tokens:
        max_tokens = get_max_output_tokens(model)
    if not max_input_tokens:
        max_input_tokens = get_context_length(model) - max_tokens

    tokens_in_prompt = count_tokens(prompt_rules)
    tokens_in_history = count_tokens(message_history)
    tokens_in_user_prompt = count_tokens(user_prompt)

    if (
        tokens_in_prompt + tokens_in_history + tokens_in_user_prompt
    ) < max_input_tokens:
        return prompt_rules + message_history + user_prompt
    if (tokens_in_prompt + tokens_in_user_prompt) > max_input_tokens:
        if tokens_in_user_prompt < MAX_DEFAULT_USER_INPUT:
            raise TooSmallContextWindow()
        raise ContextOutOfBounds()
    space_for_history = max_input_tokens - (tokens_in_prompt + tokens_in_user_prompt)
    message_history = shrink_from_begining(message_history, space_for_history, model)
    return prompt_rules + message_history + user_prompt


def shrink_from_begining(
    message_history: List[Dict[str, str]],
    space_for_history: int,
    model: str,
):
    total_tokens = count_tokens(message_history, model)
    while total_tokens > space_for_history and message_history:
        message_history.pop(0)
        total_tokens = count_tokens(message_history, model)
    return message_history


def gather_chunks(chunks: List[ChatCompletionChunk]):
    chunks = filter(
        lambda chunk: chunk.choices[0].delta.content is not None,
        chunks,
    )
    return [chunk.choices[0].delta.content for chunk in chunks]


async def stream_completion(
    prompt_rules: List[Dict[str, str]],
    *args,
    message_history: Optional[List[Dict[str, str]]] = None,
    user_prompt: Optional[List[Dict[str, str]]] = None,
    max_tokens: Optional[int] = None,
    max_input_tokens: Optional[int] = None,
    # on_stream_start: Optional[Awaitable] = None,
    on_stream_complete: Optional[Awaitable] = None,
    # on_stream_context: Optional[Dict] = None,
    model: Optional[str] = "gpt-4",
    toolkit: Optional[Dict[str, Awaitable]] = None,
    **kwargs,
):
    if not message_history:
        message_history = list()
    if not user_prompt:
        user_prompt = list()
    messages = merge_and_shrink_context_if_needed(
        model,
        prompt_rules,
        user_prompt,
        message_history,
        max_tokens,
        max_input_tokens,
    )
    try:
        stream = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            *args,
            stream=True,
            **kwargs,
            # tools=tools,
        )
        all_chunks = list()
        final_tool_calls: Dict[int, ChoiceDeltaToolCall] = dict()

        def process_tool_chunk(chunk: ChatCompletionChunk):
            for tool_call in chunk.choices[0].delta.tool_calls or []:
                index = tool_call.index
                if index not in final_tool_calls:
                    final_tool_calls[index] = tool_call
                final_tool_calls[
                    index
                ].function.arguments += tool_call.function.arguments

        async def process_tool_call():
            nonlocal final_tool_calls
            tool_call_results = list()
            if not toolkit:
                return
            for tool_call in final_tool_calls.values():
                on_tool_call = toolkit.get(tool_call.function.name)
                tool_call_results.append(
                    await on_tool_call(
                        tool_call,
                    )
                )
            finish_call_stack = toolkit.get("finish")
            await finish_call_stack(tool_call_results)

        def process_response_chunk(chunk: ChatCompletionChunk):
            if not chunk.choices[0].delta.content:
                return
            all_chunks.append(chunk)
            return chunk.choices[0].delta.content

        async def process_reponse():
            nonlocal all_chunks
            asyncio.create_task(
                on_stream_complete(
                    content=gather_chunks(all_chunks),
                    tool_calls=None,
                )
            )

        async for chunk in stream:
            process_tool_chunk(chunk)
            response = process_response_chunk(chunk)
            if response:
                yield response

        if final_tool_calls:
            await process_tool_call()
        if all_chunks:
            await process_reponse()

        if configs.DEBUG:
            logging.warning(str(stream))
            logging.warning(str(all_chunks))

    except Exception as e:
        raise ChatComplitionCommonError()


async def completion(
    prompt_rules: List[Dict[str, str]],
    # messages: List[Dict[str, str]],
    message_history: Optional[List[Dict[str, str]]] = None,
    user_prompt: Optional[Dict[str, str]] = None,
    max_tokens: Optional[int] = None,
    max_input_tokens: Optional[int] = None,
    model: Optional[str] = "gpt-4",
    *args,
    **kwargs,
) -> ChatCompletion:
    if not message_history:
        message_history = list()
    if not user_prompt:
        user_prompt = list()
    messages = merge_and_shrink_context_if_needed(
        model,
        prompt_rules,
        message_history,
        user_prompt,
        max_tokens,
        max_input_tokens,
    )
    chat_completion = await openai_client.chat.completions.create(
        model=model,
        messages=messages,
        *args,
        **kwargs,
    )
    if configs.DEBUG:
        logging.warning(str(chat_completion))
    return chat_completion


ORIGIN = "OPENAI"


def update_exception_with_response(message: ExceptionMessage, request, exception):
    message.detailed = exception.response.text


exceptions = {
    TooSmallContextWindow: ExceptionMessage(
        id=get_exception_id(ORIGIN, "toosmallinputwindow"),
        status=500,
        title="chat completion: context window too small",
        detailed=f"Context window restrictions setted for this prompt is \
            too small and can't handle both user input and prompt rules \
            while user input is of reasonable size ({MAX_DEFAULT_USER_INPUT})",
    ),
    ContextOutOfBounds: ExceptionMessage(
        id=get_exception_id(ORIGIN, "inputoutofbounds"),
        status=500,
        title="chat completion: input out of bounds",
        detailed=f"Input window restrictions setted for this prompt is \
            too small and can't handle both user input and prompt rules \
            while user input EXCEEDS reasanable size ({MAX_DEFAULT_USER_INPUT})",
    ),
    openai.BadRequestError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "badrequest"),
        status=500,
        title="chat completion: bad request to chat gpt api",
        update_func=update_exception_with_response,
    ),
    # ChatComplitionBadUrl:
    #     ExceptionMessage(
    #         id=get_exception_id(ORIGIN, 'badurl'),
    #         status=500,
    #         title='chat completion: bad image url',
    #         detailed="Image url format is wrong or resource is not accessable."
    #     ),
    ChatComplitionCommonError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "commonerror"),
        status=500,
        title="chat completion: common error",
        detailed="This is common (general) error for unhandled scenarious. Check server logs for more",
    ),
}
