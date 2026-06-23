"""
Central registry of LLM tool schemas and their valid phases.
"""

from typing import Any

AVAILABLE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_symbols",
            "description": "Search for symbols across the project.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        "valid_phases": ["blue", "red", "green", "magenta"],
    },
    {
        "type": "function",
        "function": {
            "name": "get_symbol_source",
            "description": "Get the source code of a specific symbol.",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        },
        "valid_phases": ["blue", "red", "green", "magenta"],
    },
    {
        "type": "function",
        "function": {
            "name": "ask_researcher",
            "description": "Ask the Research Sub-Agent a question.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        "valid_phases": ["blue", "red", "green", "magenta"],
    },
    {
        "type": "function",
        "function": {
            "name": "stage_implementation",
            "description": "Stage an implementation for the Blue or Green phase.",
            "parameters": {
                "type": "object",
                "properties": {"filepath": {"type": "string"}, "code": {"type": "string"}},
                "required": ["filepath", "code"],
            },
        },
        "valid_phases": ["blue", "green"],
    },
    {
        "type": "function",
        "function": {
            "name": "stage_test_implementation",
            "description": "Stage a test implementation for the Red phase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                    "code": {"type": "string"},
                    "test_name": {"type": "string"},
                    "test_concept": {"type": "string"},
                },
                "required": ["filepath", "code", "test_name", "test_concept"],
            },
        },
        "valid_phases": ["red", "magenta"],
    },
    {
        "type": "function",
        "function": {
            "name": "success",
            "description": "Signal that the phase is successfully completed.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        },
        "valid_phases": ["blue", "red", "green", "magenta"],
    },
    {
        "type": "function",
        "function": {
            "name": "abort",
            "description": "Abort the phase execution.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
        "valid_phases": ["blue", "red", "green", "magenta"],
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        "valid_phases": ["blue", "red", "green", "magenta"],
    },
]


def get_tools_for_phase(phase_value: str) -> list[dict[str, Any]]:
    """
    Returns a list of OpenAI function schemas valid for the given phase.
    """
    return [
        {"type": t["type"], "function": t["function"]}
        for t in AVAILABLE_TOOLS
        if phase_value in t.get("valid_phases", [])
    ]
