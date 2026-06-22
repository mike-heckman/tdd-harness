"""
Sub-agents for TDD Harness.
"""

from src.tdd_harness.context import Context, ContextType
from src.tdd_harness.llm import LLMClient
from src.tdd_harness.prompt import Prompt
from src.tdd_harness.registry import ToolRegistry


class ReviewSubAgent:
    """
    Sub-agent responsible for reviewing implemented code against the original task definition.

    Design Pattern: Single Responsibility Principle (SRP) / Facade
    Isolates the review LLM logic into a dedicated component.
    """

    def __init__(self, llm_client: LLMClient, prompt: Prompt | None = None) -> None:
        """
        Initialize the ReviewSubAgent.

        Args:
            llm_client: The shared LLMClient instance.
            prompt: The prompt configuration to use.
        """
        self.llm_client = llm_client
        self.prompt = prompt or Prompt("review_prompt")

    async def review(
        self, task_content: str, modified_files_list: str, unified_diff: str, registry: ToolRegistry
    ) -> str:
        """
        Review the changes and return APPROVE or REJECT.
        """
        sys_msg = self.prompt.get_system_message(self.llm_client._model)
        user_content = (
            f"Task File:\n{task_content}\n\nModified Files:\n{modified_files_list}\n\nUnified Diff:\n{unified_diff}"
        )

        contexts = [
            Context(text=sys_msg.text, context_type=ContextType.SYSTEM),
            Context(text=user_content, context_type=ContextType.TASK_CONTEXT),
        ]

        tools = []
        for schema in registry.get_openai_schemas():
            name = schema["function"]["name"]
            if name in ("get_file_content", "get_symbol_source"):
                tools.append(schema)

        response = await self.llm_client.chat(contexts, tools=tools, registry=registry)
        return response or "APPROVE"


class PostMortemSubAgent:
    """
    Sub-agent responsible for generating post-mortem summaries of test and linter failures.

    Design Pattern: Single Responsibility Principle (SRP) / Facade
    Isolates the post-mortem analysis LLM logic into a dedicated component.
    """

    def __init__(self, llm_client: LLMClient, prompt: Prompt | None = None) -> None:
        """
        Initialize the PostMortemSubAgent.

        Args:
            llm_client: The shared LLMClient instance.
            prompt: The prompt configuration to use.
        """
        self.llm_client = llm_client
        self.prompt = prompt or Prompt("post_mortem_prompt")

    async def generate(self, filepath: str, code: str, raw_error: str) -> str:
        """
        Analyze the failure and return a root cause summary and guidance.
        """
        sys_msg = self.prompt.get_system_message(self.llm_client._model)
        prompt_text = sys_msg.text.format(filepath=filepath, code=code, raw_error=raw_error)

        contexts = [Context(text=prompt_text, context_type=ContextType.TASK_CONTEXT)]

        response = await self.llm_client.chat(contexts)
        return response or "Failed to generate post-mortem."


class ResearchSubAgent:
    """
    Sub-agent responsible for researching user queries using MCP tools.

    Design Pattern: Single Responsibility Principle (SRP) / Facade
    Isolates the research LLM logic into a dedicated component.
    """

    def __init__(self, llm_client: LLMClient, prompt: Prompt | None = None) -> None:
        """
        Initialize the ResearchSubAgent.

        Args:
            llm_client: The shared LLMClient instance.
            prompt: The prompt configuration to use.
        """
        self.llm_client = llm_client
        self.prompt = prompt or Prompt("research_prompt")

    async def ask(self, query: str, registry: ToolRegistry) -> str:
        """
        Investigate a query and return a concise technical summary.
        """
        sys_msg = self.prompt.get_system_message(self.llm_client._model)

        contexts = [
            Context(text=sys_msg.text, context_type=ContextType.SYSTEM),
            Context(text=query, context_type=ContextType.TASK_CONTEXT),
        ]

        tools = []
        for schema in registry.get_openai_schemas():
            tool_name = schema["function"]["name"]
            if registry.tools[tool_name].type.value == "mcp" or tool_name in ["search_web", "download_to_reference"]:
                tools.append(schema)

        response = await self.llm_client.chat(contexts, tools=tools, registry=registry)
        return response or "Research loop maxed out without a final summary."
