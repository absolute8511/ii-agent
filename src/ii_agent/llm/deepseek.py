"""LLM client for Deepseek models."""

import json
import os
import random
import time
from typing import Any, Tuple, cast
import openai
import logging



from openai import (
    APIConnectionError as OpenAI_APIConnectionError,
)
from openai import (
    InternalServerError as OpenAI_InternalServerError,
)
from openai import (
    RateLimitError as OpenAI_RateLimitError,
)
from openai._types import (
    NOT_GIVEN as OpenAI_NOT_GIVEN,  # pyright: ignore[reportPrivateImportUsage]
)

from ii_agent.core.config.llm_config import LLMConfig
from ii_agent.llm.base import (
    LLMClient,
    AssistantContentBlock,
    LLMMessages,
    ToolParam,
    TextPrompt,
    ToolCall,
    TextResult,
    ToolFormattedResult,
    ImageBlock,
)

logger = logging.getLogger(__name__)
MAX_DEEPSEEK_DETAIL_LOG_LEN = 200

class DeepseekDirectClient(LLMClient):
    """Use Deepseek models via first party API."""

    def __init__(self, llm_config: LLMConfig):
        """Initialize the Deepseek first party client."""
        base_url = llm_config.base_url or "https://api.deepseek.com/v1"
        self.client = openai.OpenAI(
            api_key=llm_config.api_key.get_secret_value() if llm_config.api_key else None,
            base_url=base_url,
            max_retries=llm_config.max_retries,
        )
        self.model_name = llm_config.model
        self.max_retries = llm_config.max_retries

    def generate(
        self,
        messages: LLMMessages,
        max_tokens: int,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        tools: list[ToolParam] = [],
        tool_choice: dict[str, str] | None = None,
        thinking_tokens: int | None = None,
    ) -> Tuple[list[AssistantContentBlock], dict[str, Any]]:
        """Generate responses.

        Args:
            messages: A list of messages.
            system_prompt: A system prompt.
            max_tokens: The maximum number of tokens to generate.
            temperature: The temperature.
            tools: A list of tools.
            tool_choice: A tool choice.

        Returns:
            A generated response.
        """

        openai_messages = []
        if system_prompt is not None:
            system_message = {"role": "system", "content": system_prompt}
            openai_messages.append(system_message)

        tool_call_outputs = {}
        assistant_messages_with_tool_calls = []

        for idx, message_list in enumerate(messages):
            tool_calls_in_turn = [m for m in message_list if isinstance(m, ToolCall)]
            other_messages_in_turn = [m for m in message_list if not isinstance(m, ToolCall)]

            if tool_calls_in_turn:
                openai_tool_calls = []
                for tool_call in tool_calls_in_turn:
                    try:
                        arguments_str = json.dumps(tool_call.tool_input)
                    except TypeError as e:
                        logger.error(f"Failed to serialize tool_input for {tool_call.tool_name}: {e}")
                        continue

                    tool_call_id = tool_call.tool_call_id
                    log_args = arguments_str if len(arguments_str) <= MAX_DEEPSEEK_DETAIL_LOG_LEN else arguments_str[:MAX_DEEPSEEK_DETAIL_LOG_LEN] + "..."
                    logger.info(f"deepseek got Tool call id: {tool_call_id}, tool name: {tool_call.tool_name}, arguments: {log_args}")
                    openai_tool_calls.append({
                        "type": "function",
                        "id": tool_call_id,
                        "function": {
                            "name": tool_call.tool_name,
                            "arguments": arguments_str,
                        },
                    })
                if openai_tool_calls:
                    assistant_message = {"role": "assistant", "tool_calls": openai_tool_calls}
                    openai_messages.append(assistant_message)
                    assistant_messages_with_tool_calls.append(assistant_message)

            for msg in other_messages_in_turn:
                if isinstance(msg, ToolFormattedResult):
                    tool_call_outputs[msg.tool_call_id] = msg.tool_output
                    json_output = json.dumps(msg.tool_output)
                    log_output = json_output if len(json_output) <= MAX_DEEPSEEK_DETAIL_LOG_LEN else json_output[:MAX_DEEPSEEK_DETAIL_LOG_LEN] + "..."
                    logger.info(f"deepseek got Tool output in turn id: {msg.tool_call_id}, tool name: {msg.tool_name}, output: {log_output}")
                else:
                    role = "user" if isinstance(msg, (TextPrompt, ImageBlock)) else "assistant"
                    content = None
                    if isinstance(msg, TextPrompt):
                        content = msg.text
                    elif isinstance(msg, ImageBlock):
                        image_url_data = {}
                        if "url" in msg.source:
                            image_url_data["url"] = msg.source["url"]
                        elif "data" in msg.source:
                            media_type = msg.source.get("media_type", "image/png")
                            image_url_data["url"] = f"data:{media_type};base64,{msg.source['data']}"
                        content = [{"type": "image_url", "image_url": image_url_data}]
                    elif isinstance(msg, TextResult):
                        content = msg.text
                    else:
                        continue

                    if content is not None:
                        if isinstance(content, list):
                            openai_messages.append({"role": role, "content": content})
                        else:
                            openai_messages.append({"role": role, "content": content})

        # Insert tool messages right after the assistant messages with tool_calls
        for assistant_message in assistant_messages_with_tool_calls:
            tool_call_ids = [tool_call["id"] for tool_call in assistant_message["tool_calls"]]
            insert_index = openai_messages.index(assistant_message) + 1
            for tool_call_id in tool_call_ids:
                if tool_call_id in tool_call_outputs:
                    tool_output = tool_call_outputs[tool_call_id]
                    if not isinstance(tool_output, str):
                        try:
                            tool_output = json.dumps(tool_output)
                        except TypeError as e:
                            logger.error(f"Failed to serialize tool output for {tool_call_id}: {e}")
                            continue
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": tool_output
                    }
                    openai_messages.insert(insert_index, tool_message)
                    insert_index += 1
                else:
                    logger.warning(f"Missing tool output for tool_call_id: {tool_call_id}")

        if tool_choice is None:
            tool_choice_param = "auto"
        elif tool_choice["type"] == "any":
            tool_choice_param = "required"
        elif tool_choice["type"] == "auto":
            tool_choice_param = "auto"
        elif tool_choice["type"] == "tool":
            tool_choice_param = {
                "type": "function",
                "function": {"name": tool_choice["name"]},
            }
        else:
            raise ValueError(f"Unknown tool_choice type: {tool_choice['type']}")

        openai_tools = []
        for tool in tools:
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            }
            tool_def["parameters"]["strict"] = True
            openai_tool_object = {
                "type": "function",
                "function": tool_def,
            }
            openai_tools.append(openai_tool_object)

        response = None
        logger.info(f"Request to Deepseek model: {self.model_name} and tool_choice: {tool_choice_param}")
        for retry in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=openai_messages,
                    tools=openai_tools if len(openai_tools) > 0 else OpenAI_NOT_GIVEN,
                    tool_choice=tool_choice_param,
                    max_tokens=max_tokens,
                )
                break
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from Deepseek response: {e}")
                if retry == self.max_retries - 1:
                    raise e
                else:
                    logger.warning(f"Retrying Deepseek request: {retry + 1}/{self.max_retries}")
                    time.sleep(10 * random.uniform(0.8, 1.2))
            except (
                OpenAI_APIConnectionError,
                OpenAI_InternalServerError,
                OpenAI_RateLimitError,
            ) as e:
                if retry == self.max_retries - 1:
                    logger.error(f"Failed Deepseek request after {retry + 1} retries: {str(e)}")
                    raise e
                else:
                    logger.warning(f"Retrying Deepseek request: {retry + 1}/{self.max_retries}")
                    time.sleep(10 * random.uniform(0.8, 1.2))
            except Exception as e:
                logger.error(f"Unexpected error during Deepseek request: {str(e)}")
                raise e

        internal_messages = []
        assert response is not None
        openai_response_messages = response.choices
        if len(openai_response_messages) > 1:
            raise ValueError("Only one message supported for Deepseek")
        openai_response_message = openai_response_messages[0].message
        tool_calls = openai_response_message.tool_calls
        content = openai_response_message.content

        if not tool_calls and not content:
            raise ValueError("Either tool_calls or content should be present")

        if content:
            internal_messages.append(TextResult(text=content))

        if tool_calls:
            available_tool_names = {t.name for t in tools}
            logger.info(f"Model returned {len(tool_calls)} tool_calls. Available tools: {available_tool_names}")
            
            processed_tool_call = False
            for tool_call_data in tool_calls:
                tool_name_from_model = tool_call_data.function.name
                if tool_name_from_model and tool_name_from_model in available_tool_names:
                    logger.info(f"Attempting to process tool call: {tool_name_from_model}")
                    try:
                        args_data = tool_call_data.function.arguments
                        if isinstance(args_data, dict):
                            tool_input = args_data
                        elif isinstance(args_data, str):
                            tool_input = json.loads(args_data)
                        else:
                            logger.error(f"Tool arguments for '{tool_name_from_model}' are not a valid format (string or dict): {args_data}")
                            continue

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON arguments for tool '{tool_name_from_model}': {tool_call_data.function.arguments}. Error: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error parsing arguments for tool '{tool_name_from_model}': {str(e)}")
                        continue
                    logger.info(f" tool call: {tool_name_from_model}, tool input: {tool_input}")
                    internal_messages.append(
                        ToolCall(
                            tool_name=tool_name_from_model,
                            tool_input=tool_input,
                            tool_call_id=tool_call_data.id,
                        )
                    )
                    processed_tool_call = True
                    logger.info(f"Successfully processed and selected tool call: {tool_name_from_model}")
                else:
                    logger.warning(f"Skipping tool call with unknown or placeholder name: '{tool_name_from_model}'. Not in available tools: {available_tool_names}")
            
            if not processed_tool_call:
                logger.warning("No valid and available tool calls found after filtering.")

        assert response.usage is not None
        message_metadata = {
            "raw_response": response,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }

        return internal_messages, message_metadata
