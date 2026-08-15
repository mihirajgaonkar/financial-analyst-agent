"""Run-scoped capture of external JSON responses for local diagnostics."""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


_responses: ContextVar[list[dict[str, Any]] | None] = ContextVar("debug_external_responses", default=None)


@contextmanager
def capture_external_responses() -> Iterator[list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []
    token = _responses.set(captured)
    try:
        yield captured
    finally:
        _responses.reset(token)


def record_external_response(provider: str, url: str, params: dict[str, Any] | None, payload: Any) -> None:
    captured = _responses.get()
    if captured is None:
        return
    captured.append(
        {
            "provider": provider,
            "url": url,
            "params": _redact(params or {}),
            "payload": payload,
        }
    )


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if any(secret in key.lower() for secret in ("key", "token", "secret", "password")) else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(child) for child in value]
    return value
