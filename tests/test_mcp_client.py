"""
Unit tests for the MCPClient class.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.client.session import ClientSession
from mcp.types import CallToolResult

from src.tdd_harness.mcp_client import MCPClient


@pytest.fixture
def mock_stdio_client():
    """Mock the stdio_client context manager."""
    with patch("src.tdd_harness.mcp_client.stdio_client") as mock:
        # stdio_client returns an async context manager yielding (read, write)
        ctx = AsyncMock()
        ctx.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock.return_value = ctx
        yield mock


@pytest.fixture
def mock_client_session():
    """Mock the ClientSession context manager."""
    with patch("src.tdd_harness.mcp_client.ClientSession") as mock:
        session = AsyncMock(spec=ClientSession)

        ctx = AsyncMock()
        ctx.__aenter__.return_value = session
        mock.return_value = ctx
        yield session


@pytest.mark.asyncio
async def test_empty_config_returns_gracefully():
    """Test that an empty config does not attempt connection."""
    client = MCPClient({})
    await client.connect()
    assert client.session is None

    tools = await client.get_tools()
    assert tools == []

    result = await client.call_tool("test_tool", {"arg": "val"})
    assert result == {}


@pytest.mark.asyncio
async def test_connect_success(mock_stdio_client, mock_client_session):
    """Test successful connection initialization."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "exit"}
    client = MCPClient(config)

    await client.connect()

    assert client.session is not None
    mock_client_session.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_tools_success(mock_stdio_client, mock_client_session):
    """Test retrieving tools correctly parses tools into dicts."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "exit"}
    client = MCPClient(config)
    await client.connect()

    # Setup mock tool response
    tool_mock = MagicMock()
    tool_mock.model_dump.return_value = {"name": "test_tool", "description": "A test tool"}

    result_mock = MagicMock()
    result_mock.tools = [tool_mock]
    mock_client_session.list_tools.return_value = result_mock

    tools = await client.get_tools()

    assert tools == [{"name": "test_tool", "description": "A test tool"}]
    mock_client_session.list_tools.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_tool_success(mock_stdio_client, mock_client_session):
    """Test calling a tool successfully."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "exit"}
    client = MCPClient(config)
    await client.connect()

    mock_result = CallToolResult(content=[], isError=False)
    mock_client_session.call_tool.return_value = mock_result

    result = await client.call_tool("test_tool", {"arg": "val"})

    assert result is mock_result
    mock_client_session.call_tool.assert_awaited_once_with("test_tool", arguments={"arg": "val"})


@pytest.mark.asyncio
async def test_call_tool_failure(mock_stdio_client, mock_client_session):
    """Test calling a tool that raises an exception."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "exit"}
    client = MCPClient(config)
    await client.connect()

    mock_client_session.call_tool.side_effect = Exception("Tool error")

    with patch.object(client, "handle_failure") as mock_handle:
        with pytest.raises(Exception, match="Tool error"):
            await client.call_tool("test_tool", {"arg": "val"})
        mock_handle.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.tdd_harness.mcp_client.sys.exit")
@patch("src.tdd_harness.mcp_client.print")
async def test_handle_failure_exit_policy(mock_print, mock_exit, mock_stdio_client, mock_client_session):
    """Test failure with exit policy terminates process."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "exit"}
    client = MCPClient(config)

    # Make initialize fail
    mock_client_session.initialize.side_effect = Exception("Test error")

    await client.connect()

    mock_exit.assert_called_once_with(1)
    mock_print.assert_called_once()


@pytest.mark.asyncio
async def test_handle_failure_on_failure_policy(mock_stdio_client, mock_client_session):
    """Test on-failure policy attempts reconnection exactly once."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "on-failure"}
    client = MCPClient(config)

    # Track calls to close and connect
    with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
        # First initialize fails, second succeeds
        mock_client_session.initialize.side_effect = [Exception("Test error"), None]

        await client.connect()

        # Should have called close and reconnect once
        mock_close.assert_awaited_once()
        assert client._retry_count == 0  # Resets on success


@pytest.mark.asyncio
async def test_handle_failure_on_failure_policy_exhausted(mock_stdio_client, mock_client_session):
    """Test on-failure policy fails permanently after one retry."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "on-failure"}
    client = MCPClient(config)

    # Track calls to close and print
    with (
        patch.object(client, "close", new_callable=AsyncMock) as mock_close,
        patch("src.tdd_harness.mcp_client.print") as mock_print,
    ):
        # Fails both times
        mock_client_session.initialize.side_effect = Exception("Test error")

        await client.connect()

        # Reconnected once, failed again, printed error
        mock_close.assert_awaited_once()
        mock_print.assert_called_once()
        assert client._retry_count == 1


@pytest.mark.asyncio
@patch("src.tdd_harness.mcp_client.asyncio.sleep", new_callable=AsyncMock)
async def test_handle_failure_always_policy(mock_sleep, mock_stdio_client, mock_client_session):
    """Test always policy retries continuously."""
    config = {"command": "echo", "args": ["hello"], "restart_policy": "always"}
    client = MCPClient(config)

    with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
        # Fails first time, succeeds second
        mock_client_session.initialize.side_effect = [Exception("Test error"), None]

        await client.connect()

        mock_sleep.assert_awaited_once_with(1)
        mock_close.assert_awaited_once()
        assert client._retry_count == 0  # Resets on success


@pytest.mark.asyncio
@patch("src.tdd_harness.mcp_client.sys.exit")
@patch("src.tdd_harness.mcp_client.print")
async def test_handle_failure_masks_secrets(mock_print, mock_exit, mock_stdio_client, mock_client_session):
    """Test that API keys in env are redacted from error messages."""
    config = {
        "command": "echo",
        "args": ["hello"],
        "restart_policy": "exit",
        "env": {"OPENAI_API_KEY": "supersecretkey123", "SAFE_VAR": "hello"},
    }
    client = MCPClient(config)

    # Force an error containing the secret
    mock_client_session.initialize.side_effect = Exception("Command failed with supersecretkey123 and SAFE_VAR=hello")

    await client.connect()

    mock_exit.assert_called_once_with(1)
    mock_print.assert_called_once()

    printed_msg = mock_print.call_args[0][0]
    assert "supersecretkey123" not in printed_msg
    assert "***" in printed_msg
    assert "SAFE_VAR=hello" in printed_msg
