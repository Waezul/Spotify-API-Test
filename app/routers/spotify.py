"""Spotify OAuth and Web API routes for local integration testing."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.spotify import auth, token_store
from app.spotify.client import (
    SPOTIFY_OEMBED_BASE,
    SpotifyApiError,
    raise_http_from_spotify,
    spotify_request,
)

router = APIRouter(tags=["spotify"])


def _require_access_token() -> str:
    token = token_store.get_access_token()
    if not token:
        raise_http_from_spotify(
            SpotifyApiError(status_code=401, message="not logged in; open /auth/login first")
        )
    return token


class CreatePlaylistBody(BaseModel):
    name: str = Field(default="API Test Playlist")
    description: str = Field(default="Created by the Spotify FastAPI sample routes")
    public: bool = False


class AddPlaylistItemsBody(BaseModel):
    uris: list[str] = Field(min_length=1, max_length=100)


@router.get("/auth/login")
async def auth_login(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    """Start the Spotify authorization code flow."""
    settings.require_spotify_credentials()
    state = auth.new_state()
    token_store.set_oauth_state(state)
    return RedirectResponse(auth.build_authorize_url(settings, state))


@router.get("/auth/callback")
async def auth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Handle the Spotify OAuth redirect and store tokens in memory."""
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    if not code or not state:
        return JSONResponse(status_code=400, content={"error": "missing code or state"})

    expected = token_store.pop_oauth_state()
    if expected is None or state != expected:
        return JSONResponse(status_code=400, content={"error": "invalid oauth state"})

    try:
        tokens = await auth.exchange_code_for_tokens(settings, code)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    saved = token_store.save_tokens(tokens)
    return JSONResponse(
        {
            "message": "login successful; call the /spotify/* routes next",
            "token_type": saved.get("token_type"),
            "expires_in": saved.get("expires_in"),
            "scope": saved.get("scope"),
            "has_refresh_token": bool(saved.get("refresh_token")),
        }
    )


