"""Profile pictures: the site shows our own copy, so changing your picture on Discord never leaves an empty ring (2026-11-18)."""
import asyncio

import httpx
from fastapi.testclient import TestClient

from backend import auth
from backend.auth import upsert_user
from backend.main import app

PNG = b"\x89PNG\r\n\x1a\nfake"


def fake_discord(alive):
    """Discord's picture server: serves the links in `alive`, 404s everything else."""
    real = httpx.AsyncClient

    def client(*a, **kw):
        kw["transport"] = httpx.MockTransport(
            lambda req: httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
            if str(req.url).split("?")[0] in alive else httpx.Response(404))
        return real(*a, **kw)
    return client


def test_site_shows_our_copy_and_keeps_it_after_discord_link_dies(league, monkeypatch):
    old = "https://cdn.discordapp.com/avatars/u-av/aaa.png"
    user = upsert_user("u-av", "Pic Person", old, "picperson")
    assert user["avatar_url"] == "/avatars/u-av.png" and user["discord_avatar_url"] == old
    client = TestClient(app)
    monkeypatch.setattr(auth.httpx, "AsyncClient", fake_discord({old}))
    r = client.get("/avatars/u-av.png")
    assert r.status_code == 200 and r.content == PNG               # first request fills the copy
    monkeypatch.setattr(auth.httpx, "AsyncClient", fake_discord(set()))   # they changed it on Discord: old link 404s
    assert client.get("/avatars/u-av.png").content == PNG          # our copy still shows


def test_new_discord_login_refreshes_the_copy(league, monkeypatch):
    new = "https://cdn.discordapp.com/avatars/u-av2/bbb.png"
    upsert_user("u-av2", "Pic Two", "https://cdn.discordapp.com/avatars/u-av2/old.png", "pictwo")
    monkeypatch.setattr(auth.httpx, "AsyncClient", fake_discord({new}))
    upsert_user("u-av2", "Pic Two", new, "pictwo")
    assert asyncio.run(auth.save_avatar_copy("u-av2", new))
    assert TestClient(app).get("/avatars/u-av2.png").content == PNG


def test_dead_link_and_no_copy_is_404_so_the_page_shows_a_letter(league, monkeypatch):
    upsert_user("u-av3", "Pic Three", "https://cdn.discordapp.com/avatars/u-av3/gone.png", "picthree")
    monkeypatch.setattr(auth.httpx, "AsyncClient", fake_discord(set()))
    assert TestClient(app).get("/avatars/u-av3.png").status_code == 404
