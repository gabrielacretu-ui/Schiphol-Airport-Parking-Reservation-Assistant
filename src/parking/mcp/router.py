"""
MCP client router — LLM picks the right tool; execution goes through MCP stdio protocol.

Usage:
    from parking.mcp import route_and_execute_mcp_tool

    route_and_execute_mcp_tool(validated_dict)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from .server import make_reservation, cancel_reservation, modify_reservation

# ---------------------------------------------------------------------------
# Subprocess configuration — server.py is launched via `python -m` so that
# relative imports inside the package work correctly.
# ---------------------------------------------------------------------------
_PROJECT_SRC = str(Path(__file__).parent.parent.parent)  # .../src
_subprocess_env = {
    **os.environ,
    "PYTHONPATH": os.pathsep.join(
        filter(None, [_PROJECT_SRC, os.environ.get("PYTHONPATH", "")])
    ),
}
_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "parking.mcp.server"],
    env=_subprocess_env,
)

# ---------------------------------------------------------------------------
# Tool descriptors — give the LLM schemas to choose from.
# The functions are only used for type inference; they are never called here.
# ---------------------------------------------------------------------------
_mcp_tools = [
    StructuredTool.from_function(
        func=make_reservation,
        name="make_reservation",
        description="Make a new parking reservation. Use when the operation is 'making'.",
    ),
    StructuredTool.from_function(
        func=cancel_reservation,
        name="cancel_reservation",
        description="Cancel an existing parking reservation. Use when the operation is 'cancelling'.",
    ),
    StructuredTool.from_function(
        func=modify_reservation,
        name="modify_reservation",
        description="Modify an existing parking reservation. Use when the operation is 'modifying'.",
    ),
]

_router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(_mcp_tools)


# ---------------------------------------------------------------------------
# Internal async call — spawns server subprocess and calls the tool
# ---------------------------------------------------------------------------
async def _call_mcp_tool(tool_name: str, arguments: dict):
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.isError:
                raise RuntimeError(
                    f"MCP tool '{tool_name}' failed: {[c.text for c in result.content]}"
                )
            return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def route_and_execute_mcp_tool(validated_dict: dict) -> None:
    """LLM selects the correct MCP tool; executes it via the stdio protocol."""
    response = _router_llm.invoke(
        f"Execute the following reservation operation using the appropriate tool:\n"
        f"{json.dumps(validated_dict)}"
    )
    if not response.tool_calls:
        print("Warning: LLM did not select a tool. No reservation action taken.")
        return
    for tool_call in response.tool_calls:
        print(f"Routing to MCP tool: {tool_call['name']} with args: {tool_call['args']}")
        asyncio.run(_call_mcp_tool(tool_call["name"], tool_call["args"]))
