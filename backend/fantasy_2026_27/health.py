"""The check-up (GET /admin/health, scripts/data_check.py): looks at the real data and lists what's wrong or out of
date, in plain words. Each check: {"check", "ok", "detail"}. Nothing here changes data.

The pipeline it guards (change the scoring rules → everything below must be rebuilt, or it's flagged):
  rules (scoring.py / league) → player projections + team projections & weekly curves (scripts/build_projections.py)
                              → past-season history '23–'26 (POST /admin/history/build)
                              → draft ranking + Rec bids (read the above live)
"""
from datetime import date, timedelta

from . import projections, scoring as scoring_mod
from .engine import as_of, league, weeks_for_league
from .history import HISTORY_SEASONS
from .logic import fits_somewhere
from .weeks import league_settings


def _c(name, ok, detail=""):
    return {"check": name, "ok": bool(ok), "detail": detail}


def run(cur, scenario: str) -> list:
    out = []
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    settings = league_settings(cur, scenario)

    # 1. The pipeline: everything built for the current rules
    if projections.is_active(cur, season):  # leagues that draft on projections (the replay ranks on the prior season)
        st = projections.build_status(cur, scenario) or {}
        for side in ("player", "team"):
            s = st.get(side)
            out.append(_c(f"{side} projections match the scoring rules", s and not s["stale"],
                          "not loaded" if not s else ("; ".join(s["changes"]) or "built for older rules") if s["stale"] else f"built {s['loaded_at'][:16]}"))
        cur.execute("SELECT count(*) AS n, count(proj_weeks) AS curved FROM fantasy_team_pool WHERE season = %s", (season,))
        r = cur.fetchone()
        out.append(_c("NBA teams have weekly curves", r["n"] >= 30 and r["curved"] == r["n"], f"{r['curved']} of {r['n']} teams"))
    cur.execute("SELECT season, version FROM fantasy_history_builds")
    hist = {x["season"]: x["version"] for x in cur.fetchall()}
    stale = [s for s in HISTORY_SEASONS if hist.get(s) != scoring_mod.DEFAULT["version"]]
    out.append(_c("past-season history scored with the current rules", not stale,
                  f"rebuild {', '.join(stale)} (POST /admin/history/build)" if stale else "all seasons current"))

    # 2. The pool
    pool = projections.pool_for(cur, scenario) or {}
    no_pos = [p["name"] for p in pool.values() if not p.get("position")]
    no_team = [p["name"] for p in pool.values() if not p.get("nba_team")]
    out.append(_c("every pool player has a position", not no_pos, ", ".join(no_pos[:8]) + (" …" if len(no_pos) > 8 else "")))
    out.append(_c("every pool player has an NBA team", not no_team, ", ".join(no_team[:8]) + (" …" if len(no_team) > 8 else "")))
    misfits = [p["name"] for p in pool.values() if not fits_somewhere({"kind": "player", "position": p.get("position")}, settings["roster_slots"])]
    out.append(_c("every pool player fits a roster spot", not misfits, ", ".join(misfits[:8])))

    # 3. Rosters
    total = sum(settings["roster_slots"].values())
    cur.execute("SELECT t.name, count(r.id) AS n FROM fantasy_teams t LEFT JOIN fantasy_rosters r ON r.team_id = t.id "
                "WHERE t.scenario = %s GROUP BY t.name HAVING count(r.id) > %s", (scenario, total))
    over = [f"{x['name']} ({x['n']})" for x in cur.fetchall()]
    out.append(_c(f"no roster over {total} spots", not over, ", ".join(over)))
    cur.execute("""SELECT r.slot, count(*) AS n FROM fantasy_rosters r WHERE r.scenario = %s AND NOT (r.slot = ANY(%s))
                   GROUP BY r.slot""", (scenario, list(settings["roster_slots"])))
    bad = [f"{x['slot']} ×{x['n']}" for x in cur.fetchall()]
    out.append(_c("every roster spot exists in this league's rules", not bad, ", ".join(bad)))

    # 4. Schedule and box scores
    weeks = weeks_for_league(cur, lg)
    out.append(_c("schedule loaded", bool(weeks), f"{len(weeks)} weeks" if weeks else f"no {season} games"))
    if weeks and weeks[0]["start"] <= today:
        cur.execute("""SELECT max(g.game_date) AS last_final FROM nba_games g WHERE g.season = %s AND g.game_type = 'regular'
                       AND g.status = 'final' AND g.game_date <= %s""", (season, today))
        last_final = cur.fetchone()["last_final"]
        cur.execute("""SELECT max(g.game_date) AS last_box FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                       WHERE pg.season = %s AND g.game_date <= %s""", (season, today))
        last_box = cur.fetchone()["last_box"]
        ok = last_final is None or (last_box is not None and last_box >= last_final - timedelta(days=1))
        out.append(_c("box scores keep up with finished games", ok, f"last finished game {last_final}, last box score {last_box}"))
        cur.execute("""SELECT max(g.game_date) AS d FROM nba_team_game_stats s JOIN nba_games g ON g.game_id = s.game_id
                       WHERE g.season = %s AND g.game_date <= %s""", (season, today))
        last_team = cur.fetchone()["d"]
        ok = last_final is None or (last_team is not None and last_team >= last_final - timedelta(days=1))
        out.append(_c("team defensive stats keep up", ok, f"last finished game {last_final}, last team stats {last_team}"))

    # 5. Waivers aren't stuck
    clock = "until_asof <= %s" if scenario == "replay" else "until_at <= now()"
    args = (scenario, today) if scenario == "replay" else (scenario,)
    cur.execute(f"SELECT count(*) AS n FROM fantasy_waivers WHERE scenario = %s AND status = 'open' AND {clock}", args)
    n = cur.fetchone()["n"]
    out.append(_c("no waivers past due", n == 0, f"{n} waiting to settle (they settle on the next page load)" if n else ""))
    return out


def summary(cur, scenario: str) -> dict:
    checks = run(cur, scenario)
    return {"scenario": scenario, "date": date.today().isoformat(), "ok": all(c["ok"] for c in checks),
            "failing": [c for c in checks if not c["ok"]], "checks": checks}
