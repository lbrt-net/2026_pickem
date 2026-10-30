"""League activity (Home): the most impactful moves, not the latest ones (DECISIONS.md 2026-10-10).

- Only moves that happened: the Transaction Log already holds only real moves (add-then-drop before any lock leaves
  it); a real drop shows when it's made, an add only once that player has locked into that team's lineup
  (a row in the roster lock record, fantasy_lock_ledger, for the team, that week or later).
- One entry per team per period (lock to lock; "pre" = before Week 1; a 2-week playoff round is one period): its net
  change — a player added and dropped inside the same period never appears.
- Impact = the biggest value among the entry's players (not the sum), frozen as of the week the move happened (PROJ
  MAX blended with his actual weeks before it — later games never change it). Every entry halves at the same moment
  — each time a new week starts — so two moves' relative weight never changes: an old move can't jump a newer one or
  vice versa; only new moves slot in. The draft is one entry: its three biggest picks (as of week 0).
- The impact number is only for ranking; it is never sent to the page.
"""
from .engine import as_of, league, weeks_for_league
from . import projections
from datetime import datetime

from .transactions import log as tx_log

TOP = 15            # entries kept (the Home box shows as many of the most important as fit)
ROLE_RANK = 25      # replacement level for a player: the 25th best at his role (G / F / C)
TEAM_RANK = 13      # for an NBA team: the 13th best team


def _values(cur, scenario) -> "callable":
    """importance(entity, week): how much he's worth above a replacement player through the move's week (commissioner,
    2026-10-23). Value = the site's blend — 25% preseason PROJ MAX + 75% his weekly best over the 4 weeks ending with
    the move's week, once he has 4+ games there (projections.season_weight), else PROJ MAX. Replacement = the 25th best
    value at his role (G / F / C), or the 13th best NBA team, same window. Never below 0. While the move's week is on it
    moves with that week's games; once the week is over it's locked."""
    from .board import actual
    season = projections.league_season(cur, scenario)
    lg = league(cur, scenario)
    weeks = weeks_for_league(cur, lg)
    cur.execute("SELECT player_id AS id, proj_max, proj_weeks, position FROM fantasy_pool WHERE season = %s AND proj_max IS NOT NULL", (season,))
    proj, role = {}, {}
    for r in cur.fetchall():
        proj[r["id"]] = projections.shown_max(r["proj_weeks"], r["proj_max"])
        role[r["id"]] = r["position"]
    cur.execute("SELECT team AS id, proj_max FROM fantasy_team_pool WHERE season = %s AND proj_max IS NOT NULL", (season,))
    for r in cur.fetchall():
        proj[r["id"]], role[r["id"]] = r["proj_max"], "TEAM"
    weekly = {eid: {int(k): v for k, v in row.get("weeks", {}).items()}
              for eid, row in actual(cur, scenario, "season", with_weeks=True)["players"].items()}
    # games played per fantasy week (players: minutes > 0; NBA teams: every final game) — for the 4-games rule
    games: dict = {}
    wk_of = lambda d: next((w["week"] for w in weeks if w["start"] <= d <= w["end"]), None)
    cur.execute("""SELECT pg.player_id AS id, g.game_date FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                   WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0""", (lg["season"],))
    rows = cur.fetchall()
    cur.execute("SELECT home_team, away_team, game_date FROM nba_games WHERE season = %s AND game_type = 'regular' AND status = 'final'", (lg["season"],))
    rows += [{"id": t, "game_date": g["game_date"]} for g in cur.fetchall() for t in (g["home_team"], g["away_team"])]
    for r in rows:
        w = wk_of(r["game_date"])
        if w:
            games.setdefault(r["id"], {}).setdefault(w, 0)
            games[r["id"]][w] += 1

    def value(eid, week):
        p = proj.get(eid)
        # the 4 weeks ending with the move's week (2026-10-23): it keeps moving with that week's games and locks once
        # the week is over
        window = [k for k in range((week or 0) - projections.RECENT_WEEKS + 1, (week or 0) + 1)]
        n = sum(games.get(eid, {}).get(k, 0) for k in window)
        ws = [weekly.get(eid, {})[k] for k in window if k in weekly.get(eid, {})]
        w = projections.season_weight(n) if ws else 0.0
        if p is None:
            return sum(ws) / len(ws) if ws else 0.0
        return (1 - w) * p + w * (sum(ws) / len(ws)) if w else p

    repl_cache: dict = {}

    def replacement(week, r):
        if week not in repl_cache:
            by: dict = {}
            for eid in proj:
                by.setdefault(role.get(eid), []).append(value(eid, week))
            repl_cache[week] = {k: (sorted(v, reverse=True)[(TEAM_RANK if k == "TEAM" else ROLE_RANK) - 1]
                                    if len(v) >= (TEAM_RANK if k == "TEAM" else ROLE_RANK) else 0.0) for k, v in by.items()}
        return repl_cache[week].get(r, 0.0)

    def importance(eid, week):
        week = week or 0
        return max(0.0, value(eid, week) - replacement(week, role.get(eid)))
    return importance


