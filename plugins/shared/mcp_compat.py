"""Build an MCP ``Server`` that works on both the 1.x and 2.x Python SDKs.

SDK 1.x registers tool handlers with the ``Server.list_tools()`` /
``Server.call_tool()`` decorators. SDK 2.x removed them: handlers are passed to
the ``Server`` constructor as ``on_list_tools(ctx, params) -> ListToolsResult``
and ``on_call_tool(ctx, params) -> CallToolResult``. Every plugin server keeps
its plain ``list_tools()`` / ``call_tool(name, arguments)`` coroutines and hands
them to :func:`build_server`, so the SDK version is the only thing this module
has to know about.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

ListTools = Callable[[], Awaitable[list[Tool]]]
CallTool = Callable[[str, dict[str, Any]], Awaitable[list[TextContent]]]


def uses_decorator_api() -> bool:
    """True when the installed SDK still has the 1.x decorator registration API."""
    return hasattr(Server, "list_tools") and hasattr(Server, "call_tool")


def sdk2_handlers(list_tools: ListTools, call_tool: CallTool) -> tuple[Any, Any]:
    """Wrap the plain handlers in the SDK 2.x ``(ctx, params) -> Result`` shape."""
    from mcp.types import CallToolResult, ListToolsResult

    async def on_list_tools(ctx: Any, params: Any) -> ListToolsResult:
        return ListToolsResult(tools=await list_tools())

    async def on_call_tool(ctx: Any, params: Any) -> CallToolResult:
        # The 1.x decorator turned a raised exception into an is_error result;
        # keep that contract instead of surfacing a protocol error.
        try:
            content = await call_tool(params.name, dict(params.arguments or {}))
        except Exception as exc:  # noqa: BLE001 - mirrored 1.x behaviour
            return CallToolResult(content=[TextContent(type="text", text=str(exc))], is_error=True)
        return CallToolResult(content=content)

    return on_list_tools, on_call_tool


def build_server(name: str, list_tools: ListTools, call_tool: CallTool) -> Server:
    """Return a ``Server`` named ``name`` wired to the given handlers."""
    if uses_decorator_api():
        server = Server(name)
        server.list_tools()(list_tools)
        server.call_tool()(call_tool)
        return server

    on_list_tools, on_call_tool = sdk2_handlers(list_tools, call_tool)
    return Server(name, on_list_tools=on_list_tools, on_call_tool=on_call_tool)
