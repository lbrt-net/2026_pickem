"""League membership: join / leave, for leagues people join themselves (JOIN_SCENARIOS).

Rules (2026-10-02):
- Joining is open until the draft starts, up to the league's team limit (settings team_count, ≤ 16).
- Joining asks for a team name, abbreviation, and picture (Discord avatar, an uploaded image, or a
  glyph + color); blanks fall back to the Discord display name and an automatic abbreviation.
  Nothing happens until the person clicks Join.
- Leaving before the draft removes the team (and its spot in the draft order).
  Leaving once the draft has started turns the team into a bot team the commissioner controls.
- The site admin is always the commissioner.
- Fake users (chika2, wonton2, mits2) are real user rows that can't log in, seeded into the
  2025-26 test league.
"""
import random

from .settings import GLYPHS, assign_color, clean_abbreviation, clean_color, clean_name, default_abbreviation, logo_url
from .weeks import league_settings

JOIN_SCENARIOS = ("live", "replay")  # 2026-27 mirrors the 2025-26 test league: people join
TEST_LEAGUE = "replay"
FAKE_USERS = ["chika2", "wonton2", "mits2"]


def _draft_status(cur, scenario: str) -> str:
    cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    row = cur.fetchone()
    status = row["status"] if row else "not_started"
    if status == "not_started":
        cur.execute("SELECT 1 FROM fantasy_rosters WHERE scenario = %s LIMIT 1", (scenario,))
        if cur.fetchone():
            status = "complete"
    return status


def members(cur, scenario: str, viewer: dict | None) -> dict:
    settings = league_settings(cur, scenario)
    cur.execute("""
        SELECT t.id, t.name, t.abbreviation, t.color, t.glyph, t.owner_user_id, t.logo_updated, t.picture_url,
               u.username AS owner_name, COALESCE(u.is_fake, FALSE) AS owner_is_fake
        FROM fantasy_teams t LEFT JOIN users u ON u.discord_id = t.owner_user_id
        WHERE t.scenario = %s ORDER BY t.name
    """, (scenario,))
    teams = [{
        "id": t["id"], "name": t["name"], "abbreviation": t["abbreviation"], "color": t["color"], "glyph": t["glyph"],
        "logo_url": logo_url(t), "owner_user_id": t["owner_user_id"], "owner_name": t["owner_name"],
        "kind": "bot" if not t["owner_user_id"] else "fake" if t["owner_is_fake"] else "member",
    } for t in cur.fetchall()]
    status = _draft_status(cur, scenario)
    me = viewer.get("discord_id") if viewer else None
    mine = next((t for t in teams if me and t["owner_user_id"] == me), None)
    reason = None
    if scenario not in JOIN_SCENARIOS:
        reason = "this league isn't open for joining"
    elif status != "not_started":
        reason = "joining closed when the draft started"
    elif len(teams) >= settings["team_count"]:
        reason = "the league is full"
    elif mine:
        reason = "you're already in"
    elif not viewer:
        reason = "log in to join"
    return {"scenario": scenario, "league_name": settings["league_name"], "teams": teams, "team_limit": settings["team_count"], "draft_status": status,
            "my_team_id": mine["id"] if mine else None, "can_join": reason is None, "join_closed_reason": reason,
            "can_leave": bool(mine) and scenario in JOIN_SCENARIOS}


def join(cur, scenario: str, user: dict, name: str | None, abbreviation: str | None,
         picture: str | None = None, glyph: str | None = None, color: str | None = None) -> str:
    """picture: "avatar" (default) or "upload" keep the Discord avatar as the fallback picture (an
    upload follows via PUT /teams/{id}/logo); "glyph" drops it so the icon is the glyph on the color."""
    info = members(cur, scenario, user)
    if not info["can_join"]:
        raise ValueError(info["join_closed_reason"])
    cur.execute("SELECT username, avatar_url FROM users WHERE discord_id = %s", (user["discord_id"],))
    u = cur.fetchone()
    if not u:
        raise ValueError("log in again first")
    team_name = clean_name(name) if (name or "").strip() else u["username"][:50]
    abbr = clean_abbreviation(abbreviation) if (abbreviation or "").strip() else default_abbreviation(team_name)
    if glyph is not None and glyph not in GLYPHS:
        raise ValueError("unknown glyph")
    chosen_color = clean_color(color) if color else None
    team_id = f"{scenario}:{user['discord_id']}"
    cur.execute("""
        INSERT INTO fantasy_teams (id, scenario, owner_user_id, name, abbreviation, picture_url, glyph, color, color_custom)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (team_id, scenario, user["discord_id"], team_name, abbr,
          None if picture == "glyph" else u["avatar_url"], glyph or random.choice(GLYPHS),
          chosen_color, chosen_color is not None))
    assign_color(cur, scenario)
    return team_id


def leave(cur, scenario: str, user: dict) -> None:
    if scenario not in JOIN_SCENARIOS:
        raise ValueError("you can't leave this league")
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s AND owner_user_id = %s",
                (scenario, user["discord_id"]))
    team = cur.fetchone()
    if not team:
        raise ValueError("you're not in this league")
    _remove(cur, scenario, team)


def remove_team(cur, scenario: str, team_id: str) -> None:
    """Commissioner: take a team out of the league (same rules as leaving)."""
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    team = cur.fetchone()
    if not team:
        raise ValueError("no such team in this league")
    _remove(cur, scenario, team)


def _remove(cur, scenario: str, team: dict) -> None:
    if _draft_status(cur, scenario) == "not_started":
        cur.execute("DELETE FROM fantasy_teams WHERE id = %s", (team["id"],))  # draft order skips missing teams
    else:
        # Mid-draft or later: the team stays as a bot the commissioner controls.
        cur.execute("UPDATE fantasy_teams SET owner_user_id = NULL, name = %s WHERE id = %s",
                    ((team["name"] + " (bot)")[:50], team["id"]))


def seed_test_league(cur) -> None:
    """Fake users exist; the test league starts with them as its members (only when it has no teams)."""
    for name in FAKE_USERS:
        cur.execute("""
            INSERT INTO users (discord_id, username, handle, is_admin, is_hidden, is_fake)
            VALUES (%s, %s, %s, FALSE, TRUE, TRUE) ON CONFLICT (discord_id) DO NOTHING
        """, (f"fake-{name}", name, name))
    for scenario in (TEST_LEAGUE,):
        cur.execute("SELECT count(*) AS n FROM fantasy_teams WHERE scenario = %s", (scenario,))
        if cur.fetchone()["n"]:
            continue
        for name in FAKE_USERS:
            cur.execute("""
                INSERT INTO fantasy_teams (id, scenario, owner_user_id, name, abbreviation, glyph)
                VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING
            """, (f"{scenario}:fake-{name}", scenario, f"fake-{name}", name, default_abbreviation(name), random.choice(GLYPHS)))
        assign_color(cur, scenario)
