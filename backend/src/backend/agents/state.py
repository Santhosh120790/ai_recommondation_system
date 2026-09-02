from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    user_input: str
    user_profile: NotRequired[str]
    candidates: NotRequired[str]
    trend_analysis: NotRequired[str]
    style_analysis: NotRequired[str]
    nutrition_analysis: NotRequired[str]
    final_recommendation: NotRequired[str]
    errors: NotRequired[list[str]]
