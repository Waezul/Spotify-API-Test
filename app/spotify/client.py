"""HTTP helpers for the Spotify Web API and related public endpoints."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_ACCOUNTS_BASE = "https://accounts.spotify.com"
SPOTIFY_OEMBED_BASE = "https://open.spotify.com/oembed"


class SpotifyApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        retry_after: str | None = None,
        reason: str | None = None,
    ):
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after
        self.reason = reason
        super().__init__(message)


async def spotify_request(
    method: str,
    path: str,
    *,
    access_token: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | list[Any] | None = None,
) -> Any:
    """Send an authenticated request to the Spotify Web API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    url = path if path.startswith("http") else f"{SPOTIFY_API_BASE}{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
        )

    if response.status_code == 204:
        return None

    if response.status_code >= 400:
        retry_after = response.headers.get("Retry-After")
        reason = None
        message = response.text
        try:
            payload = response.json()
            error = payload.get("error", payload)
            if isinstance(error, dict):
                message = str(error.get("message") or message)
                reason = error.get("reason")
            else:
                message = str(error)
        except Exception:
            pass

        raise SpotifyApiError(
            status_code=response.status_code,
            message=message,
            retry_after=retry_after,
            reason=reason,
        )

    if not response.content:
        return None
    return response.json()


def raise_http_from_spotify(exc: SpotifyApiError) -> None:
    detail: dict[str, Any] = {"spotify_status": exc.status_code, "message": exc.message}
    if exc.retry_after is not None:
        detail["retry_after_seconds"] = exc.retry_after
    if exc.reason is not None:
        detail["reason"] = exc.reason
    raise HTTPException(status_code=exc.status_code, detail=detail)
