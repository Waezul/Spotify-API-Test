# Spotify Web API Sample (FastAPI)

Minimal FastAPI backend for trying Spotify OAuth and common Web API endpoints with your own Developer Dashboard credentials.

## Setup

1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Add redirect URI exactly: `http://127.0.0.1:8000/auth/callback`  
   (`localhost` is not accepted; use `127.0.0.1`.)
3. Copy `.env.example` to `.env` and set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
4. Install dependencies and run:

```bash
python -m venv venv
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

5. Open `http://127.0.0.1:8000/auth/login`, then use `http://127.0.0.1:8000/docs`.

## Notes

- Development Mode apps are limited to a small allowlisted user set for Web API / Web Playback SDK auth.
- Tokens are stored in memory for local testing only; restarting the server clears login state.
- Never commit `.env` or share your client secret.
