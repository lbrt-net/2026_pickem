import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import URLSafeTimedSerializer

app = FastAPI()

CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["DISCORD_REDIRECT_URI"]
SECRET_KEY    = os.environ.get("SECRET_KEY", "change-me-in-prod")

signer = URLSafeTimedSerializer(SECRET_KEY)

DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL   = "https://discord.com/api/users/@me"


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html><body style="font-family:sans-serif;padding:2rem">
      <h1>Pickem</h1>
      <a href="/auth/login">
        <button style="padding:.75rem 1.5rem;font-size:1rem;background:#5865F2;color:white;border:none;border-radius:6px;cursor:pointer">
          Login with Discord
        </button>
      </a>
    </body></html>
    """


@app.get("/auth/login")
async def login():
    params = (
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return RedirectResponse(f"{DISCORD_AUTH_URL}?{params}")


@app.get("/auth/callback", response_class=HTMLResponse)
async def callback(request: Request, code: str = None, error: str = None):
    if error or not code:
        return HTMLResponse(f"<h2>OAuth error: {error or 'no code returned'}</h2>", status_code=400)

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data={
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Fetch Discord user
        user_resp = await client.get(
            DISCORD_API_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

    username = user.get("global_name") or user.get("username")
    discriminator = user.get("discriminator", "0")
    display = username if discriminator == "0" else f"{username}#{discriminator}"

    return f"""
    <html><body style="font-family:sans-serif;padding:2rem">
      <h1>✅ OAuth works!</h1>
      <p style="font-size:1.5rem">Hello, <strong>{display}</strong></p>
      <p style="color:gray">Discord ID: {user['id']}</p>
    </body></html>
    """
