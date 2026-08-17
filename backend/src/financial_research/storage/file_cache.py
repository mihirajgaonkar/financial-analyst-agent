from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from financial_research.config.settings import Settings, get_settings


def get_cached_provider_response(
    provider: str,
    url: str,
    params: dict[str, Any] | None = None,
    *,
    ttl_seconds: int,
    settings: Settings | None = None,
) -> Any | None:
    settings = settings or get_settings()
    if not settings.provider_cache_enabled or ttl_seconds <= 0:
        return None
    path = _cache_path(settings.provider_cache_dir, provider, url, params)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(record["cached_at"])
    except (OSError, KeyError, json.JSONDecodeError, ValueError):
        return None
    age = datetime.now(timezone.utc) - cached_at
    if age.total_seconds() > ttl_seconds:
        return None
    return record.get("payload")


def store_provider_response(
    provider: str,
    url: str,
    params: dict[str, Any] | None,
    payload: Any,
    *,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not settings.provider_cache_enabled:
        return
    path = _cache_path(settings.provider_cache_dir, provider, url, params)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "provider": provider,
        "url": url,
        "params": _redact(params or {}),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    path.write_text(json.dumps(_jsonable(record), indent=2, ensure_ascii=True), encoding="utf-8")


def _cache_path(base_dir: str, provider: str, url: str, params: dict[str, Any] | None) -> Path:
    key = json.dumps(
        {
            "provider": provider,
            "url": url,
            "params": _cache_key_params(params or {}),
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    provider_dir = provider.lower().replace(" ", "_")
    return Path(base_dir) / provider_dir / f"{digest}.json"


def _cache_key_params(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in sorted(params.items())
        if not any(secret in key.lower() for secret in ("key", "token", "secret", "password"))
    }


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if any(secret in key.lower() for secret in ("key", "token", "secret", "password")) else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(child) for child in value]
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
