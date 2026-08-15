from __future__ import annotations

import re
from time import sleep
from typing import Any, Callable


class LLMQuotaError(RuntimeError):
    """Raised when a provider quota/rate limit prevents model generation."""


def invoke_with_quota_handling(
    model: Any,
    messages: list[Any],
    *,
    sleep_fn: Callable[[float], None] = sleep,
):
    """Invoke a chat model with clear handling for quota and rate-limit failures."""
    try:
        return model.invoke(messages)
    except Exception as exc:
        message = str(exc)
        if not _is_quota_error(message):
            raise
        if _is_daily_quota_error(message):
            raise LLMQuotaError(_quota_message(message)) from exc

        retry_delay = _retry_delay_seconds(message)
        if retry_delay is not None and retry_delay <= 10:
            sleep_fn(retry_delay)
            try:
                return model.invoke(messages)
            except Exception as retry_exc:
                retry_message = str(retry_exc)
                if _is_quota_error(retry_message):
                    raise LLMQuotaError(_quota_message(retry_message)) from retry_exc
                raise

        raise LLMQuotaError(_quota_message(message)) from exc


def _is_quota_error(message: str) -> bool:
    lowered = message.lower()
    return "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered or "429" in lowered


def _is_daily_quota_error(message: str) -> bool:
    lowered = message.lower()
    return "perday" in lowered or "per day" in lowered or "free_tier_requests" in lowered


def _retry_delay_seconds(message: str) -> float | None:
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", message)
    if match:
        return float(match.group(1))
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", message, flags=re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _quota_message(message: str) -> str:
    model_match = re.search(r"model:\s*([\w.\-/]+)", message)
    model = model_match.group(1) if model_match else "the configured model"
    if _is_daily_quota_error(message):
        return (
            f"LLM quota exhausted for {model}. The provider reported a daily/free-tier quota limit. "
            "Wait for the quota window to reset, upgrade billing, or switch LLM_PROVIDER/associated model in .env."
        )
    retry_delay = _retry_delay_seconds(message)
    retry_hint = f" Retry after about {retry_delay:g} seconds." if retry_delay else ""
    return f"LLM rate limit reached for {model}.{retry_hint}"