# Kept, not recomputed per visit (2026-10-23): the list only changes when a transaction is made, an added player locks
# into a lineup (an add counts from then), or a new week starts (every entry halves). One quick fingerprint of those;
# the full calculation runs only when it changes (and once in the background at startup).
_KEPT: dict = {}   # scenario -> (fingerprint, result)


def _fingerprint(cur, scenario: str) -> tuple:
    cur.execute("SELECT count(*) AS n, coalesce(max(id), 0) AS m FROM fantasy_transactions WHERE scenario = %s", (scenario,))
    t = cur.fetchone()
    cur.execute("SELECT count(*) AS n FROM fantasy_lock_ledger WHERE scenario = %s", (scenario,))
    locks = cur.fetchone()["n"]
    cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    d = cur.fetchone()
    lg = league(cur, scenario)
    today = as_of(lg)
    cw = next((w["week"] for w in weeks_for_league(cur, lg) if w["start"] <= today <= w["end"]), None)
    # a finished game moves this week's values (until the week is over)
    cur.execute("SELECT count(*) AS n FROM nba_games WHERE season = %s AND game_type = 'regular' AND status = 'final'", (lg["season"],))
    finals = cur.fetchone()["n"]
    return (t["n"], t["m"], locks, (d or {}).get("status"), cw, finals)


_REBUILDING = set()


def _rebuild(scenario: str, fp) -> None:
    from backend.db import get_db
    conn = get_db()
    try:
        with conn.cursor() as cur:
            _KEPT[scenario] = (fp, activity(cur, scenario))
        conn.commit()
    except Exception:  # noqa: BLE001 — the old copy stays up; next request tries again
        conn.rollback()
    finally:
        conn.close()
        _REBUILDING.discard(scenario)


def kept_activity(cur, scenario: str) -> dict:
    """The kept list. When something changed (a move, a lock, a finished game), the last copy is answered at once and the
    new one is built in the background (~5 s; 2026-10-25: the box sat on "Loading…" during every rebuild)."""
    fp = _fingerprint(cur, scenario)
    hit = _KEPT.get(scenario)
    if hit and hit[0] == fp:
        return hit[1]
    if hit:
        if scenario not in _REBUILDING:
            _REBUILDING.add(scenario)
            import threading
            threading.Thread(target=_rebuild, args=(scenario, fp), daemon=True).start()
        return hit[1]
    out = activity(cur, scenario)
    _KEPT[scenario] = (fp, out)
    return out


def warm() -> None:
    """Startup: build the live league's list once in the background, so the first visitor doesn't wait."""
    from backend.db import get_db
    conn = get_db()
    try:
        with conn.cursor() as cur:
            kept_activity(cur, "live")
        conn.commit()
    except Exception:  # noqa: BLE001
        conn.rollback()
    finally:
        conn.close()


