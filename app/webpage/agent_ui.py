import asyncio
from dataclasses import dataclass
from typing import Any, Self

from nicegui import ui
from nicegui.events import Handler, UploadEventArguments

from app import ada_api
from app.data.messages import FileContent, LinkContent, MessageContent, TextContent


@dataclass
class Message:
    role: str
    content: MessageContent
    display_name: str | None = None
    avatar: str | None = None

    @property
    def chat_name(self):
        if self.role == "ai_agent":
            default_name = "AI Agent"
        elif self.role == "human_agent":
            default_name = "Human Agent"
        else:
            default_name = "Anonymous User"

        return f"{self.display_name or default_name} ({self.role})"


@dataclass(frozen=True)
class QueueUnitSettings:
    name: str
    label: str | None = None
    placeholder: str | None = None
    min: int | None = None
    max: int | None = None


# Input limits mirror what the handoff queue API accepts for each unit. "unknown"
# takes no amount, so it has no input.
QUEUE_UNITS: dict[str, QueueUnitSettings] = {
    "position": QueueUnitSettings(
        name="Position", label="Queue position", placeholder="0 to 9999", min=0, max=9999
    ),
    "time": QueueUnitSettings(
        name="Wait time",
        label="Wait time (seconds)",
        placeholder="-1 to 86400",
        min=-1,
        max=86400,
    ),
    "unknown": QueueUnitSettings(name="Unknown"),
}
DEFAULT_QUEUE_UNIT = "position"


class UploadButton(ui.button):
    """nicegui does not have a clean way to trigger the file picker dialogue without the `ui.upload` element

    To avoid the ugly UI of the `ui.upload` element, we create a thin wrapper to couple the `ui.button` with
    a hidden `ui.upload` element that is triggered when the button is clicked.
    """
    _upload_element: ui.upload | None = None

    def on_upload(self, handler: Handler[UploadEventArguments]) -> Self:
        """Add a callback to be invoked when a file is uploaded. Overrides the button's on_click"""

        if self._upload_element is None:
            self._upload_element = ui.upload(auto_upload=True).classes("hidden")

        def _internal_handler(e: UploadEventArguments):
            result = handler(e)
            if self._upload_element:
                self._upload_element.reset()
            return result

        self._upload_element.on_upload(_internal_handler)
        self.on_click(lambda: self._upload_element.run_method("pickFiles"))

        return self

