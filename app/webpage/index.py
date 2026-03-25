import random

from nicegui import ui, APIRouter
from nicegui.events import UploadEventArguments

from app import ada_api
from app.data.messages import FileContent, TextContent
from app.webpage.agent_ui import get_agent_ui


router = APIRouter(prefix="", tags=["webpage"])


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

    with agent_ui.chat_footer():
        agent_ui.upload_button.on_upload(_upload_file)
        agent_ui.text_input.on("keydown.enter", _send_agent_msg)
        agent_ui.end_button.on_click(_end_handoff)

    agent_ui.disable_chat_inputs()
