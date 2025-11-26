import asyncio
from datetime import datetime
import os
from typing import Any, Literal, cast

from fastapi import HTTPException, Request
from nicegui import APIRouter
from pydantic import BaseModel
import svix

from app.data.messages import FileContent, LinkContent, TextContent
from app.webpage.agent_ui import get_agent_ui


WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class HandoffRequestBody(BaseModel):
    ada_conversation_id: str


class PostMessageAuthor(BaseModel):
    display_name: str | None
    role: str
    avatar: str | None
    id: str | None


class PostMessageData(BaseModel):
    message_id: str
    conversation_id: str
    end_user_id: str
    channel: dict[str, Any]
    created_at: datetime
    author: PostMessageAuthor
    content: TextContent | LinkContent | FileContent
    handoff_integration: str | None


class PostMessageRequest(BaseModel):
    type: Literal["v1.conversation.message"]
    data: PostMessageData
    timestamp: datetime


class EndHandoffData(BaseModel):
    conversation_id: str
    end_user_id: str
    handoff_integration: str


class EndHandoffRequest(BaseModel):
    type: Literal["v1.conversation.handoff.ended"]
    data: EndHandoffData
    timestamp: datetime


class GenericEventRequest(BaseModel):
    type: str
    data: dict[str, Any]
    timestamp: datetime


_global_event_queue: list[PostMessageRequest | EndHandoffRequest] = []
_global_batch_task: asyncio.Task | None = None
_global_batch_lock = asyncio.Lock()


@router.post("/start-handoff", status_code=204)
async def start_handoff(body: HandoffRequestBody):
    print("\033[94mReceived start handoff webhook\033[0m")
    agent_ui = get_agent_ui()
    agent_ui.send_notification(f"Starting ticket for conversation {body.ada_conversation_id}")
    await agent_ui.initialize_ticket(body.ada_conversation_id)


@router.post("/events", status_code=204)
async def handle_event(msg: PostMessageRequest | EndHandoffRequest | GenericEventRequest, request: Request):
    print(f"\033[94mReceived webhook event: {msg.model_dump_json()}\033[0m")

    headers = request.headers
    payload = await request.body()

    try:
        webhook = svix.Webhook(WEBHOOK_SECRET)
        webhook.verify(payload, cast(dict[str, str], headers))
    except svix.WebhookVerificationError as e:
        raise HTTPException(status_code=400, detail="Bad Request") from e

    if isinstance(msg, GenericEventRequest):
        print(f"\033[90mWebhook failed to parse or received unsupported type: {msg.type}\033[0m")
    else:
        await push_event_to_queue(msg)


async def push_event_to_queue(event: PostMessageRequest | EndHandoffRequest):
    """Batch events in a queue to be processed after a delay to account for unordered messages"""
    global _global_batch_lock

    async with _global_batch_lock:
        global _global_event_queue, _global_batch_task
        print("Pushing message to queue")
        _global_event_queue.append(event)

        if _global_batch_task is not None:
            print("Rescheduling batch task")
            _global_batch_task.cancel()
        else:
            print("Scheduling new batch task")

        _global_batch_task = asyncio.create_task(batch_process_events())


async def batch_process_events():
    global _global_batch_lock

    await asyncio.sleep(2)

    async with _global_batch_lock:
        global _global_event_queue, _global_batch_task
        events = _global_event_queue
        _global_event_queue = []
        _global_batch_task = None

    print("Processing batched events")

    events.sort(key=lambda e: e.timestamp)
    for event in events:
        if isinstance(event, PostMessageRequest):
            await process_message_event(event)
        elif isinstance(event, EndHandoffRequest):
            await process_end_handoff_event(event)


async def process_message_event(event: PostMessageRequest):
    if event.data.handoff_integration != "sandbox-handoff":
        print(f"\033[90mSkipping message for integration {event.data.handoff_integration}\033[0m")
        return

    if event.data.author.role == "human_agent":
        print(f"\033[90mSkipping message from human agent\033[0m")
        return

    agent_ui = get_agent_ui()
    conversation_id = await agent_ui.get_conversation_id()
    if conversation_id != event.data.conversation_id:
        print(f"\033[90mSkipping message for conversation {conversation_id}\033[0m")
        return

    author_role = event.data.author.role
    display_name = event.data.author.display_name
    avatar = event.data.author.avatar

    agent_ui.add_message(author_role, event.data.content, display_name, avatar)


async def process_end_handoff_event(event: EndHandoffRequest):
    if event.data.handoff_integration != "sandbox-handoff":
        print(f"\033[90mSkipping end handoff for integration {event.data.handoff_integration}\033[0m")
        return

    agent_ui = get_agent_ui()
    conversation_id = await agent_ui.get_conversation_id()
    if conversation_id != event.data.conversation_id:
        print(f"\033[90mSkipping end handoff for conversation {conversation_id}\033[0m")
        return

    agent_ui.send_notification("User has ended the handoff.")
    await agent_ui.close_ticket()
