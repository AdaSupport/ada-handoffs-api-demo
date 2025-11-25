from typing import Literal

from pydantic import BaseModel


class MessageContent(BaseModel):
    type: str


class TextContent(MessageContent):
    body: str
    type: Literal["text", "presence"] = "text"


class LinkContent(MessageContent):
    url: str
    link_text: str | None = None
    type: Literal["link"] = "link"


class FileContent(MessageContent):
    url: str
    filename: str
    mime_type: str
    type: Literal["file"] = "file"
