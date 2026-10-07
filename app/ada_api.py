from collections.abc import AsyncGenerator
import json
import os
from typing import Any, Literal

import aiohttp

from app.data.messages import MessageContent


ADA_BASE_URL = os.environ["ADA_BASE_URL"]
ADA_API_KEY = os.environ["ADA_API_KEY"]


def _colorize(status_code: int, text: str) -> str:
    return (
        (
            "\033[92mSuccess Response: "
            if status_code < 300
            else "\033[91mError Response"
        )
        + text
        + "\033[0m"
    )


async def send_agent_message(
    conversation_id: str, display_name: str, avatar: str, message: MessageContent
):
    """Send a human agent message to Ada"""

    print("Sending agent message...")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{ADA_BASE_URL}/v2/conversations/{conversation_id}/messages",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            json={
                "author": {
                    "role": "human_agent",
                    "display_name": display_name,
                    "avatar": avatar
                },
                "content": message.model_dump(),
            }
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()


async def upload_agent_file(
    conversation_id: str, filename: str, content_type: str, content: bytes
) -> dict[str, Any]:
    """Uploads a file to Ada's system"""

    if len(content) > 50 * 1024 * 1024:
        raise ValueError("File size exceeds the 50MB limit")

    print("Uploading file...")
    data = aiohttp.FormData()
    data.add_field("file", content, filename=filename, content_type=content_type)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{ADA_BASE_URL}/v2/conversations/{conversation_id}/attachments",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            data=data,
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()
            return body


async def fetch_conversation_messages(conversation_id: str) -> AsyncGenerator[dict[str, Any]]:
    """Fetch all messages for an Ada conversation, yielding one by one"""

    print("Fetching conversation messages...")

    page_url = f"{ADA_BASE_URL}/v2/conversations/{conversation_id}/messages"
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(
                page_url,
                headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            ) as response:
                body = await response.json()
                print(_colorize(response.status, json.dumps(body)))

                response.raise_for_status()

                for message in body["data"]:
                    if message["type"] == "message_logs":
                        yield message

                page_url = body.get("meta", {}).get("next_page_url")
                if not page_url:
                    break


QueueUnit = Literal["position", "time", "unknown"]


async def report_queue_status(
    conversation_id: str, unit: QueueUnit, amount: int | None = None
):
    """Report the end user's place in the agent queue

    Send an update whenever the queue state changes; each one replaces the last.
    - `unit="position"`: `amount` is the place in the queue (0-9999)
    - `unit="time"`: `amount` is the estimated wait in seconds (-1 to 86400)
    - `unit="unknown"`: no `amount`; shows a generic waiting message

    An `amount` of 0 (or -1 for time) also shows the generic waiting message.
    """

    payload: dict[str, Any] = {"unit": unit}
    if unit != "unknown":
        if amount is None:
            raise ValueError(f"amount is required when unit is {unit!r}")
        payload["amount"] = amount

    print("Reporting queue status...")
    async with aiohttp.ClientSession() as session:
        async with session.patch(
            f"{ADA_BASE_URL}/v2/conversations/{conversation_id}/handoff-queue",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            json=payload,
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()


async def end_handoff(conversation_id: str):
    """End the handoff in Ada"""

    print("Ending handoff...")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{ADA_BASE_URL}/v2/conversations/{conversation_id}/end-handoff",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            json={}
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()