@dataclass
class AgentUI:
    _ada_conversation_id: str = ""
    _conversation_lock: asyncio.Lock = asyncio.Lock()
    _upload_button: UploadButton | None = None
    _text_input: ui.input | None = None
    _end_button: ui.button | None = None
    _queue_unit_toggle: ui.toggle | None = None
    _queue_input: ui.number | None = None
    _queue_button: ui.button | None = None

    def __post_init__(self) -> None:
        self._messages: list[Message] = []

    @ui.refreshable
    def notifier_element(self, text: str | None = None):
        if text:
            ui.notification(
                message=text, position="top", close_button=True, multi_line=True
            )

    @ui.refreshable
    def message_list_element(self):
        with ui.scroll_area().classes("flex-1") as chat_scroll:
            with ui.column().classes("w-full items-stretch"):
                for m in self._messages:
                    bubble_text = (
                        m.content.body if isinstance(m.content, TextContent) else []
                    )

                    chat_msg = ui.chat_message(
                        text=bubble_text,
                        sent=(m.role == "human_agent"),
                        name=m.chat_name,
                        avatar=m.avatar,
                    )
                    if isinstance(m.content, LinkContent):
                        with chat_msg:
                            url = m.content.url
                            ui.button(
                                m.content.link_text or "Click this link",
                                on_click=lambda: ui.navigate.to(url, new_tab=True),
                            )
                    elif isinstance(m.content, FileContent):
                        with chat_msg:
                            ui.link(m.content.filename, m.content.url)

                    if m.role == "ai_agent":
                        chat_msg.props("bg-color=green-3")
                    elif m.role == "end_user":
                        chat_msg.props("bg-color=blue-3")

        chat_scroll.scroll_to(percent=100)

    @property
    def upload_button(self) -> UploadButton:
        if self._upload_button is None:
            self._upload_button = UploadButton(
                "Upload File", color="primary", icon="upload_file"
            )
        return self._upload_button

    @property
    def text_input(self) -> ui.input:
        if self._text_input is None:
            self._text_input = (
                ui.input(placeholder="Type a message...")
                .props("outlined")
                .classes("flex-grow")
            )
        return self._text_input

    @property
    def end_button(self) -> ui.button:
        if self._end_button is None:
            self._end_button = ui.button(
                "Close Ticket", color="red", icon="exit_to_app"
            )
        return self._end_button

    @property
    def queue_unit_toggle(self) -> ui.toggle:
        if self._queue_unit_toggle is None:
            self._queue_unit_toggle = ui.toggle(
                {unit: settings.name for unit, settings in QUEUE_UNITS.items()},
                value=DEFAULT_QUEUE_UNIT,
                on_change=lambda e: self._apply_queue_unit(e.value),
            ).classes("items-center")
        return self._queue_unit_toggle

    @property
    def queue_input(self) -> ui.number:
        if self._queue_input is None:
            self._queue_input = (
                ui.number(precision=0)
                .props("outlined dense")
                .classes("w-56")
            )
            self._apply_queue_unit(DEFAULT_QUEUE_UNIT)
        return self._queue_input

    @property
    def queue_button(self) -> ui.button:
        if self._queue_button is None:
            self._queue_button = ui.button(
                "Update Queue", color="secondary", icon="hourglass_top"
            )
        return self._queue_button

    def queue_controls(self) -> ui.row:
        controls = ui.row().classes("h-12 w-full items-stretch")
        with controls:
            self.queue_unit_toggle
            self.queue_input
            self.queue_button
        return controls

    def _apply_queue_unit(self, unit: str):
        """Match the queue input's label and limits to the selected unit"""

        settings = QUEUE_UNITS[unit]
        queue_input = self.queue_input
        queue_input.value = None
        queue_input.set_visibility(settings.min is not None)
        if settings.min is None:
            return

        queue_input.set_label(settings.label)
        queue_input._props["placeholder"] = settings.placeholder
        queue_input.min = settings.min
        queue_input.max = settings.max
        queue_input.update()

    def chat_footer(self) -> ui.row:
        footer = ui.row().classes("h-12 w-full items-stretch")
        with footer:
            self.upload_button
            self.text_input
            self.end_button
        return footer

    def enable_chat_inputs(self):
        self.text_input._props["placeholder"] = "Type a message..."
        self.upload_button.enable()
        self.text_input.enable()
        self.end_button.enable()
        self.queue_unit_toggle.enable()
        self.queue_input.enable()
        self.queue_button.enable()

    def disable_chat_inputs(self):
        self.text_input.value = ""
        self.text_input._props["placeholder"] = "No active ticket"
        self.upload_button.disable()
        self.text_input.disable()
        self.end_button.disable()
        self.queue_unit_toggle.value = DEFAULT_QUEUE_UNIT
        self.queue_input.value = None
        self.queue_unit_toggle.disable()
        self.queue_input.disable()
        self.queue_button.disable()

    def add_message(
        self,
        role: str,
        content: MessageContent,
        display_name: str | None = None,
        avatar: str | None = None,
    ):
        self._messages.append(Message(role, content, display_name, avatar))
        self.message_list_element.refresh()

    def send_notification(self, text: str):
        self.notifier_element.refresh(text)

    async def initialize_ticket(self, ada_conversation_id: str):
        async with self._conversation_lock:
            self._ada_conversation_id = ada_conversation_id
            self._messages.clear()
            self.message_list_element.refresh()
            self.enable_chat_inputs()

        transcript_lines = []
        async for msg in ada_api.fetch_conversation_messages(ada_conversation_id):
            transcript_lines.append(format_transcript_msg(msg))

        transcript = "\n".join(transcript_lines)

        self.add_message("ai_agent", TextContent(body="TRANSCRIPT: \n" + transcript))

    async def close_ticket(self):
        async with self._conversation_lock:
            self._ada_conversation_id = ""
            self.disable_chat_inputs()

    async def get_conversation_id(self) -> str:
        async with self._conversation_lock:
            return self._ada_conversation_id


def format_transcript_msg(msg: dict[str, Any]) -> str:
    author_role = msg["author"]["role"].upper()

    content_type = msg["content"]["type"]
    if content_type == "text":
        body = msg["content"]["body"]
    elif content_type == "link":
        body = msg["content"]["url"]
    elif content_type == "file":
        body = msg["content"]["url"]
    else:
        body = f"<Unsupported content type: {content_type}>"

    return f"{author_role}: {body}"


_agent_ui: AgentUI | None = None


def get_agent_ui() -> AgentUI:
    global _agent_ui
    if _agent_ui is None:
        _agent_ui = AgentUI()
    return _agent_ui