def activity(cur, scenario: str) -> dict:
    lg = league(cur, scenario)
    weeks = weeks_for_league(cur, lg)
    today = as_of(lg)
    items = tx_log(cur, scenario)["items"]
    cur.execute("SELECT team_id, week, entity_id FROM fantasy_lock_ledger WHERE scenario = %s", (scenario,))  # the roster lock record
    locked = {}  # (team, entity) -> earliest week he locked in for that team
    for r in cur.fetchall():
        k = (r["team_id"], r["entity_id"])
        locked[k] = min(locked.get(k, r["week"]), r["week"])
    value = _values(cur, scenario)
    # every entry halves at the same moment: when a new week starts (weeks since its week; before the season = 0)
    cw = next((w["week"] for w in weeks if w["start"] <= today <= w["end"]), None)
    if cw is None:
        cw = max((w["week"] for w in weeks if w["end"] < today), default=0)
    fade = lambda week: 0.5 ** max(0, cw - (week or 0))

    # one entry per team per period (2026-10-25, restored): every add / drop a team makes between one period's lock and
    # the next is one line — moves inside one period are linked (the drop that made room for the pickup). A player who came
    # and went (or left and came back) inside the same period drops out — no change.
    # the week a move is for: the week it was made in, or the next one once that week's rosters have locked (a move on
    # Saturday of week 1 is a week 2 move — 2026-10-24: Jerome for Harden)
    from .waivers import week_locks
    locks = week_locks(cur, lg, weeks, False)  # every week's first lock, one query
    lock_at = {wn: datetime.fromisoformat(fl["at"]) if fl.get("at") else None for wn, fl in locks.items()}
    label_of = {w["week"]: w["label"] for w in weeks}
    # a period = one matchup unit (2026-10-29): a 2-week playoff round (two legs) is one period — one entry per team,
    # filed under its first leg's week and the round's name (the waiver order counts it the same way)
    period_of, period_label = {}, {}
    for w in weeks:
        if w["kind"] == "playoffs" and (w.get("legs") or 1) > 1:
            period_of[w["week"]] = next(x["week"] for x in weeks if x["kind"] == "playoffs" and x.get("round_index") == w.get("round_index"))
            period_label[w["week"]] = w.get("round") or w["label"]
        else:
            period_of[w["week"]], period_label[w["week"]] = w["week"], w["label"]
    moved = []
    for g in items:
        wk = g["week"]
        if wk and lock_at.get(wk) and datetime.fromisoformat(g["at"]) >= lock_at[wk] and wk + 1 in label_of:
            wk = wk + 1
        if wk:
            g = {**g, "week": period_of.get(wk, wk), "week_label": period_label.get(wk) or label_of.get(wk)}
        moved.append(g)
    items = moved
    seen = {}  # (team, week) -> (ids added, ids dropped) that week
    for g in items:
        a, d = seen.setdefault((g["team_id"], g["week"] or 0), (set(), set()))
        a.update(p["id"] for p in g["adds"])
        d.update(p["id"] for p in g["drops"])
    bursts = []  # newest first; each starts at its newest move
    for g in items:  # newest first
        t = datetime.fromisoformat(g["at"])
        b = next((b for b in bursts if b["team_id"] == g["team_id"] and (b["week"] or 0) == (g["week"] or 0)), None)
        if b is None:
            b = {"kind": "moves", "key": f"{g['team_id']}-{g['week'] or 0}", "team_id": g["team_id"], "team_name": g["team_name"],
                 "week": g["week"], "week_label": g["week_label"], "at": g["at"], "asof": g["asof"], "_t": t,
                 "_via": False, "adds": {}, "drops": {}}
            bursts.append(b)
        # "via" belongs to each player, not the whole entry (2026-10-27: Dosunmu; 2026-10-29: 'trade' too, on adds and
        # drops) — the Transaction Log's own per-player via
        for p in g["adds"]:
            b["adds"].setdefault(p["id"], p)
        for p in g["drops"]:
            b["drops"].setdefault(p["id"], p)
        b["_via"] = b["_via"] or g["via"] == "waivers"
    entries = []
    for b in bursts:
        wk = b["week"] or 0
        a, d = seen[(b["team_id"], wk)]
        both = a & d
        # every add shows right away with the drop it came with (2026-10-25: no waiting for him to lock in); a move for a
        # week that hasn't started counts at full weight (fade = 1)
        adds = [p for i, p in b["adds"].items() if i not in both]
        drops = [p for i, p in b["drops"].items() if i not in both]
        if not adds and not drops:
            continue
        impact = max((value(p["id"], b["week"]) for p in adds + drops), default=0.0)  # frozen at its week
        e = {k: v for k, v in b.items() if not k.startswith("_")}
        entries.append({**e, "adds": adds, "drops": drops, "via": "waivers" if adds and b["_via"] else None,
                        "_score": impact * fade(b["week"])})

    # the draft: one entry, its three biggest picks
    from .draft import _picks
    picks = _picks(cur, scenario)
    cur.execute("SELECT status, completed_at FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    d = cur.fetchone()
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s", (scenario,))
    team_names = {r["id"]: r["name"] for r in cur.fetchall()}
    if picks and d and d["status"] == "complete":
        def val(p):
            return p.get("price") if p.get("price") is not None else value(p["player_id"] or p["nba_team_id"], 0)
        top = sorted(picks, key=val, reverse=True)[:3]
        at = d["completed_at"] or max(p["picked_at"] for p in picks)
        impact = max((value(p["player_id"] or p["nba_team_id"], 0) for p in top), default=0.0)
        entries.append({"kind": "draft", "at": at.isoformat(), "total": len(picks), "_score": impact * fade(0),
                        "top": [{"id": p["player_id"] or p["nba_team_id"], "name": p["name"], "kind": "player" if p["player_id"] else "nba_team",
                                 "position": p.get("position"), "price": p.get("price"), "team_id": p["team_id"], "team_name": team_names.get(p["team_id"])}
                                for p in top]})

    # most important first (2026-10-23): the Home box shows as many as fit, so the cut drops the least important
    shown = sorted(entries, key=lambda e: (e["_score"], e["at"]), reverse=True)[:TOP]
    for e in shown:
        e.pop("_score", None)
    return {"as_of": today.isoformat(), "current_week": next((w["week"] for w in weeks if w["start"] <= today <= w["end"]), None),
            "entries": shown}

