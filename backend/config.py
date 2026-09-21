import os
from zoneinfo import ZoneInfo

CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["DISCORD_REDIRECT_URI"]
SECRET_KEY    = os.environ.get("SECRET_KEY", "change-me-in-prod")
DATABASE_URL  = os.environ["DATABASE_URL"]

ADMIN_DISCORD_IDS: set[str] = set(
    x.strip()
    for x in os.environ.get("ADMIN_DISCORD_IDS", "").split(",")
    if x.strip()
)

INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

CENTRAL = ZoneInfo("America/Chicago")

DISCORD_AUTH_URL  = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL   = "https://discord.com/api/users/@me"

COOKIE_NAME    = "session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 14
