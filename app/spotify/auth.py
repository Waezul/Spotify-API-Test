"""Spotify authorization code flow helpers."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.spotify.client import SPOTIFY_ACCOUNTS_BASE

DEFAULT_SCOPES = [
    "user-read-email",
    "user-read-private",
    "user-read-recently-played",
    "user-top-read",
    "playlist-modify-private",
    "playlist-modify-public",
    "playlist-read-private",
    "user-read-playback-state",
    "user-modify-playback-state",
    "streaming",
]


def build_authorize_url(settings: Settings, state: str) -> str:
    """Build the Spotify authorize URL. Redirect URI must match the Developer Dashboard exactly."""
    query = urlencode(
        {
            "client_id": settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": settings.spotify_redirect_uri,
            "scope": " ".join(DEFAULT_SCOPES),
            "state": state,
            "show_dialog": "true",
        }
    )
    return f"{SPOTIFY_ACCOUNTS_BASE}/authorize?{query}"


def new_state() -> str:
    return secrets.token_urlsafe(24)


async def exchange_code_for_tokens(settings: Settings, code: str) -> dict[str, Any]:
    """Exchange an authorization code for access and refresh tokens."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.spotify_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SPOTIFY_ACCOUNTS_BASE}/api/token",
            data=data,
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code >= 400:
        raise RuntimeError(f"token exchange failed ({response.status_code}): {response.text}")
    return response.json()


async def refresh_access_token(settings: Settings, refresh_token: str) -> dict[str, Any]:
    """Obtain a new access token using a refresh token."""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SPOTIFY_ACCOUNTS_BASE}/api/token",
            data=data,
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code >= 400:
        raise RuntimeError(f"token refresh failed ({response.status_code}): {response.text}")
    return response.json()
