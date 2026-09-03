import json
import logging
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agents.graph import stream_graph_events

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


@router.post("/stream")
async def chat_stream(body: ChatRequest, request: Request) -> EventSourceResponse:
    graph = request.app.state.agent_graph
    thread_id = body.thread_id or str(uuid.uuid4())

    async def event_generator():
        try:
            yield {"event": "thread", "data": json.dumps({"thread_id": thread_id})}
            async for event in stream_graph_events(graph, body.message, thread_id):
                yield {"event": event["stage"], "data": json.dumps(event["data"], ensure_ascii=False)}
        except Exception as exc:
            logger.exception("Chat stream failed")
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())
