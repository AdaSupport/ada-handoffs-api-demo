import random

import aiohttp
from nicegui import ui, APIRouter
from nicegui.events import UploadEventArguments

from app import ada_api
from app.data.messages import FileContent, TextContent
from app.webpage.agent_ui import QUEUE_UNITS, get_agent_ui


router = APIRouter(prefix="", tags=["webpage"])

QUEUE_ERROR_REASONS = {
    400: "the amount is out of range for the selected unit",
    422: (
        "the conversation must be on the chat channel, in an active handoff, "
        "and not yet assigned to a human agent"
    ),
}


def _generate_name() -> str:
    first_name = random.choice(["John", "Jane", "Alice", "Bob", "Eve"])
    last_name = random.choice(["Smith", "Johnson", "Williams", "Jones", "Brown"])
    return f"{first_name} {last_name}"


@router.page("/")
async def index():
    async def _upload_file(e: UploadEventArguments):
        conversation_id = await agent_ui.get_conversation_id()
        uploaded_file = await ada_api.upload_agent_file(
            conversation_id, e.file.name, e.file.content_type, await e.file.read()
        )
        message = FileContent(**uploaded_file)
        agent_ui.add_message("human_agent", message, display_name, avatar)
        await ada_api.send_agent_message(conversation_id, display_name, avatar, message)

    async def _send_agent_msg():
        text_value = agent_ui.text_input.value
        message = TextContent(body=text_value)
        agent_ui.add_message("human_agent", message, display_name, avatar)
        agent_ui.text_input.value = ""
        conversation_id = await agent_ui.get_conversation_id()
        await ada_api.send_agent_message(conversation_id, display_name, avatar, message)

    async def _report_queue_status():
        unit = agent_ui.queue_unit_toggle.value
        amount = None
        if unit != "unknown":
            settings = QUEUE_UNITS[unit]
            if agent_ui.queue_input.value is None:
                agent_ui.send_notification(f"Enter a {settings.label.lower()} first")
                return
            if agent_ui.queue_input.out_of_limits:
                agent_ui.send_notification(
                    f"{settings.label} must be between {settings.min} and {settings.max}"
                )
                return
            # ui.number yields a float, and the API requires a whole number.
            amount = int(agent_ui.queue_input.value)

        conversation_id = await agent_ui.get_conversation_id()
        try:
            await ada_api.report_queue_status(conversation_id, unit, amount)
        except aiohttp.ClientResponseError as e:
            reason = QUEUE_ERROR_REASONS.get(e.status, e.message)
            agent_ui.send_notification(f"Queue update failed ({e.status}): {reason}")
        except aiohttp.ClientError as e:
            agent_ui.send_notification(f"Queue update failed: {e}")

    async def _end_handoff():
        agent_ui.disable_chat_inputs()
        conversation_id = await agent_ui.get_conversation_id()
        await ada_api.end_handoff(conversation_id)
        await agent_ui.close_ticket()

    display_name = _generate_name()
    avatar = "https://upload.wikimedia.org/wikipedia/commons/0/09/.hecko_-_Floaty_-_profile_picture.svg"

    ui.query('.nicegui-content').classes("h-screen flex flex-col w-full")

    agent_ui = get_agent_ui()

    header = ui.row().classes("h-12 w-full items-stretch bg-gray-200 justify-center")
    with header:
        ui.label("Agent Interface").classes("text-lg content-center font-bold")

    agent_ui.notifier_element()
    agent_ui.message_list_element()

    with agent_ui.queue_controls():
        agent_ui.queue_button.on_click(_report_queue_status)

    with agent_ui.chat_footer():
        agent_ui.upload_button.on_upload(_upload_file)
        agent_ui.text_input.on("keydown.enter", _send_agent_msg)
        agent_ui.end_button.on_click(_end_handoff)

    agent_ui.disable_chat_inputs()
