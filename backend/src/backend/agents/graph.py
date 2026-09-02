"""The multi-agent recommendation workflow as a real LangGraph StateGraph.

Hybrid workflow: User Profile Generator -> RAG Retriever (sequential), then
Food Trend Analyst / Food Style Expert / Nutrition Expert as true parallel
graph branches (all three edge from "retrieve"), joined by Recommendation
Expert (LangGraph waits for all three predecessors before running it).

Tool access (retrieval) goes through a live `MCPClient`, not direct RAG
calls — the MCP server is the actual data/tool layer for the agents.
"""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

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


async def _ask(llm: BaseChatModel, config: dict, user_message: str) -> str:
    response = await llm.ainvoke(
        [
            {"role": "system", "content": build_system_prompt(config)},
            {"role": "user", "content": user_message},
        ]
    )
    return str(response.content)


def build_graph(client: MCPClient, llm: BaseChatModel) -> CompiledStateGraph:
    async def node_generate_profile(state: AgentState) -> dict:
        profile = await _ask(
            llm,
            USER_PROFILE_GENERATOR,
            f"Build a user profile from this input (visit history / preferences):\n\n{state['user_input']}",
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
            result = await client.call_tool("fuse_search", {"query": query.strip(), "k": 10})
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
        return {"final_recommendation": final}

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

    return graph.compile()


async def run_recommendation(user_input: str) -> AgentState:
    from backend.core.llm import get_agent_model

    llm = get_agent_model()
    async with MCPClient() as client:
        graph = build_graph(client, llm)
        result = await graph.ainvoke({"user_input": user_input})
    return result


async def stream_recommendation(user_input: str):
    """Yields {"stage": <node name>, "data": <node output>} as each node
    completes, then a final {"stage": "done", "data": <full state>}."""
    from backend.core.llm import get_agent_model

    llm = get_agent_model()
    async with MCPClient() as client:
        graph = build_graph(client, llm)
        final_state: dict = {"user_input": user_input}
        async for update in graph.astream({"user_input": user_input}, stream_mode="updates"):
            for node_name, node_output in update.items():
                final_state.update(node_output)
                yield {"stage": node_name, "data": node_output}
        yield {"stage": "done", "data": final_state}
