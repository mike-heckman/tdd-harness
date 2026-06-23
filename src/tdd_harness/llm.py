"""
LLM Client implementation.
"""

import json

from openai import AsyncOpenAI

from .config import load_prompt_config
from .context import Context, ContextBuilder, ContextType


class LLMClient:
    """
    Client for communicating with the configured LLM API.
    """

    def __init__(
        self, config_loader: object, prompt: object, context_builder: ContextBuilder
    ):  # Reason: Avoid circular imports and complex mock typings
        """
        Initializes the LLMClient.

        Args:
            config_loader: The configuration loader.
            prompt: The prompt manager.
            context_builder: The context builder instance.
        """
        self.config_loader = config_loader
        self.prompt = prompt
        self.context_builder = context_builder
        self.config = config_loader.get_config()  # type: ignore
        self.llm_config = self.config.llm

        # Check/fetch configuration values
        self.client = AsyncOpenAI(api_key=self.llm_config.get("api_key"), base_url=self.llm_config.get("base_url"))  # type: ignore
        errors: list = []
        self._model = self.llm_config.get("model", None)
        if not self._model:
            errors.append("Model not specified in LLM configuration")

        self._context_size = self.llm_config.get("context_size", None)
        if not self._context_size:
            errors.append("Context size not specified in LLM configuration")

        self._minimum_available_context = self.llm_config.get("minimum_available_context", None)
        if not self._minimum_available_context:
            errors.append("Minimum available context not specified in LLM configuration")

        self._keep_turns = self.llm_config.get("keep_turns", None)
        if not self._keep_turns:
            errors.append("Keep turns not specified in LLM configuration")

        if errors:
            raise ValueError("\n".join(errors))

    async def _compress_history(self, flat_history: list[Context], new_contexts: list[Context]) -> None:
        """
        Compresses the active conversation history when token limits are reached.
        """
        flat_dicts = [c.as_openai_message() for c in flat_history]
        new_dicts = [c.as_openai_message() for c in new_contexts]

        comp_config = load_prompt_config("compression_prompt")
        comp_messages = [
            {"role": "system", "content": comp_config.prompt},
            {
                "role": "user",
                "content": f"Summarize the following history: {flat_dicts}\nNew messages: {new_dicts}",
            },
        ]

        comp_response = await self.client.chat.completions.create(
            model=self._model,
            messages=comp_messages,  # type: ignore
        )
        summary = comp_response.choices[0].message.content or ""

        summary_ctx = Context(text=f"Previous conversation summary: {summary}", context_type=ContextType.CHAT_HISTORY)

        # Replace the entire flat_history block in ContextBuilder with the new summary
        context_ids = [c.id for c in flat_history]
        self.context_builder.replace_with_summary(context_ids, summary_ctx.text)

    async def _handle_tool_calls(
        self, msg: object, messages: list[dict], current_turn: list[Context], registry: object | None
    ) -> None:
        """
        Executes requested tool calls and appends the results to the conversation.
        """
        msg_dict = msg.model_dump(exclude_none=True)  # type: ignore
        messages.append(msg_dict)

        metadata = {}
        tool_calls = getattr(msg, "tool_calls", [])
        if tool_calls:
            metadata["tool_calls"] = [t.model_dump() for t in tool_calls]

        assistant_ctx = Context(
            text=getattr(msg, "content", "") or "",
            context_type=ContextType.CHAT_HISTORY,
            metadata=metadata,
        )
        current_turn.append(assistant_ctx)

        for tool_call in tool_calls:  # type: ignore
            func = tool_call.function
            name = str(func.name)
            args = json.loads(func.arguments)

            content = "Tool executed."
            if registry:
                try:
                    res = await registry.dispatch(name, args)  # type: ignore
                    content = str(res.content) if res.success else f"Error: {res.error}"
                except Exception as e:
                    content = f"Error executing tool: {e}"

            tool_msg = {"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": content}
            messages.append(tool_msg)

            tool_ctx = Context(
                text=content,
                context_type=ContextType.TOOL_RESULT,
                metadata={"tool_call_id": tool_call.id, "name": name},
            )
            current_turn.append(tool_ctx)

    async def chat(
        self, contexts: list[Context], tools: list[dict] | None = None, registry: object | None = None
    ) -> str | None:  # Reason: Could return None on error
        """
        Sends messages to the LLM, handling context compression, tool calls, and baseline caching.

        Args:
            contexts: A list of Context objects.
            tools: Optional list of OpenAI-compatible tool schemas.
            registry: Optional tool registry for executing tool calls.
        """
        cb = self.context_builder

        # Add incoming contexts if they aren't already in the builder
        for c in contexts:
            if c not in cb.get_context():
                cb.add_context(c)

        system_context = self.prompt.get_system_message(model=self._model)  # type: ignore
        system_tokens = system_context.token_count or 0

        incoming_tokens = sum((c.token_count or max(1, len(c.text) // 4)) for c in contexts)
        if (self._context_size - (system_tokens + incoming_tokens)) < self._minimum_available_context:
            raise RuntimeError("Context Exhausted: Static context (system + task) exceeds available room.")

        # Current snapshot of the entire conversation block
        flat_history = cb.get_context()
        history_tokens = sum((c.token_count or max(1, len(c.text) // 4)) for c in flat_history)

        remaining_context = self._context_size - (system_tokens + incoming_tokens + history_tokens)

        if remaining_context < self._minimum_available_context:
            await self._compress_history(flat_history, contexts)
            flat_history = cb.get_context()

        messages = [{"role": "system", "content": system_context.text}]
        messages.extend(c.as_openai_message() for c in flat_history)

        # Note: the input contexts are already inside flat_history because we added them above

        current_turn = []
        final_content = None
        max_loops = 5

        for _ in range(max_loops):
            kwargs = {
                "model": self._model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = await self.client.chat.completions.create(**kwargs)  # type: ignore
            msg = response.choices[0].message

            if system_tokens == 0 and response.usage:
                self.prompt.update_token_size(self._model, response.usage.prompt_tokens)  # type: ignore
                system_tokens = response.usage.prompt_tokens

            if getattr(msg, "tool_calls", None):
                await self._handle_tool_calls(msg, messages, current_turn, registry)
            else:
                final_content = msg.content
                if msg.content:
                    assistant_msg = {"role": "assistant", "content": msg.content}
                    messages.append(assistant_msg)

                    assistant_ctx = Context(text=msg.content, context_type=ContextType.CHAT_HISTORY)
                    current_turn.append(assistant_ctx)
                break

        # Native addition of tool executions and assistant responses to global ContextBuilder
        for ctx in current_turn:
            cb.add_context(ctx)

        # Enforce keep_turns across the entire history based on assistant turns
        all_assistant_turns = cb.get_context([ContextType.CHAT_HISTORY])
        if len(all_assistant_turns) > self._keep_turns:
            # Simple heuristic: remove older assistant/tool responses until we are under the keep_turns limit
            # This replaces the naive list slicing previously maintained locally
            limit = len(all_assistant_turns) - self._keep_turns
            for ctx_to_remove in all_assistant_turns[:limit]:
                cb.remove_context(ctx_to_remove.id)

        return final_content
