"""
Tests for tool schemas registry.
"""

from src.tdd_harness.tool_schemas import get_tools_for_phase


def test_read_file_in_all_active_phases():
    """
    Test that the read_file tool is present in the schemas returned by get_tools_for_phase()
    for blue, red, green, and magenta phases.
    """
    phases = ["blue", "red", "green", "magenta"]
    for phase in phases:
        tools = get_tools_for_phase(phase)
        tool_names = [t["function"]["name"] for t in tools]
        assert "read_file" in tool_names, f"read_file tool missing in phase {phase}"

        # Verify read_file schema
        read_file_tool = next(t for t in tools if t["function"]["name"] == "read_file")
        assert "path" in read_file_tool["function"]["parameters"]["properties"]
        assert "path" in read_file_tool["function"]["parameters"]["required"]
