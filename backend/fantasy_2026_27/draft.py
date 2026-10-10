"""Live draft: snake order, a pick clock, auto-pick on expiry, commissioner picks for anyone.

- One draft per league (fantasy_drafts row keyed by scenario). Picks are the league's
  fantasy_rosters rows, numbered by pick_no.
- Clock: settings["pick_seconds"] (10 minutes). There's no background job — every read or
  write first "catches up": each pick whose clock ran out is auto-picked (best available that
  fits), and the next clock starts when the previous one ended.
- Auto-pick / ranking: PROJ MAX (else PROJ AVG) when the league's season has a pool (projections.py); otherwise the
  pool's per-game fantasy points, and in the replay league the season *before* the replayed one
  (so it can't see the future).
- Rounds = roster spots (settings["roster_slots"]); every team fills every spot, no bench.
"""
import math
import time
from datetime import datetime, timedelta, timezone

from psycopg2.extras import Json

from .logic import draft_pool, fits_somewhere, open_slot, player_points, team_game_points
from . import scoring as scoring_mod
from . import projections
from . import bid as bid_mod
from .settings import logo_url
from .weeks import league_settings, round_seconds

# Which leagues can start a draft (2026-10-03): only the 2025-26 test league while the rebuilt
# draft room gets its first real run. Elsewhere the Start button / POST /admin/draft/start refuse
# and a scheduled start time doesn't fire. Add "live" when the 2026-27 league is ready to draft.
START_SCENARIOS = {"replay", "live"}


def start_enabled(scenario: str) -> bool:
    return scenario in START_SCENARIOS

REPLAY = "replay"


def _now():
    return datetime.now(timezone.utc)


# Every start opens with a warm-up: the draft is on (everyone's pulled into the room) but no clock runs and no
# pick, nomination or bid counts until it ends, so slow connections are in before anything happens.
WARMUP_SECONDS = 10
# When a clock runs out, the next one starts this long after (the page holds 0:00 meanwhile, then shows the new
# clock from its full time). Cosmetic: nothing can be done in the gap, and the clock that ran out isn't extended.
HOLD = timedelta(seconds=1)


def _check_warm(d) -> None:
    if d.get("warmup_until") and _now() < d["warmup_until"]:
        left = max(1, int((d["warmup_until"] - _now()).total_seconds() + 0.999))
        raise ValueError(f"the draft starts in {left} second{'s' if left != 1 else ''}")


def _prev_season(season: str) -> str:
    y = int(season[:4]) - 1
    return f"{y}-{str(y + 1)[2:]}"


_REC_CACHE: dict = {}    # (scenario, team, picks, spent) → that team's Rec bids
_RANK_CACHE: dict = {}   # prior season → ranking (finished seasons don't change)
_GAMES_CACHE: dict = {}  # prior season → games played per player / NBA team


