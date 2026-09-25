"""The plugin MCP servers must start on both MCP Python SDK 1.x and 2.x.

SDK 2.x removed the ``Server.list_tools()`` / ``Server.call_tool()`` decorators.
Until 2026-09 every server used them inside ``serve()``, which no other test
executes, so a fresh install that resolved 2.x crashed at startup while this
suite stayed green. The servers now register through
``plugins.shared.mcp_compat.build_server``; these tests pin that and exercise
the adapter against whichever SDK is installed.
"""

import json
import re
from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from plugins.shared.mcp_compat import build_server, sdk2_handlers, uses_decorator_api

ROOT = Path(__file__).resolve().parent.parent
SERVERS = sorted(ROOT.glob("plugins/*/scripts/*_mcp.py"))


def test_there_are_plugin_servers_to_check():
    assert len(SERVERS) == 5


@pytest.mark.parametrize("server", SERVERS, ids=lambda p: p.parent.parent.name)
def test_server_registers_through_the_compat_builder(server):
    text = server.read_text(encoding="utf-8")
    assert not re.search(r"@\w+\.(list_tools|call_tool)\(\)", text), "1.x-only decorator API"
    assert re.search(r'build_server\("searchcarriers-[a-z-]+", list_tools, call_tool\)', text)


@pytest.mark.parametrize("server", SERVERS, ids=lambda p: p.parent.parent.name)
def test_requirement_allows_both_sdk_majors(server):
    req = (server.parent / "requirements.txt").read_text(encoding="utf-8")
    line = next(ln for ln in req.splitlines() if re.match(r"^mcp\b", ln.strip()))
    assert re.search(r"<\s*3\b", line.split("#")[0])


async def _list_tools():
    return [Tool(name="probe", description="probe tool", inputSchema={"type": "object"})]


async def _call_tool(name, arguments):
    if name == "boom":
        raise RuntimeError("handler exploded")
    return [TextContent(type="text", text=json.dumps({"name": name, "args": arguments}))]


def test_build_server_returns_a_named_server_on_the_installed_sdk():
    assert (
        build_server("searchcarriers-probe", _list_tools, _call_tool).name == "searchcarriers-probe"
    )


@pytest.mark.skipif(uses_decorator_api(), reason="SDK 1.x uses the decorator path")
async def test_sdk2_adapter_lists_and_calls_tools():
    from mcp.types import CallToolRequestParams

    on_list, on_call = sdk2_handlers(_list_tools, _call_tool)
    listed = await on_list(None, None)
    assert [t.name for t in listed.tools] == ["probe"]

    ok = await on_call(None, CallToolRequestParams(name="probe", arguments={"a": 1}))
    assert not ok.is_error
    assert json.loads(ok.content[0].text) == {"name": "probe", "args": {"a": 1}}

    bad = await on_call(None, CallToolRequestParams(name="boom", arguments=None))
    assert bad.is_error
    assert bad.content[0].text == "handler exploded"
