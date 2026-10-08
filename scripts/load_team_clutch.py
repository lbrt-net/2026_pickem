"""Load the inputs for TEAM scoring (TEAM_SCORING.md, draft 6) and player clutch scoring (SCORING_SCALE.md) into the
app, from nba-pipeline's raw files (pulled by pull_league_seasons.py, pull_team_daily.py, pull_player_clutch.py):

  team games  — per team-game: opponent fast-break / paint points (TeamGameLogs Misc), opponent turnovers incl. team
                turnovers (Opponent logs OPP_TOV), our / their defensive rebounds, and shot clock violations forced
                (the opponent's own SHOT_CLOCK that day — each team plays at most once a day)
                → POST /nba/admin/team-games
  clutch      — points scored in clutch time per player-game (LeagueDashPlayerClutch by day)
                → POST /nba/admin/clutch (first chunk of a season resets that season's played games to 0)
  team proj   — 2026-27 TEAM projections (proj_avg, proj_max per team) from team_draft4.json
                → POST /fantasy/2026_27/admin/team-pool/load

    python3 scripts/load_team_clutch.py                         # dry run: counts per season
    python3 scripts/load_team_clutch.py --post                  # '23–'26 team games + clutch to prod
    python3 scripts/load_team_clutch.py --post --team-proj path/to/team_draft4.json

Then rebuild history (POST /fantasy/2026_27/admin/history/build). Loads INTERNAL_API_KEY from .env. Safe to re-run.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]
CHUNK = 2000


def _rows(path: Path) -> list[dict]:
    """A stats.nba.com response file → list of dicts (first result set)."""
    j = json.load(open(path))
    rs = j["resultSets"][0] if isinstance(j["resultSets"], list) else j["resultSets"]
    return [dict(zip(rs["headers"], r)) for r in rs["rowSet"]]


def _mdy(d: str) -> str:
    return datetime.strptime(d, "%m/%d/%Y").strftime("%Y-%m-%d")


def team_games(season: str) -> list[dict]:
    base = _rows(RAW / "team_logs_base" / f"{season}.json")
    misc = {(r["GAME_ID"], r["TEAM_ABBREVIATION"]): r for r in _rows(RAW / "team_logs_misc" / f"{season}.json")}
    opp = {(r["GAME_ID"], r["TEAM_ABBREVIATION"]): r for r in _rows(RAW / "team_logs_opponent" / f"{season}.json")}
    abbr = {r["TEAM_ID"]: r["TEAM_ABBREVIATION"] for r in base}
    # each team's own violations by date → forced = the opponent's
    viol = {}
    vf = RAW / "team_violations" / f"{season}.json"
    if vf.exists():
        for d, block in json.load(open(vf)).items():
            for r in (dict(zip(block["headers"], x)) for x in block["rows"]):
                if r["TEAM_ID"] in abbr:
                    viol[(_mdy(d), abbr[r["TEAM_ID"]])] = r.get("SHOT_CLOCK")
    by_game = {}
    for r in base:
        by_game.setdefault(r["GAME_ID"], []).append(r["TEAM_ABBREVIATION"])
    out = []
    for r in base:
        if r["GAME_ID"][2] != "2":  # regular season only
            continue
        team, gid = r["TEAM_ABBREVIATION"], r["GAME_ID"]
        other = [t for t in by_game[gid] if t != team]
        date = r["GAME_DATE"][:10]
        m, o = misc.get((gid, team), {}), opp.get((gid, team), {})
        out.append({
            "game_id": gid, "team": team, "season": season, "game_date": date,
            "opp_pts_fb": m.get("OPP_PTS_FB"), "opp_pts_paint": m.get("OPP_PTS_PAINT"),
            "opp_tov": o.get("OPP_TOV"), "dreb": r.get("DREB"), "opp_dreb": o.get("OPP_DREB"),
            "shot_clock_forced": viol.get((date, other[0])) if other else None,
        })
    for x in out:  # ints for the INTEGER columns
        for k in ("opp_pts_fb", "opp_pts_paint", "opp_tov", "dreb", "opp_dreb", "shot_clock_forced"):
            x[k] = None if x[k] is None else int(round(x[k]))
    return out


def clutch(season: str) -> list[dict]:
    f = RAW / "player_clutch" / f"{season}.json"
    if not f.exists():
        return []
    out = []
    for d, block in json.load(open(f)).items():
        for r in (dict(zip(block["headers"], x)) for x in block["rows"]):
            out.append({"player_id": str(r["PLAYER_ID"]), "game_date": _mdy(d), "pts": int(r["PTS"] or 0)})
    return out


def post(base: str, key: str, path: str, body: dict) -> dict:
    r = requests.post(f"{base}{path}", json=body, headers={"X-Internal-Key": key}, timeout=300)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--season", choices=SEASONS)
    ap.add_argument("--base", default="https://lbrt.net")
    ap.add_argument("--team-proj", help="team_draft4.json (TEAM_SCORING.md projections) to load for 2026-27")
    args = ap.parse_args()
    key = os.environ.get("INTERNAL_API_KEY", "")
    if args.post and not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")

    for season in [args.season] if args.season else SEASONS:
        tg, cl = team_games(season), clutch(season)
        missing_viol = sum(1 for x in tg if x["shot_clock_forced"] is None)
        print(f"{season}: {len(tg)} team-games ({missing_viol} without violations), {len(cl)} clutch rows")
        if not args.post:
            continue
        for i in range(0, len(tg), CHUNK):
            post(args.base, key, "/nba/admin/team-games", {"rows": tg[i:i + CHUNK]})
        for i in range(0, max(len(cl), 1), CHUNK):
            out = post(args.base, key, "/nba/admin/clutch", {"season": season, "reset": i == 0, "rows": cl[i:i + CHUNK]})
        print(f"  posted; clutch games updated in the last chunk: {out.get('updated')}")

    if args.team_proj:
        res = json.load(open(args.team_proj))["res"]
        proj = res[sorted(res)[-1]]["proj"]  # the file's current draft
        rows = [{"team": p["team"], "proj_avg": round(p["proj_avg"], 2), "proj_max": round(p["proj_max"], 2)} for p in proj]
        print(f"team projections: {len(rows)} teams")
        if args.post:
            print(post(args.base, key, "/fantasy/2026_27/admin/team-pool/load", {"season": "2026-27", "rows": rows}))


if __name__ == "__main__":
    main()