def rank_season(cur, scenario: str) -> str | None:
    """The season auto-pick ranks on: replay = the season before the replayed one; else None."""
    if scenario != REPLAY:
        return None
    cur.execute("SELECT season FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    return _prev_season(cur.fetchone()["season"])


def rank_kind(cur, scenario: str) -> str:
    """'proj' when the league's season has a pool with projections (PROJ AVG), else 'box'."""
    return "proj" if projections.is_active(cur, projections.league_season(cur, scenario)) else "box"


def rank_points(cur, scenario: str) -> dict | None:
    """With a season pool: players rank by PROJ MAX, else PROJ AVG (blank = not in the dict, sorts last) and NBA teams by
    the prior season's average margin. Without one: replay ranks on the prior season; other leagues None
    (pool's own averages)."""
    season = projections.league_season(cur, scenario)
    if projections.is_active(cur, season):
        rank = dict(_prior_season_rank(cur, _prev_season(season)))
        # NBA teams: their TEAM projection when loaded (fantasy_team_pool), else last season's average
        cur.execute("SELECT team, proj_max FROM fantasy_team_pool WHERE season = %s AND proj_max IS NOT NULL", (season,))
        rank.update({r["team"]: r["proj_max"] for r in cur.fetchall()})
        # PROJ MAX (the weekly score under the season's schedule) when loaded, else PROJ AVG
        cur.execute("SELECT player_id, COALESCE(proj_max, proj_avg) AS v FROM fantasy_pool WHERE season = %s AND proj_avg IS NOT NULL", (season,))
        players = {r["player_id"]: r["v"] for r in cur.fetchall()}
        cur.execute("SELECT id FROM fantasy_nba_teams")
        teams = {r["id"] for r in cur.fetchall()}
        return {**{k: v for k, v in rank.items() if k in teams}, **players}
    prior = rank_season(cur, scenario)
    if prior is None:
        return None
    return _prior_season_rank(cur, prior)


def _prior_season_rank(cur, prior: str) -> dict:
    """Per-game fantasy points in a finished season, players and NBA teams, under the default rules."""
    if prior in _RANK_CACHE:
        return _RANK_CACHE[prior]
    cur.execute("""
        SELECT player_id, pts, fgm, fga, fg3m, ftm, fta, oreb, dreb, ast, stl, blk, tov, blkd, clutch_pts
        FROM nba_player_games WHERE season = %s AND minutes > 0 AND substr(game_id, 3, 1) = '2'
    """, (prior,))
    sums, counts = {}, {}
    for r in cur.fetchall():
        sums[r["player_id"]] = sums.get(r["player_id"], 0) + player_points(r)
        counts[r["player_id"]] = counts.get(r["player_id"], 0) + 1
    rank = {pid: sums[pid] / counts[pid] for pid in sums}
    cur.execute("""
        SELECT game_id, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
    """, (prior,))
    games = cur.fetchall()
    extras = scoring_mod.team_extras(cur, [g["game_id"] for g in games])
    tot, n = {}, {}
    for g in games:
        for team, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
            m = team_game_points(mine > theirs, mine, theirs, None, extras.get((g["game_id"], team)))
            tot[team] = tot.get(team, 0) + m
            n[team] = n.get(team, 0) + 1
    rank.update({t: tot[t] / n[t] for t in tot})
    _RANK_CACHE[prior] = rank
    _GAMES_CACHE[prior] = {**counts, **n}
    return rank


# Short-lived copies of the ranking and the draftable pool: they only change when projections load, and every
# draft-room check needs them (auto-pick, Rec bids). Rebuilding them per check reloaded the whole projection table.
_HOT: dict = {}
_HOT_SECONDS = 60


def _hot(key, build):
    now = time.monotonic()
    hit = _HOT.get(key)
    if hit and now - hit[0] < _HOT_SECONDS:
        return hit[1]
    value = build()
    _HOT[key] = (now, value)
    return value


def _rank_hot(cur, scenario: str):
    return _hot(("rank", scenario), lambda: rank_points(cur, scenario))


def _pool_hot(cur, scenario: str, rank):
    """The draftable pool: everyone who fits at least one spot under the league's roster rules."""
    slots = league_settings(cur, scenario)["roster_slots"]
    key = ("pool", scenario, tuple(sorted(slots.items())))
    return _hot(key, lambda: [e for e in draft_pool(cur, rank, projections.pool_for(cur, scenario)) if fits_somewhere(e, slots)])


def queue_ids(cur, scenario: str, team_id: str) -> list:
    cur.execute("SELECT entity_id FROM fantasy_draft_queue WHERE scenario = %s AND team_id = %s ORDER BY rank",
                (scenario, team_id))
    return [r["entity_id"] for r in cur.fetchall()]


def _auto_choice(cur, scenario, settings, picks, team_id, rank=None):
    """What auto-pick takes for `team_id` right now: the first player in the team's draft queue
    that's still available and fits, else the best available that fits."""
    taken = {p["player_id"] or p["nba_team_id"] for p in picks}
    filled = _filled(picks, team_id)
    pool = _pool_hot(cur, scenario, rank if rank is not None else _rank_hot(cur, scenario))
    by_id = {e["id"]: e for e in pool}
    queued = [by_id[i] for i in queue_ids(cur, scenario, team_id) if i in by_id]
    for e in queued + pool:
        if e["id"] not in taken and open_slot(filled, e, settings["roster_slots"]):
            return e
    return None


def set_queue(cur, scenario: str, user: dict, entity_ids: list, team_id: str | None = None) -> None:
    """Replace a team's draft queue with `entity_ids`, in order (draft only): the user's own team,
    or — commissioner only — any team named by `team_id` (e.g. bots / fake users)."""
    if team_id and user.get("is_admin"):
        cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    else:
        cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s AND owner_user_id = %s", (scenario, user.get("discord_id")))
    row = cur.fetchone()
    if not row:
        raise PermissionError("you don't have a team in this league" if not team_id else "no such team in this league")
    ids = list(dict.fromkeys(str(i) for i in entity_ids))[:200]
    valid = {e["id"] for e in draft_pool(cur, season_pool=projections.pool_for(cur, scenario))}
    cur.execute("DELETE FROM fantasy_draft_queue WHERE scenario = %s AND team_id = %s", (scenario, row["id"]))
    for n, i in enumerate(x for x in ids if x in valid):
        cur.execute("INSERT INTO fantasy_draft_queue (scenario, team_id, entity_id, rank) VALUES (%s, %s, %s, %s)",
                    (scenario, row["id"], i, n))


def _row(cur, scenario: str) -> dict:
    cur.execute("INSERT INTO fantasy_drafts (scenario) VALUES (%s) ON CONFLICT DO NOTHING", (scenario,))
    cur.execute("SELECT * FROM fantasy_drafts WHERE scenario = %s FOR UPDATE", (scenario,))
    return dict(cur.fetchone())


def _picks(cur, scenario: str) -> list[dict]:
    # Position: this season's (the pool's) when there is one — newer players have none in fantasy_players; 'TEAM' only
    # for NBA teams.
    cur.execute("""
        SELECT r.*, COALESCE(p.name, n.name) AS name,
               CASE WHEN r.nba_team_id IS NOT NULL THEN 'TEAM' ELSE COALESCE(fp.position, p.position) END AS position
        FROM fantasy_rosters r
        LEFT JOIN fantasy_players p ON p.id = r.player_id
        LEFT JOIN fantasy_nba_teams n ON n.id = r.nba_team_id
        LEFT JOIN fantasy_leagues lg ON lg.scenario = r.scenario
        LEFT JOIN fantasy_pool fp ON fp.player_id = r.player_id AND fp.season = lg.season
        WHERE r.scenario = %s AND r.pick_no IS NOT NULL ORDER BY r.pick_no, r.id
    """, (scenario,))  # draft picks only: players added later (Players page) have no pick number
    return cur.fetchall()


def _reversed_round(draft_type: str, rnd: int) -> bool:
    """Does 0-based round `rnd` run last-to-first?
    linear: never. snake: odd rounds. snake_3rr (third-round reversal): rounds 2 and 3
    (0-based 1 and 2) both reverse, then it alternates — 1→N, N→1, N→1, 1→N, N→1, ..."""
    if draft_type == "linear":
        return False
    if draft_type == "snake_3rr" and rnd >= 2:
        return rnd % 2 == 0
    return rnd % 2 == 1


def _team_on_clock(order: list, pick_index: int, draft_type: str = "snake"):
    n = len(order)
    rnd, pos = divmod(pick_index, n)
    return order[n - 1 - pos] if _reversed_round(draft_type, rnd) else order[pos]


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
    """The team on the clock's first queued player that fits, else the best available that fits."""
    picks = _picks(cur, scenario)
    team_id = _team_on_clock(d["team_order"], len(picks), settings["draft_type"])
    e = _auto_choice(cur, scenario, settings, picks, team_id)
    if not e:
        raise ValueError("no available player fits the team on the clock")
    _insert_pick(cur, scenario, team_id, e, open_slot(_filled(picks, team_id), e, settings["roster_slots"]), len(picks) + 1, when, True, by)


def _pick_step(settings: dict, d: dict, pick_index: int) -> timedelta:
    """The clock for a given pick, by its round (per-round clocks, else pick_seconds)."""
    n = max(len(d["team_order"]), 1)
    return timedelta(seconds=round_seconds(settings, pick_index // n))


def catch_up(cur, scenario: str) -> None:
    """Start a scheduled draft whose time has come, then auto-pick every pick whose clock ran out."""
    d = _row(cur, scenario)
    settings = league_settings(cur, scenario)
    when = settings["draft_start_at"]
    # Each scheduled time starts the draft once: after that (or after a Reset) it stays manual
    # until the commissioner schedules a new time.
    if (start_enabled(scenario) and d["status"] == "not_started" and when and when != d.get("schedule_used")
            and _now() >= datetime.fromisoformat(when)):
        cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = %s", (scenario,))
        if not cur.fetchone()["n"]:
            start(cur, scenario, at=datetime.fromisoformat(when))
            d = _row(cur, scenario)
    if d["status"] != "in_progress":
        return
    if settings["draft_type"] == "auction":
        _auction_catch_up(cur, scenario, settings)
        return
    total = len(d["team_order"]) * sum(settings["roster_slots"].values())
    while d["status"] == "in_progress" and d["clock_started_at"]:
        cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = %s", (scenario,))
        made = cur.fetchone()["n"]
        if _team_on_clock(d["team_order"], made, settings["draft_type"]) in (d.get("autopick_teams") or []):
            deadline = d["clock_started_at"]  # Autopick: picks the moment it's on the clock
        else:
            deadline = d["clock_started_at"] + _pick_step(settings, d, made)
        if _now() < deadline:
            break
        _auto_pick(cur, scenario, d, settings, deadline)
        _advance(cur, scenario, d, total, deadline + HOLD)
        d = _row(cur, scenario)


def state(cur, scenario: str, viewer: dict | None = None) -> dict:
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    settings = league_settings(cur, scenario)
    cur.execute("SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url, picture_mode FROM fantasy_teams WHERE scenario = %s ORDER BY name",
                (scenario,))
    teams = {}
    for t in cur.fetchall():
        t = dict(t)
        t["logo_url"] = logo_url(t)  # uploaded logo, else the owner's picture; TeamIcon falls back to the glyph
        del t["logo_updated"], t["picture_url"], t["picture_mode"]
        teams[t["id"]] = t
    order = [teams[t] for t in _resolved_order(d["team_order"], list(teams))]
    picks = _picks(cur, scenario)
    rounds = sum(settings["roster_slots"].values())
    n = len(order) or 1
    out_picks = [{
        "pick": i + 1, "round": i // n + 1, "team_id": p["team_id"],
        "team_name": teams.get(p["team_id"], {}).get("name"), "owner_user_id": teams.get(p["team_id"], {}).get("owner_user_id"),
        "slot": p["slot"], "kind": "player" if p["player_id"] else "nba_team", "id": p["player_id"] or p["nba_team_id"],
        "name": p["name"], "position": p["position"], "auto": p["auto"], "price": p.get("price"),
        # Who made it: auto (clock / Autopick / leftovers), the team's owner, or the commissioner for them.
        "by": "auto" if p["auto"] else ("owner" if p.get("picked_by") in (None, teams.get(p["team_id"], {}).get("owner_user_id")) else "commissioner"),
        "picked_at": p["picked_at"].isoformat() if p["picked_at"] else None,
    } for i, p in enumerate(picks)]
    status = d["status"]
    if status == "not_started" and picks:
        status = "complete"  # drafted instantly (simulated) before live drafting existed
    on_clock, deadline, auction = None, None, None
    if settings["draft_type"] == "auction":
        ids = [t["id"] for t in order]
        budgets = _budgets(settings, ids, picks)
        lot = d.get("lot")
        auction = {
            "budget": settings["auction_budget"], "min_bid": settings["auction_min_bid"],
            "min_raise_pct": settings.get("auction_min_raise_pct", 0),
            "nomination_seconds": settings["nomination_seconds"], "bid_seconds": settings["bid_seconds"],
            "budgets": [{"team_id": t, "team_name": teams[t]["name"], **budgets[t]} for t in ids],
            "phase": None if status != "in_progress" else ("bidding" if lot else "nominating"),
            "lot": {**lot, "min_next": min_next_bid(settings, lot["high_bid"]),  # smallest legal next bid
                    "high_team_name": teams.get(lot["high_team"], {}).get("name"),
                    "nominated_by_name": teams.get(lot["nominated_by"], {}).get("name")} if lot else None,
        }
        if status == "in_progress":
            if lot:
                deadline = d["lot_deadline"].isoformat()
            else:
                on_clock = teams.get(ids[d["nominate_index"]]) if d["nominate_index"] < len(ids) else None
                deadline = d["nominate_deadline"].isoformat() if d["nominate_deadline"] else None
    elif status == "in_progress":
        on_clock = teams.get(_team_on_clock([t["id"] for t in order], len(picks), settings["draft_type"]))
        deadline = (d["clock_started_at"] + _pick_step(settings, {"team_order": order}, len(picks))).isoformat()
    # What auto-pick would take for the viewer's own team right now (first queued player that fits,
    # else best available) — only ever sent to that team's owner; other teams' choices are never sent.
    rank = _rank_hot(cur, scenario)
    viewer = viewer or {}
    mine = next((t for t in teams.values() if viewer.get("discord_id") and t.get("owner_user_id") == viewer.get("discord_id")), None)
    my_auto_next = None
    if status == "in_progress" and mine:
        e = _auto_choice(cur, scenario, settings, picks, mine["id"], rank)
        my_auto_next = {"id": e["id"], "name": e["name"], "kind": e["kind"]} if e else None
    # Rec bid (bid.py): only the viewer's own team's, before and during an auction.
    my_rec_bids = None
    if auction and mine and status in ("not_started", "in_progress"):
        ids = [t["id"] for t in order]
        # Rec bids only change when a pick lands: cache per (league, team, picks so far) — every poll used to rerun the mock auction.
        ck = (scenario, mine["id"], len(picks), sum(p.get("price") or 0 for p in picks))
        my_rec_bids = _REC_CACHE.get(ck)
        if my_rec_bids is None:
            my_rec_bids = bid_mod.rec_bids([dict(e) for e in _pool_hot(cur, scenario, rank)], picks, settings,
                                           _budgets(settings, ids, picks), mine["id"])
            if len(_REC_CACHE) > 200:
                _REC_CACHE.clear()
            _REC_CACHE[ck] = my_rec_bids
        my_rec_bids = dict(my_rec_bids)
        lot_now = auction.get("lot")
        if lot_now and lot_now["entity_id"] in my_rec_bids:
            # the player on the block, for this viewer: his Rec bid, and whether the next legal bid is still within it
            rec = my_rec_bids[lot_now["entity_id"]]
            lot_now["my_rec"] = rec
            lot_now["my_call"] = ("winning" if lot_now["high_team"] == mine["id"] else
                                  "bid" if lot_now["min_next"] <= rec else "pass")
    taken_ids = {p["player_id"] or p["nba_team_id"] for p in picks}
    rank_values ={k: round(v, 1) for k, v in (rank or {}).items() if k not in taken_ids} if rank else None
    kind = rank_kind(cur, scenario)
    gp_season = _prev_season(projections.league_season(cur, scenario)) if kind == "proj" else rank_season(cur, scenario)
    games = _GAMES_CACHE.get(gp_season or "", {})
    rank_games = {k: g for k, g in games.items() if k not in taken_ids or (auction and auction["lot"] and auction["lot"]["entity_id"] == k)} if rank else None
    if rank and auction and auction["lot"]:  # the player on the block keeps his numbers
        v = rank.get(auction["lot"]["entity_id"])
        rank_values[auction["lot"]["entity_id"]] = None if v is None else round(v, 1)
    # Which direction each round runs, for the board.
    round_reversed = [_reversed_round(settings["draft_type"], r) for r in range(rounds)]
    return {
        "scenario": scenario, "status": status, "order": order, "rounds": rounds, "round_reversed": round_reversed,
        "roster_slots": settings["roster_slots"], "pick_seconds": settings["pick_seconds"],
        "pick_seconds_by_round": settings["pick_seconds_by_round"], "draft_type": settings["draft_type"],
        "draft_start_at": settings["draft_start_at"], "team_limit": settings["team_count"], "start_enabled": start_enabled(scenario),
        "picks": out_picks, "total_picks": n * rounds, "on_clock": on_clock,
        "pick_number": len(picks) + 1 if status == "in_progress" else None,
        "deadline": deadline, "server_time": _now().isoformat(), "auction": auction,
        "warmup_until": d["warmup_until"].isoformat() if status == "in_progress" and d.get("warmup_until") and _now() < d["warmup_until"] else None,
        "autopick_teams": [t for t in (d.get("autopick_teams") or []) if t in teams],
        "my_auto_next": my_auto_next, "my_rec_bids": my_rec_bids, "rank_season": gp_season, "rank_kind": kind, "rank_values": rank_values, "rank_games": rank_games,
    }


def _resolved_order(saved: list, team_ids: list) -> list:
    """The saved draft order, minus teams no longer in the league, plus any new teams at the end."""
    order = [t for t in (saved or []) if t in team_ids]
    return order + [t for t in team_ids if t not in order]


def _league_team_ids(cur, scenario: str) -> list:
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    return [r["id"] for r in cur.fetchall()]


def set_order(cur, scenario: str, team_ids: list) -> None:
    """Commissioner sets the round-1 order (snake reverses it each round). Only before the draft starts."""
    d = _row(cur, scenario)
    if d["status"] == "in_progress":
        raise ValueError("the draft is running — the order is locked")
    league = _league_team_ids(cur, scenario)
    if sorted(team_ids) != sorted(league):
        raise ValueError("the order must list every team in the league exactly once")
    cur.execute("UPDATE fantasy_drafts SET team_order = %s WHERE scenario = %s", (Json(team_ids), scenario))


def randomize_order(cur, scenario: str) -> None:
    import random
    order = _league_team_ids(cur, scenario)
    random.shuffle(order)
    set_order(cur, scenario, order)


def set_autopick(cur, scenario: str, team_id: str, on: bool) -> None:
    """Commissioner: put a team on Autopick (picks / nominates the moment it's on the clock) or take it off."""
    if team_id not in _league_team_ids(cur, scenario):
        raise ValueError("no such team in this league")
    d = _row(cur, scenario)
    teams = [t for t in (d.get("autopick_teams") or []) if t != team_id] + ([team_id] if on else [])
    cur.execute("UPDATE fantasy_drafts SET autopick_teams = %s WHERE scenario = %s", (Json(teams), scenario))
    catch_up(cur, scenario)


def start(cur, scenario: str, at: datetime | None = None) -> None:
    """Start a fresh draft: clears the league's rosters, uses the saved order (alphabetical if
    none was set), clock starts now (or at the scheduled time `at`). Locks joining."""
    _HOT.clear()
    _REC_CACHE.clear()
    if not start_enabled(scenario):
        raise ValueError("starting the draft is switched off for this league for now")
    settings = league_settings(cur, scenario)
    if scenario == "live":
        cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = 'live'")
        if cur.fetchone()["n"]:
            raise ValueError("the live league already has rosters")
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_lineups WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_lineup_weeks WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_transactions WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_waivers WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_claims WHERE scenario = %s", (scenario,))
    d = _row(cur, scenario)
    order = _resolved_order(d["team_order"], _league_team_ids(cur, scenario))
    if len(order) < 2:
        raise ValueError("need at least 2 teams to draft")
    began = at or _now()
    go = max(began, _now()) + timedelta(seconds=WARMUP_SECONDS)  # the first clock starts after the warm-up
    cur.execute("""
        UPDATE fantasy_drafts SET status = 'in_progress', team_order = %s, clock_started_at = %s,
               started_at = %s, completed_at = NULL, schedule_used = %s,
               lot = NULL, lot_deadline = NULL, nominate_index = 0, nominate_deadline = %s,
               autopick_teams = '[]', warmup_until = %s WHERE scenario = %s
    """, (Json(order), go, began, settings["draft_start_at"],
          go + timedelta(seconds=settings["nomination_seconds"]) if settings["draft_type"] == "auction" else None,
          go, scenario))


def reset(cur, scenario: str) -> None:
    """Back to before the draft: empty rosters, not started, every Autopick switch off. Keeps the
    saved draft order and each team's draft queue."""
    _HOT.clear()
    _REC_CACHE.clear()
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_lineups WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_lineup_weeks WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_transactions WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_waivers WHERE scenario = %s", (scenario,))
    cur.execute("DELETE FROM fantasy_claims WHERE scenario = %s", (scenario,))
    _row(cur, scenario)
    cur.execute("""
        UPDATE fantasy_drafts SET status = 'not_started', clock_started_at = NULL, started_at = NULL,
               completed_at = NULL, lot = NULL, lot_deadline = NULL, nominate_index = 0, nominate_deadline = NULL,
               autopick_teams = '[]', warmup_until = NULL
        WHERE scenario = %s
    """, (scenario,))


def make_pick(cur, scenario: str, entity_id: str, user: dict) -> None:
    """The team on the clock picks `entity_id`. Allowed for that team's owner, or any admin
    (the commissioner picks for every bot)."""
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    if d["status"] != "in_progress":
        raise ValueError("the draft isn't running")
    _check_warm(d)
    settings = league_settings(cur, scenario)
    if settings["draft_type"] == "auction":
        raise ValueError("this is an auction — nominate or bid instead")
    picks = _picks(cur, scenario)
    team_id = _team_on_clock(d["team_order"], len(picks), settings["draft_type"])
    cur.execute("SELECT owner_user_id FROM fantasy_teams WHERE id = %s", (team_id,))
    owner = cur.fetchone()["owner_user_id"]
    if not user.get("is_admin") and owner != user.get("discord_id"):
        raise PermissionError("it's not your pick")
    if any((p["player_id"] or p["nba_team_id"]) == entity_id for p in picks):
        raise ValueError("already drafted")
    entity = next((e for e in draft_pool(cur, season_pool=projections.pool_for(cur, scenario)) if e["id"] == entity_id), None)
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
    if settings["draft_type"] == "auction":
        _auction_now(cur, scenario, user, rest)
        return
    total = len(d["team_order"]) * sum(settings["roster_slots"].values())
    while d["status"] == "in_progress":
        now = _now()
        _auto_pick(cur, scenario, d, settings, now, by=user.get("discord_id"))
        _advance(cur, scenario, d, total, now)
        d = _row(cur, scenario)
        if not rest:
            break


# ---- Auction ----
# Teams nominate in draft order (skipping full rosters). The nominator names a player and an
# opening bid (≥ minimum) within the nomination clock — or the best available that fits is
# nominated at the minimum. Then anyone can top the high bid; each bid resets the bid clock;
# when it runs out the high bidder wins at that price. A team can bid everything it has left
# ("all in"); the safe max (remaining minus the minimum bid for each other open spot) is shown as
# guidance only. A team that can't cover the minimum bid sits out nominating and bidding; when no
# team with an open spot can afford a bid, the auction ends — teams keep what they won and any
# open spots stay empty.
# Like the snake draft, expired clocks are resolved lazily on every read/write.

def _budgets(settings: dict, order: list, picks: list) -> dict:
    spots = sum(settings["roster_slots"].values())
    out = {}
    for tid in order:
        mine = [p for p in picks if p["team_id"] == tid]
        spent = sum(p.get("price") or 0 for p in mine)
        open_spots = spots - len(mine)
        remaining = settings["auction_budget"] - spent
        safe = remaining - settings["auction_min_bid"] * (open_spots - 1) if open_spots > 0 else 0
        out[tid] = {"spent": spent, "remaining": remaining, "open_spots": open_spots,
                    "safe_max": max(safe, 0), "max_bid": remaining if open_spots > 0 else 0,
                    "can_bid": open_spots > 0 and remaining >= settings["auction_min_bid"]}
    return out


def min_next_bid(settings: dict, high: int) -> int:
    """The smallest legal raise over the high bid: + auction_min_raise_pct of it, rounded up, at least $1
    (at 4%: $25 → $26, $26 → $28, $50 → $52, $100 → $104, $150 → $156)."""
    return high + max(1, math.ceil(high * settings.get("auction_min_raise_pct", 0) / 100 - 1e-9))


def _check_bid(settings, order, picks, team_id, entity, amount):
    b = _budgets(settings, order, picks)[team_id]
    if b["open_spots"] <= 0:
        raise ValueError("that team's roster is full")
    if not open_slot(_filled(picks, team_id), entity, settings["roster_slots"]):
        raise ValueError(f"{entity['name']} doesn't fit any open roster spot for that team")
    if amount < settings["auction_min_bid"]:
        raise ValueError(f"the minimum bid is {settings['auction_min_bid']}")
    if amount > b["max_bid"]:
        raise ValueError(f"that team has only {b['max_bid']} left")


def _reseat_by_price(cur, scenario, settings, team_id):
    """Auction: seat a team's buys by price — the priciest eligible buys take G / F / C / TM, then Flex, then Bench
    (ties: earlier buy first). Keeps the board and the live roster showing the best buys as starters."""
    from .lineup import eligible
    cur.execute("""SELECT r.id, r.slot, r.player_id, r.nba_team_id, r.price, r.pick_no, p.position
                   FROM fantasy_rosters r LEFT JOIN fantasy_players p ON p.id = r.player_id
                   WHERE r.scenario = %s AND r.team_id = %s""", (scenario, team_id))
    rows = [{**r, "kind": "player" if r["player_id"] else "nba_team",
             "position": r["position"] if r["player_id"] else "TEAM"} for r in cur.fetchall()]
    rows.sort(key=lambda r: (-(r["price"] or 0), r["pick_no"] or 0))
    left = list(rows)
    seat = {}
    for t in ("G", "F", "C", "TEAM", "FLEX", "BENCH"):
        for _ in range(settings["roster_slots"].get(t, 0)):
            e = next((r for r in left if eligible(r, t)), None)
            if e:
                seat[e["id"]] = t
                left.remove(e)
    if left:  # can't happen with a legal roster; leave everything as it was
        return
    for r in rows:
        if seat[r["id"]] != r["slot"]:
            cur.execute("UPDATE fantasy_rosters SET slot = %s WHERE id = %s", (seat[r["id"]], r["id"]))


def _start_nominating(cur, scenario, settings, order, picks, from_index, when):
    """Next team (from `from_index`, wrapping) that has an open spot and can afford the minimum bid
    nominates. A team that can't afford it is done: its roster is whoever it won. Nobody can → the auction is over."""
    budgets = _budgets(settings, order, picks)
    n = len(order)
    nxt = next(((from_index + k) % n for k in range(n) if budgets[order[(from_index + k) % n]]["can_bid"]), None)
    if nxt is None:
        cur.execute("""UPDATE fantasy_drafts SET status = 'complete', completed_at = %s, lot = NULL, lot_deadline = NULL,
                       nominate_deadline = NULL WHERE scenario = %s""", (when, scenario))
        return
    cur.execute("""UPDATE fantasy_drafts SET nominate_index = %s, nominate_deadline = %s, lot = NULL, lot_deadline = NULL
                   WHERE scenario = %s""", (nxt, when + timedelta(seconds=settings["nomination_seconds"]), scenario))


def _open_lot(cur, scenario, settings, team_id, entity, amount, when, by):
    lot = {"entity_id": entity["id"], "kind": entity["kind"], "name": entity["name"], "position": entity.get("position"),
           "high_bid": amount, "high_team": team_id, "high_by": by, "nominated_by": team_id, "bids": 1}
    cur.execute("UPDATE fantasy_drafts SET lot = %s, lot_deadline = %s, nominate_deadline = NULL WHERE scenario = %s",
                (Json(lot), when + timedelta(seconds=settings["bid_seconds"]), scenario))


def _award(cur, scenario, d, settings, when):
    lot = d["lot"]
    picks = _picks(cur, scenario)
    entity = {"id": lot["entity_id"], "kind": lot["kind"], "position": lot["position"], "name": lot["name"]}
    slot = open_slot(_filled(picks, lot["high_team"]), entity, settings["roster_slots"])
    _insert_pick(cur, scenario, lot["high_team"], entity, slot, len(picks) + 1, when, lot.get("high_by") == "auto", lot.get("high_by"))
    cur.execute("UPDATE fantasy_rosters SET price = %s WHERE scenario = %s AND pick_no = %s", (lot["high_bid"], scenario, len(picks) + 1))
    _reseat_by_price(cur, scenario, settings, lot["high_team"])
    _start_nominating(cur, scenario, settings, d["team_order"], _picks(cur, scenario), d["nominate_index"] + 1, when + HOLD)


def _auto_nominate(cur, scenario, d, settings, when, by="auto"):
    """The nominating team's first queued player that fits (else best available), at the minimum bid."""
    picks = _picks(cur, scenario)
    team_id = d["team_order"][d["nominate_index"]]
    e = _auto_choice(cur, scenario, settings, picks, team_id)
    if not e:
        raise ValueError("no available player fits the nominating team")
    _open_lot(cur, scenario, settings, team_id, e, settings["auction_min_bid"], when, by)


def _auction_catch_up(cur, scenario, settings):
    while True:
        d = _row(cur, scenario)
        if d["status"] != "in_progress":
            return
        if d["lot"] and _now() >= d["lot_deadline"]:
            _award(cur, scenario, d, settings, d["lot_deadline"])
        elif d.get("warmup_until") and _now() < d["warmup_until"]:
            return  # nothing happens during the warm-up
        elif not d["lot"] and d["nominate_deadline"] and d["team_order"][d["nominate_index"]] in (d.get("autopick_teams") or []):
            _auto_nominate(cur, scenario, d, settings, _now())  # Autopick: nominates right away
        elif not d["lot"] and d["nominate_deadline"] and _now() >= d["nominate_deadline"]:
            _auto_nominate(cur, scenario, d, settings, d["nominate_deadline"] + HOLD)
        else:
            return


def _acting_team(cur, scenario, user, team_id):
    """The team a user acts as: their own team, or (commissioner) any team they name."""
    if team_id and user.get("is_admin"):
        return team_id
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s AND owner_user_id = %s", (scenario, user.get("discord_id")))
    row = cur.fetchone()
    if not row:
        raise PermissionError("you don't have a team in this league")
    return row["id"]


def nominate(cur, scenario: str, user: dict, entity_id: str, amount: int, team_id: str | None = None) -> None:
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    settings = league_settings(cur, scenario)
    if settings["draft_type"] != "auction" or d["status"] != "in_progress":
        raise ValueError("no auction is running")
    _check_warm(d)
    if d["lot"]:
        raise ValueError(f"{d['lot']['name']} is up for bid right now")
    nominator = d["team_order"][d["nominate_index"]]
    if _acting_team(cur, scenario, user, team_id or nominator) != nominator:
        raise PermissionError("it's not your turn to nominate")
    picks = _picks(cur, scenario)
    if any((p["player_id"] or p["nba_team_id"]) == entity_id for p in picks):
        raise ValueError("already drafted")
    entity = next((e for e in draft_pool(cur, season_pool=projections.pool_for(cur, scenario)) if e["id"] == entity_id), None)
    if not entity:
        raise ValueError("no such player or NBA team")
    _check_bid(settings, d["team_order"], picks, nominator, entity, int(amount))
    _open_lot(cur, scenario, settings, nominator, entity, int(amount), _now(), user.get("discord_id"))


def bid(cur, scenario: str, user: dict, amount: int, team_id: str | None = None) -> None:
    catch_up(cur, scenario)
    d = _row(cur, scenario)
    settings = league_settings(cur, scenario)
    lot = d["lot"]
    if not lot:
        raise ValueError("nothing is up for bid")
    team = _acting_team(cur, scenario, user, team_id)
    if team not in d["team_order"]:
        raise ValueError("that team isn't in this draft")
    amount = int(amount)
    need = min_next_bid(settings, lot["high_bid"])
    if amount < need:
        raise ValueError(f"the next bid has to be at least ${need} (raises are at least {settings.get('auction_min_raise_pct', 0):g}% of the high bid, $1 minimum)")
    entity = {"id": lot["entity_id"], "kind": lot["kind"], "position": lot["position"], "name": lot["name"]}
    _check_bid(settings, d["team_order"], _picks(cur, scenario), team, entity, amount)
    lot.update(high_bid=amount, high_team=team, high_by=user.get("discord_id"), bids=lot.get("bids", 1) + 1)
    cur.execute("UPDATE fantasy_drafts SET lot = %s, lot_deadline = %s WHERE scenario = %s",
                (Json(lot), _now() + timedelta(seconds=settings["bid_seconds"]), scenario))


def _auction_now(cur, scenario, user, rest):
    """Commissioner: close bidding now (or nominate now if nobody's up); `rest` = finish the whole
    auction instantly, every player going to its nominator at the minimum bid."""
    settings = league_settings(cur, scenario)
    while True:
        d = _row(cur, scenario)
        if d["status"] != "in_progress":
            return
        now = _now()
        if d["lot"]:
            _award(cur, scenario, d, settings, now)
            if not rest:
                return
        else:
            _auto_nominate(cur, scenario, d, settings, now, by=user.get("discord_id"))
            if not rest:
                return
