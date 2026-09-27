"""In-memory token store for local single-user testing. Replace with a database for multi-user apps."""

from __future__ import annotations

from typing import Any

_tokens: dict[str, Any] = {}
_oauth_state: str | None = None


def set_oauth_state(state: str) -> None:
    global _oauth_state
    _oauth_state = state


def pop_oauth_state() -> str | None:
    global _oauth_state
    state = _oauth_state
    _oauth_state = None
    return state


def save_tokens(payload: dict[str, Any]) -> dict[str, Any]:
    # Spotify may omit refresh_token on refresh responses; keep the previous one.
    if "refresh_token" not in payload and "refresh_token" in _tokens:
        payload = {**payload, "refresh_token": _tokens["refresh_token"]}
    _tokens.clear()
    _tokens.update(payload)
    return dict(_tokens)


def get_tokens() -> dict[str, Any] | None:
    if not _tokens.get("access_token"):
        return None
    return dict(_tokens)


def get_access_token() -> str | None:
    return _tokens.get("access_token")


def clear_tokens() -> None:
    _tokens.clear()