@router.post("/auth/refresh")
async def auth_refresh(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Refresh the stored access token."""
    settings.require_spotify_credentials()
    current = token_store.get_tokens()
    if not current or not current.get("refresh_token"):
        raise_http_from_spotify(
            SpotifyApiError(status_code=401, message="no refresh token stored; login first")
        )
    try:
        refreshed = await auth.refresh_access_token(settings, current["refresh_token"])
    except Exception as exc:
        raise_http_from_spotify(SpotifyApiError(status_code=400, message=str(exc)))
    saved = token_store.save_tokens(refreshed)
    return {
        "message": "token refreshed",
        "expires_in": saved.get("expires_in"),
        "scope": saved.get("scope"),
    }


@router.get("/auth/status")
async def auth_status() -> dict[str, Any]:
    """Return whether tokens are currently stored in memory."""
    tokens = token_store.get_tokens()
    return {
        "logged_in": bool(tokens),
        "has_refresh_token": bool(tokens and tokens.get("refresh_token")),
        "scope": tokens.get("scope") if tokens else None,
    }


@router.get("/spotify/me")
async def get_me(access_token: str = Depends(_require_access_token)) -> Any:
    """GET /v1/me — current user profile."""
    try:
        return await spotify_request("GET", "/me", access_token=access_token)
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/recently-played")
async def get_recently_played(
    limit: int = Query(default=20, ge=1, le=50),
    access_token: str = Depends(_require_access_token),
) -> Any:
    """GET /v1/me/player/recently-played — recent listening history (max about 50 tracks)."""
    try:
        return await spotify_request(
            "GET",
            "/me/player/recently-played",
            access_token=access_token,
            params={"limit": limit},
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/top/tracks")
async def get_top_tracks(
    time_range: str = Query(default="medium_term", pattern="^(short_term|medium_term|long_term)$"),
    limit: int = Query(default=20, ge=1, le=50),
    access_token: str = Depends(_require_access_token),
) -> Any:
    """GET /v1/me/top/tracks — user top tracks."""
    try:
        return await spotify_request(
            "GET",
            "/me/top/tracks",
            access_token=access_token,
            params={"time_range": time_range, "limit": limit},
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/top/artists")
async def get_top_artists(
    time_range: str = Query(default="medium_term", pattern="^(short_term|medium_term|long_term)$"),
    limit: int = Query(default=20, ge=1, le=50),
    access_token: str = Depends(_require_access_token),
) -> Any:
    """GET /v1/me/top/artists — user top artists."""
    try:
        return await spotify_request(
            "GET",
            "/me/top/artists",
            access_token=access_token,
            params={"time_range": time_range, "limit": limit},
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/search")
async def search(
    q: str = Query(min_length=1),
    type: str = Query(default="track"),
    limit: int = Query(default=5, ge=1, le=10),
    access_token: str = Depends(_require_access_token),
) -> Any:
    """GET /v1/search — catalog search (development mode often caps limit at 10)."""
    try:
        return await spotify_request(
            "GET",
            "/search",
            access_token=access_token,
            params={"q": q, "type": type, "limit": limit},
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.post("/spotify/playlists")
async def create_playlist(
    body: CreatePlaylistBody,
    access_token: str = Depends(_require_access_token),
) -> Any:
    """POST /v1/me/playlists — create a playlist for the current user."""
    try:
        return await spotify_request(
            "POST",
            "/me/playlists",
            access_token=access_token,
            json_body={
                "name": body.name,
                "description": body.description,
                "public": body.public,
            },
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.post("/spotify/playlists/{playlist_id}/items")
async def add_playlist_items(
    playlist_id: str,
    body: AddPlaylistItemsBody,
    access_token: str = Depends(_require_access_token),
) -> Any:
    """POST /v1/playlists/{id}/items — add track URIs (falls back to /tracks if needed)."""
    try:
        return await spotify_request(
            "POST",
            f"/playlists/{playlist_id}/items",
            access_token=access_token,
            json_body={"uris": body.uris},
        )
    except SpotifyApiError as exc:
        if exc.status_code == 404:
            try:
                return await spotify_request(
                    "POST",
                    f"/playlists/{playlist_id}/tracks",
                    access_token=access_token,
                    json_body={"uris": body.uris},
                )
            except SpotifyApiError as nested:
                raise_http_from_spotify(nested)
        raise_http_from_spotify(exc)


@router.get("/spotify/playlists/{playlist_id}")
async def get_playlist(
    playlist_id: str,
    access_token: str = Depends(_require_access_token),
) -> Any:
    """GET /v1/playlists/{id} — playlist details."""
    try:
        return await spotify_request(
            "GET",
            f"/playlists/{playlist_id}",
            access_token=access_token,
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/player/devices")
async def get_devices(access_token: str = Depends(_require_access_token)) -> Any:
    """GET /v1/me/player/devices — available playback devices."""
    try:
        return await spotify_request(
            "GET",
            "/me/player/devices",
            access_token=access_token,
        )
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/player")
async def get_playback_state(access_token: str = Depends(_require_access_token)) -> Any:
    """GET /v1/me/player — current playback state."""
    try:
        result = await spotify_request("GET", "/me/player", access_token=access_token)
        return result if result is not None else {"message": "no active playback"}
    except SpotifyApiError as exc:
        raise_http_from_spotify(exc)


@router.get("/spotify/embed")
async def get_embed_oembed(
    spotify_url: str = Query(
        ...,
        description="open.spotify.com URL for a track, album, or playlist",
        examples=["https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"],
    ),
) -> Any:
    """Fetch oEmbed metadata for Spotify Embeds. No user OAuth token required."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SPOTIFY_OEMBED_BASE, params={"url": spotify_url})
    if response.status_code >= 400:
        raise_http_from_spotify(
            SpotifyApiError(
                status_code=response.status_code,
                message=response.text,
                retry_after=response.headers.get("Retry-After"),
            )
        )
    return response.json()


@router.get("/spotify/token-for-playback")
async def token_for_playback(access_token: str = Depends(_require_access_token)) -> dict[str, Any]:
    """
    Return the current access token for local Web Playback SDK experiments.
    Do not expose an equivalent endpoint in production without proper session auth.
    """
    tokens = token_store.get_tokens() or {}
    return {
        "access_token": access_token,
        "expires_in": tokens.get("expires_in"),
        "token_type": tokens.get("token_type", "Bearer"),
    }
