from collections.abc import AsyncGenerator
import json
import mimetypes
import os
from typing import Any

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
    conversation_id: str, filepath: str
) -> dict[str, Any]:
    """Uploads a file to Ada's system"""

    print("Uploading file...")
    data = aiohttp.FormData()
    mime_type = mimetypes.guess_type(filepath)
    print(mime_type)
    with open(filepath, "rb") as f:
        data.add_field("file", f, filename=os.path.basename(filepath), content_type=mime_type[0])

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
