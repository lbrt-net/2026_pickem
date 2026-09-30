"""Live draft: snake order, a pick clock, auto-pick on expiry, commissioner picks for anyone.

- One draft per league (fantasy_drafts row keyed by scenario). Picks are the league's
  fantasy_rosters rows, numbered by pick_no.
- Clock: settings["pick_seconds"] (10 minutes). There's no background job — every read or
  write first "catches up": each pick whose clock ran out is auto-picked (best available that
  fits), and the next clock starts when the previous one ended.
- Auto-pick / ranking: the pool's per-game fantasy points; in the replay league, the season
  *before* the replayed one (so it can't see the future).
- Rounds = roster spots (settings["roster_slots"]); every team fills every spot, no bench.
"""
from datetime import datetime, timedelta, timezone

from psycopg2.extras import Json

from .logic import draft_pool, open_slot, player_points
from .weeks import league_settings

REPLAY = "replay"


def _now():
    return datetime.now(timezone.utc)


def _prev_season(season: str) -> str:
    y = int(season[:4]) - 1
    return f"{y}-{str(y + 1)[2:]}"


def rank_points(cur, scenario: str) -> dict | None:
    """Replay: rank on the prior season. Other leagues: None (pool's own averages)."""
    if scenario != REPLAY:
        return None
    cur.execute("SELECT season FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    prior = _prev_season(cur.fetchone()["season"])
    cur.execute("""
        SELECT player_id, pts, fgm, fga, fg3m, ftm, fta, oreb, dreb, ast, stl, blk, tov, blkd
        FROM nba_player_games WHERE season = %s AND minutes > 0 AND substr(game_id, 3, 1) = '2'
    """, (prior,))
    sums, counts = {}, {}
    for r in cur.fetchall():
        sums[r["player_id"]] = sums.get(r["player_id"], 0) + player_points(r)
        counts[r["player_id"]] = counts.get(r["player_id"], 0) + 1
    rank = {pid: sums[pid] / counts[pid] for pid in sums}
    cur.execute("""
        SELECT home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
    """, (prior,))
    tot, n = {}, {}
    for g in cur.fetchall():
        for team, m in ((g["home_team"], g["home_score"] - g["away_score"]), (g["away_team"], g["away_score"] - g["home_score"])):
            tot[team] = tot.get(team, 0) + m
            n[team] = n.get(team, 0) + 1
    rank.update({t: tot[t] / n[t] for t in tot})
    return rank


def _row(cur, scenario: str) -> dict:
    cur.execute("INSERT INTO fantasy_drafts (scenario) VALUES (%s) ON CONFLICT DO NOTHING", (scenario,))
    cur.execute("SELECT * FROM fantasy_drafts WHERE scenario = %s FOR UPDATE", (scenario,))
    return dict(cur.fetchone())


def _picks(cur, scenario: str) -> list[dict]:
    cur.execute("""
        SELECT r.*, COALESCE(p.name, n.name) AS name, COALESCE(p.position, 'TEAM') AS position
        FROM fantasy_rosters r
        LEFT JOIN fantasy_players p ON p.id = r.player_id
        LEFT JOIN fantasy_nba_teams n ON n.id = r.nba_team_id
        WHERE r.scenario = %s ORDER BY r.pick_no NULLS LAST, r.id
    """, (scenario,))
    return cur.fetchall()


def _team_on_clock(order: list, pick_index: int):
    n = len(order)
    rnd, pos = divmod(pick_index, n)
    return order[pos] if rnd % 2 == 0 else order[n - 1 - pos]


def _filled(picks, team_id) -> dict:
    out = {}
    for p in picks:
        if p["team_id"] == team_id:
            out[p["slot"]] = out.get(p["slot"], 0) + 1
    return out


def _insert_pick(cur, scenario, team_id, entity, slot, pick_no, when, auto, by):
    cur.execute("""
        INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, nba_team_id, pick_no, picked_at, auto, picked_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (scenario, team_id, slot,
          entity["id"] if entity["kind"] == "player" else None,
          entity["id"] if entity["kind"] == "nba_team" else None, pick_no, when, auto, by))


def _advance(cur, scenario, d, total, when):
    cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = %s", (scenario,))
    if cur.fetchone()["n"] >= total:
        cur.execute("UPDATE fantasy_drafts SET status = 'complete', completed_at = %s, clock_started_at = NULL WHERE scenario = %s",
                    (when, scenario))
    else:
        cur.execute("UPDATE fantasy_drafts SET clock_started_at = %s WHERE scenario = %s", (when, scenario))


def _auto_pick(cur, scenario, d, settings, when, by="auto"):
    """Best available that fits the team on the clock."""
    picks = _picks(cur, scenario)
    order = d["team_order"]
    team_id = _team_on_clock(order, len(picks))
    taken = {p["player_id"] or p["nba_team_id"] for p in picks}
    filled = _filled(picks, team_id)
    for e in draft_pool(cur, rank_points(cur, scenario)):
        if e["id"] in taken:
            continue
        slot = open_slot(filled, e, settings["roster_slots"])
        if slot:
            _insert_pick(cur, scenario, team_id, e, slot, len(picks) + 1, when, True, by)
            return
    raise ValueError("no available player fits the team on the clock")


def catch_up(cur, scenario: str) -> None:
    """Auto-pick every pick whose clock has run out."""
    d = _row(cur, scenario)
    if d["status"] != "in_progress":
        return
    settings = league_settings(cur, scenario)
    total = len(d["team_order"]) * sum(settings["roster_slots"].values())
    step = timedelta(seconds=settings["pick_seconds"])
    while d["status"] == "in_progress" and d["clock_started_at"] and _now() >= d["clock_started_at"] + step:
        deadline = d["clock_started_at"] + step
        _auto_pick(cur, scenario, d, settings, deadline)
        _advance(cur, scenario, d, total, deadline)
        d = _row(cur, scenario)


def state(cur, scenario: str) -> dict:
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    settings = league_settings(cur, scenario)
    cur.execute("SELECT id, name, abbreviation, color, owner_user_id FROM fantasy_teams WHERE scenario = %s ORDER BY name",
                (scenario,))
    teams = {t["id"]: dict(t) for t in cur.fetchall()}
    order_ids = d["team_order"] or list(teams)
    order = [teams[t] for t in order_ids if t in teams]
    picks = _picks(cur, scenario)
    rounds = sum(settings["roster_slots"].values())
    n = len(order) or 1
    out_picks = [{
        "pick": i + 1, "round": i // n + 1, "team_id": p["team_id"],
        "team_name": teams.get(p["team_id"], {}).get("name"), "owner_user_id": teams.get(p["team_id"], {}).get("owner_user_id"),
        "slot": p["slot"], "kind": "player" if p["player_id"] else "nba_team", "id": p["player_id"] or p["nba_team_id"],
        "name": p["name"], "position": p["position"], "auto": p["auto"],
        "picked_at": p["picked_at"].isoformat() if p["picked_at"] else None,
    } for i, p in enumerate(picks)]
    status = d["status"]
    if status == "not_started" and picks:
        status = "complete"  # drafted instantly (simulated) before live drafting existed
    on_clock, deadline = None, None
    if status == "in_progress":
        on_clock = teams.get(_team_on_clock([t["id"] for t in order], len(picks)))
        deadline = (d["clock_started_at"] + timedelta(seconds=settings["pick_seconds"])).isoformat()
    return {
        "scenario": scenario, "status": status, "order": order, "rounds": rounds,
        "roster_slots": settings["roster_slots"], "pick_seconds": settings["pick_seconds"],
        "picks": out_picks, "total_picks": n * rounds, "on_clock": on_clock,
        "pick_number": len(picks) + 1 if status == "in_progress" else None,
        "deadline": deadline, "server_time": _now().isoformat(),
    }


def start(cur, scenario: str) -> None:
    """Start a fresh draft: clears the league's rosters, order = teams by name, clock starts now."""
    if scenario == "live":
        cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = 'live'")
        if cur.fetchone()["n"]:
            raise ValueError("the live league already has rosters")
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (scenario,))
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    order = [r["id"] for r in cur.fetchall()]
    if len(order) < 2:
        raise ValueError("need at least 2 teams to draft")
    _row(cur, scenario)
    cur.execute("""
        UPDATE fantasy_drafts SET status = 'in_progress', team_order = %s, clock_started_at = %s,
               started_at = %s, completed_at = NULL WHERE scenario = %s
    """, (Json(order), _now(), _now(), scenario))


def reset(cur, scenario: str) -> None:
    if scenario == "live":
        raise ValueError("the live draft can't be reset from here")
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_drafts WHERE scenario = %s", (scenario,))


def make_pick(cur, scenario: str, entity_id: str, user: dict) -> None:
    """The team on the clock picks `entity_id`. Allowed for that team's owner, or any admin
    (the commissioner picks for every bot)."""
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    if d["status"] != "in_progress":
        raise ValueError("the draft isn't running")
    settings = league_settings(cur, scenario)
    picks = _picks(cur, scenario)
    team_id = _team_on_clock(d["team_order"], len(picks))
    cur.execute("SELECT owner_user_id FROM fantasy_teams WHERE id = %s", (team_id,))
    owner = cur.fetchone()["owner_user_id"]
    if not user.get("is_admin") and owner != user.get("discord_id"):
        raise PermissionError("it's not your pick")
    if any((p["player_id"] or p["nba_team_id"]) == entity_id for p in picks):
        raise ValueError("already drafted")
    entity = next((e for e in draft_pool(cur) if e["id"] == entity_id), None)
    if not entity:
        raise ValueError("no such player or NBA team")
    slot = open_slot(_filled(picks, team_id), entity, settings["roster_slots"])
    if not slot:
        raise ValueError(f"{entity['name']} doesn't fit any open roster spot for this team")
    now = _now()
    _insert_pick(cur, scenario, team_id, entity, slot, len(picks) + 1, now, False, user.get("discord_id"))
    _advance(cur, scenario, d, len(d["team_order"]) * sum(settings["roster_slots"].values()), now)


def auto_pick_now(cur, scenario: str, user: dict, rest: bool = False) -> None:
    """Commissioner: auto-pick the current pick (or every remaining pick) right away."""
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    settings = league_settings(cur, scenario)
    total = len(d["team_order"]) * sum(settings["roster_slots"].values())
    while d["status"] == "in_progress":
        now = _now()
        _auto_pick(cur, scenario, d, settings, now, by=user.get("discord_id"))
        _advance(cur, scenario, d, total, now)
        d = _row(cur, scenario)
        if not rest:
            break
