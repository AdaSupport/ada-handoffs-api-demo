import asyncio
from dataclasses import dataclass
from typing import Any

from nicegui import ui

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


@dataclass
class AgentUI:
    _ada_conversation_id: str = ""
    _conversation_lock: asyncio.Lock = asyncio.Lock()
    _upload_button: ui.button | None = None
    _text_input: ui.input | None = None
    _end_button: ui.button | None = None

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
    def upload_button(self) -> ui.button:
        if self._upload_button is None:
            self._upload_button = ui.button(
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

    def disable_chat_inputs(self):
        self.text_input.value = ""
        self.text_input._props["placeholder"] = "No active ticket"
        self.upload_button.disable()
        self.text_input.disable()
        self.end_button.disable()

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
