from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.spotify import router as spotify_router

app = FastAPI(
    title="Spotify Web API Sample",
    description=(
        "FastAPI sample for Spotify OAuth and common Web API endpoints "
        "(profile, listening history, search, playlists, playback helpers, embeds)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spotify_router)


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "app": "spotify-web-api-sample",
        "docs": "/docs",
        "login": "/auth/login",
        "setup": "copy .env.example to .env, add your Spotify app credentials, then open /auth/login",
    }
