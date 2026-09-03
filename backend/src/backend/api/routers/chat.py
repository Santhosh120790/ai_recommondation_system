import json
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agents.graph import stream_recommendation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/stream")
async def chat_stream(body: ChatRequest, request: Request) -> EventSourceResponse:
    mcp_client = request.app.state.mcp_client

    async def event_generator():
        try:
            async for event in stream_recommendation(body.message, client=mcp_client):
                yield {"event": event["stage"], "data": json.dumps(event["data"], ensure_ascii=False)}
        except Exception as exc:
            logger.exception("Chat stream failed")
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())
