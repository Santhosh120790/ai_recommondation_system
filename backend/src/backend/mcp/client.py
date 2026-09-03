"""MCP client: connects to the server as a subprocess over stdio, declares a
permitted filesystem root, and proxies server-delegated LLM calls (sampling)
through the AICredits gateway. This is what the FastAPI app / LangGraph agent
tool layer actually talks to.
"""

import logging
import sys
from contextlib import AsyncExitStack

import mcp_types as types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.core.config import get_settings
from backend.core.llm import get_raw_client

logger = logging.getLogger(__name__)

# Guardrail: tools the LangGraph agents are allowed to call autonomously.
# Deliberately excludes add_restaurant / delete_restaurant — those stay
# reachable only from the FastAPI CRUD routers, driven by an explicit human
# action in the UI (which is itself confirm-gated). No amount of prompt
# injection or agent reasoning can make the graph reach a write tool: it's
# not just gated on confirm=True, it isn't in the callable set at all.
AGENT_SAFE_TOOLS = frozenset(
    {
        "get_restaurant_info",
        "recommend_by_vibe",
        "get_review",
        "search_restaurants",
        "search_food_images",
        "fuse_search",
    }
)


async def _sampling_callback(
    context: object,
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult | types.ErrorData:
    """Runs an LLM completion on the server's behalf, via the AICredits gateway."""
    settings = get_settings()
    messages = []
    if params.system_prompt:
        messages.append({"role": "system", "content": params.system_prompt})
    for msg in params.messages:
        content = msg.content
        text = content.text if hasattr(content, "text") else str(content)
        messages.append({"role": msg.role, "content": text})

    try:
        client = get_raw_client()
        response = client.chat.completions.create(
            model=settings.aicredits_agent_model,
            messages=messages,
            max_tokens=params.max_tokens or 1024,
            temperature=params.temperature if params.temperature is not None else 0.5,
        )
        text_out = response.choices[0].message.content or ""
        return types.CreateMessageResult(
            role="assistant",
            content=types.TextContent(type="text", text=text_out),
            model=settings.aicredits_agent_model,
            stop_reason="endTurn",
        )
    except Exception as exc:
        logger.exception("Sampling callback failed")
        return types.ErrorData(code=types.INTERNAL_ERROR, message=str(exc))


async def _list_roots_callback(context: object) -> types.ListRootsResult | types.ErrorData:
    data_dir = get_settings().data_dir.resolve()
    return types.ListRootsResult(roots=[types.Root(uri=f"file:///{data_dir.as_posix()}", name="project-data")])


class MCPClient:
    """Async context manager wrapping one stdio-connected MCP session."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "MCPClient":
        params = StdioServerParameters(command=sys.executable, args=["-m", "backend.mcp.server"])
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(
            ClientSession(
                read_stream,
                write_stream,
                sampling_callback=_sampling_callback,
                list_roots_callback=_list_roots_callback,
            )
        )
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._stack.aclose()

    async def list_tools(self) -> list[str]:
        assert self.session is not None
        result = await self.session.list_tools()
        return [t.name for t in result.tools]

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Calls a tool and returns its text content (tools in this server all
        return a single JSON-encoded text block)."""
        assert self.session is not None
        result = await self.session.call_tool(name, arguments)
        if result.is_error:
            raise RuntimeError(f"MCP tool '{name}' failed: {result.content}")
        text_parts = [c.text for c in result.content if hasattr(c, "text")]
        return "\n".join(text_parts)

    async def call_tool_as_agent(self, name: str, arguments: dict) -> str:
        """Same as call_tool, but enforces the AGENT_SAFE_TOOLS allowlist first.
        This is the only entry point the LangGraph agent nodes use."""
        if name not in AGENT_SAFE_TOOLS:
            raise PermissionError(
                f"Tool '{name}' is not in the agent-safe allowlist ({sorted(AGENT_SAFE_TOOLS)}); "
                "destructive/write tools are only reachable via the FastAPI CRUD routers."
            )
        return await self.call_tool(name, arguments)
