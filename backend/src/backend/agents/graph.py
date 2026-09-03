"""The multi-agent recommendation workflow as a real LangGraph StateGraph.

Hybrid workflow: User Profile Generator -> RAG Retriever (sequential), then
Food Trend Analyst / Food Style Expert / Nutrition Expert as true parallel
graph branches (all three edge from "retrieve"), joined by Recommendation
Expert (LangGraph waits for all three predecessors before running it).

Tool access (retrieval) goes through a live `MCPClient`, not direct RAG
calls — the MCP server is the actual data/tool layer for the agents.

Cross-cutting concerns (the "middleware" layer, since this graph is
hand-built rather than going through `create_agent`'s middleware slot):
- every LLM call is retried on transient failure (`_ask`)
- the graph only ever calls MCP tools through `client.call_tool_as_agent`,
  which enforces a read-only allowlist — see mcp/client.py. Destructive
  writes (add/delete restaurant) are reachable only from the FastAPI CRUD
  routers, driven by an explicit human action in the UI, never from agent
  reasoning.

Memory: `build_graph` accepts a `checkpointer`. Combined with a `thread_id`
in the invoke config, LangGraph persists `AgentState` per thread and the
`add_messages` reducer on `messages` appends each new turn rather than
replacing it, so follow-up messages ("make it cheaper") see prior context.
"""

import json
import logging
from typing import AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.configs import (
    FOOD_STYLE_EXPERT,
    FOOD_TREND_ANALYST,
    NUTRITION_EXPERT,
    RAG_RETRIEVER,
    RECOMMENDATION_EXPERT,
    USER_PROFILE_GENERATOR,
    build_system_prompt,
)
from backend.agents.state import AgentState
from backend.mcp.client import MCPClient

logger = logging.getLogger(__name__)


def _format_transcript(messages: list) -> str:
    lines = []
    for m in messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _ask(llm: BaseChatModel, config: dict, user_message: str) -> str:
    response = await llm.ainvoke(
        [
            {"role": "system", "content": build_system_prompt(config)},
            {"role": "user", "content": user_message},
        ]
    )
    return str(response.content)


