"""Helpers for extracting model text without carrying provider metadata forward."""

from typing import Any


def extract_text_content(content: Any) -> str:
    """Return only text parts from a provider content payload.

    Gemini can return content parts with metadata such as signatures in an
    `extras` field. That metadata is not model prose and must not become part
    of the next prompt or the user-facing report.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        return "\n".join(part for part in text_parts if part)
    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return content["text"]
    return ""


def strip_provider_metadata(message: Any) -> Any:
    """Keep an AI message's tool calls while replacing rich content with text only."""
    if not hasattr(message, "model_copy") or not hasattr(message, "content"):
        return message
    return message.model_copy(update={"content": extract_text_content(message.content)})
