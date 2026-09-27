import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str
    app_host: str
    app_port: int

    def __init__(self) -> None:
        self.spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
        self.spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
        self.spotify_redirect_uri = os.getenv(
            "SPOTIFY_REDIRECT_URI",
            "http://127.0.0.1:8000/auth/callback",
        ).strip()
        self.app_host = os.getenv("APP_HOST", "127.0.0.1").strip()
        self.app_port = int(os.getenv("APP_PORT", "8000"))

    def require_spotify_credentials(self) -> None:
        if not self.spotify_client_id or not self.spotify_client_secret:
            raise RuntimeError(
                "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your .env file"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