def build_graph(
    client: MCPClient,
    llm: BaseChatModel,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    async def node_generate_profile(state: AgentState) -> dict:
        transcript = _format_transcript(state["messages"])
        profile = await _ask(
            llm,
            USER_PROFILE_GENERATOR,
            "Build (or update, if this is a follow-up) a user profile from this "
            f"conversation so far:\n\n{transcript}",
        )
        return {"user_profile": profile}

    async def node_retrieve_candidates(state: AgentState) -> dict:
        query = await _ask(
            llm,
            RAG_RETRIEVER,
            f"Given this user profile, write ONE short search query (max 15 words, no "
            f"preamble) to find matching restaurants and food images:\n\n{state['user_profile']}",
        )
        try:
            result = await client.call_tool_as_agent("fuse_search", {"query": query.strip(), "k": 10})
        except Exception:
            logger.exception("RAG retrieval failed")
            result = "[]"
        return {"candidates": result}

    async def node_analyze_trends(state: AgentState) -> dict:
        analysis = await _ask(
            llm,
            FOOD_TREND_ANALYST,
            f"User profile:\n{state['user_profile']}\n\nCandidates:\n{state['candidates']}\n\n"
            "Which of these align with current food trends, and why?",
        )
        return {"trend_analysis": analysis}

    async def node_analyze_styles(state: AgentState) -> dict:
        analysis = await _ask(
            llm,
            FOOD_STYLE_EXPERT,
            f"User profile:\n{state['user_profile']}\n\nCandidates:\n{state['candidates']}\n\n"
            "Evaluate how well each candidate's cuisine/food style matches the user's "
            "preferences.",
        )
        return {"style_analysis": analysis}

    async def node_evaluate_nutrition(state: AgentState) -> dict:
        analysis = await _ask(
            llm,
            NUTRITION_EXPERT,
            f"User profile:\n{state['user_profile']}\n\nCandidates:\n{state['candidates']}\n\n"
            "Flag any dietary-restriction or allergen concerns, and note which candidates "
            "best fit the user's health goals.",
        )
        return {"nutrition_analysis": analysis}

    async def node_generate_recommendations(state: AgentState) -> dict:
        payload = {
            "user_profile": state["user_profile"],
            "candidates": state["candidates"],
            "trend_analysis": state["trend_analysis"],
            "style_analysis": state["style_analysis"],
            "nutrition_analysis": state["nutrition_analysis"],
        }
        final = await _ask(
            llm,
            RECOMMENDATION_EXPERT,
            "Synthesize the following into a final recommendation: top restaurants and, if "
            "relevant, recipes, each with a short explanation grounded in the analyses "
            f"below.\n\n{json.dumps(payload, ensure_ascii=False)}",
        )
        # Recorded back into the transcript so a follow-up turn's profile/
        # retrieval nodes can see what was already recommended.
        return {"final_recommendation": final, "messages": [AIMessage(content=final)]}

    graph = StateGraph(AgentState)
    graph.add_node("profile", node_generate_profile)
    graph.add_node("retrieve", node_retrieve_candidates)
    graph.add_node("trends", node_analyze_trends)
    graph.add_node("styles", node_analyze_styles)
    graph.add_node("nutrition", node_evaluate_nutrition)
    graph.add_node("recommend", node_generate_recommendations)

    graph.add_edge(START, "profile")
    graph.add_edge("profile", "retrieve")
    graph.add_edge("retrieve", "trends")
    graph.add_edge("retrieve", "styles")
    graph.add_edge("retrieve", "nutrition")
    graph.add_edge("trends", "recommend")
    graph.add_edge("styles", "recommend")
    graph.add_edge("nutrition", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile(checkpointer=checkpointer)


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def stream_graph_events(
    graph: CompiledStateGraph, user_input: str, thread_id: str
) -> AsyncIterator[dict]:
    """Yields {"stage": <node name>, "data": <node output>} as each node
    completes, then a final {"stage": "done", "data": <full state>}."""
    final_state: dict = {}
    config = _thread_config(thread_id)
    async for update in graph.astream(
        {"messages": [HumanMessage(content=user_input)]}, config=config, stream_mode="updates"
    ):
        for node_name, node_output in update.items():
            final_state.update(node_output)
            # `messages` carries LangChain message objects (needed internally for the
            # checkpointer's add_messages reducer) - not JSON-serializable as-is and not
            # useful to a caller that already has trend/style/nutrition/recommend text.
            yield {"stage": node_name, "data": {k: v for k, v in node_output.items() if k != "messages"}}
    yield {"stage": "done", "data": {k: v for k, v in final_state.items() if k != "messages"}}


async def run_recommendation(user_input: str, client: MCPClient | None = None, thread_id: str = "cli") -> dict:
    """If `client` is omitted, opens (and tears down) a one-off MCP connection —
    fine for the CLI, but the API layer should always pass its long-lived client
    (see api/main.py's lifespan) so the embedding models aren't cold-loaded in a
    fresh subprocess on every request."""
    from langgraph.checkpoint.memory import InMemorySaver

    from backend.core.llm import get_agent_model

    llm = get_agent_model()
    if client is not None:
        graph = build_graph(client, llm, checkpointer=InMemorySaver())
        return await graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=_thread_config(thread_id))

    async with MCPClient() as owned_client:
        graph = build_graph(owned_client, llm, checkpointer=InMemorySaver())
        return await graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=_thread_config(thread_id))


async def stream_recommendation(user_input: str, client: MCPClient | None = None, thread_id: str = "cli"):
    """CLI convenience wrapper: builds its own graph + in-memory checkpointer
    per call. Each CLI invocation is a fresh process, so nothing persists
    across separate `backend-cli recommend` runs regardless of `thread_id` —
    real cross-turn memory only works against the API, which builds one graph
    + checkpointer at startup and reuses it for the process's lifetime (see
    api/main.py's lifespan)."""
    from langgraph.checkpoint.memory import InMemorySaver

    from backend.core.llm import get_agent_model

    llm = get_agent_model()

    if client is not None:
        graph = build_graph(client, llm, checkpointer=InMemorySaver())
        async for event in stream_graph_events(graph, user_input, thread_id):
            yield event
        return

    async with MCPClient() as owned_client:
        graph = build_graph(owned_client, llm, checkpointer=InMemorySaver())
        async for event in stream_graph_events(graph, user_input, thread_id):
            yield event
