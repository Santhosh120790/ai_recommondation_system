"""Factories for LLM clients that talk to the AICredits gateway.

AICredits exposes an OpenAI-compatible API (base_url + api_key) that routes
to either GPT or Claude models depending on the model name passed in the
request. We reuse `ChatOpenAI` / the raw `openai` client pointed at that
base_url rather than juggling separate SDKs per provider.
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI
from openai import OpenAI

from backend.core.config import get_settings


@lru_cache
def get_raw_client() -> OpenAI:
    """Raw OpenAI-SDK client, used where LangChain isn't involved (e.g. the
    MCP client's sampling callback)."""
    settings = get_settings()
    return OpenAI(base_url=settings.aicredits_base_url, api_key=settings.aicredits_api_key)


def get_chat_model(model: str | None = None, temperature: float = 0.3) -> ChatOpenAI:
    """LangChain chat model for agent nodes / structuring / captioning."""
    settings = get_settings()
    return ChatOpenAI(
        base_url=settings.aicredits_base_url,
        api_key=settings.aicredits_api_key,
        model=model or settings.aicredits_text_model,
        temperature=temperature,
    )


def get_vision_model(temperature: float = 0.2) -> ChatOpenAI:
    settings = get_settings()
    return get_chat_model(model=settings.aicredits_vision_model, temperature=temperature)


def get_agent_model(temperature: float = 0.4) -> ChatOpenAI:
    settings = get_settings()
    return get_chat_model(model=settings.aicredits_agent_model, temperature=temperature)
