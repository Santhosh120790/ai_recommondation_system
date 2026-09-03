from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Full conversation transcript for this thread. The `add_messages` reducer
    # appends rather than overwrites, so - combined with a checkpointer keyed
    # by thread_id - each new turn sees everything said before it.
    messages: Annotated[list[BaseMessage], add_messages]
    user_profile: NotRequired[str]
    candidates: NotRequired[str]
    trend_analysis: NotRequired[str]
    style_analysis: NotRequired[str]
    nutrition_analysis: NotRequired[str]
    final_recommendation: NotRequired[str]
