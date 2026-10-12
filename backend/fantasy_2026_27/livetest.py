"""Throwaway live-test league (scenario `livetest`, season label "test-live"), 2026-10-12: Wolves vs Knicks scored off
tonight's MIN @ NYK preseason game (NBA 0012600043), to build and feel the live look (backend/nba/live.py).

setup() (admin, re-runnable):
- League: 2 teams, G / F / C / TM / FLX + 4 bench, one regular week (Oct 12–18) + a 1-week final (a placeholder game on
  Oct 19 makes that second week exist).
- Tonight's game is copied under season "test-live" as a regular game ("T" + id; live.MIRRORS keeps it updated).
- A best game to beat: each team's previous preseason game with its starters (MIN 10/7, NYK 10/8) is pulled from the live feed and copied
  into the same week, dated Oct 12 afternoon ("P" + id).
- Rosters from those box scores (NBA ids); players missing from fantasy_players are added.
"""
from datetime import date, datetime, timezone

from psycopg2.extras import Json

from backend.nba import live
from backend.nba.injuries import name_key

SCENARIO, SEASON, TONIGHT = "livetest", "test-live", "0012600043"
PRIOR = {"MIN": "0012600029", "NYK": "0012600035"}  # MIN 10/7 (starters sat 10/10), NYK 10/8
TEAMS = {
    "wolves": ("Wolves Fans", "MIN", ["Anthony Edwards", "Jaden McDaniels", "Rudy Gobert", "LaMelo Ball"],
               ["Terrence Shannon Jr.", "Joan Beringer", "Jonathan Kuminga", "Ayo Dosunmu", "Trey Lyles", "Jaylen Clark"]),
    "knicks": ("Knicks Fans", "NYK", ["Jalen Brunson", "OG Anunoby", "Karl-Anthony Towns", "Mikal Bridges"],
               ["Tyler Kolek", "Mohamed Diawara", "Andre Drummond", "James Wiseman", "Mitchell Robinson", "Miles McBride"]),
}
SETTINGS = {"league_name": "Live test", "team_count": 2, "playoff_teams": 2, "playoff_rounds": [{"name": "Final", "weeks": 1}],
            "playoff_auto": False, "cutoff_days": 0, "fuse_all_star": False,
            "roster_slots": {"G": 1, "F": 1, "C": 1, "TEAM": 1, "FLEX": 1, "BENCH": 4}}
POS = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}


def setup(cur) -> dict:
    cur.execute("INSERT INTO fantasy_leagues (scenario, season) VALUES (%s, %s) ON CONFLICT (scenario) DO UPDATE SET season = EXCLUDED.season",
                (SCENARIO, SEASON))
    cur.execute("UPDATE fantasy_leagues SET settings = %s, sim_date = NULL WHERE scenario = %s", (Json(SETTINGS), SCENARIO))
    # tonight's game + the placeholder for the final week
    cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, tipoff_utc, status, status_text, home_team, away_team, label)
                   SELECT 'T' || game_id, %s, 'regular', game_date, tipoff_utc, status, status_text, home_team, away_team, 'Live test'
                   FROM nba_games WHERE game_id = %s ON CONFLICT (game_id) DO NOTHING""", (SEASON, TONIGHT))
    cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, tipoff_utc, status, home_team, away_team, label)
                   VALUES ('TPLACE1', %s, 'regular', '2026-10-19', '2026-10-20T00:00:00Z', 'scheduled', 'MIN', 'NYK', 'Live test final')
                   ON CONFLICT (game_id) DO NOTHING""", (SEASON,))
    # the earlier game each team plays "this week": pulled, copied as P + id, dated Oct 12 afternoon (old copies removed)
    keep = ["P" + g for g in PRIOR.values()]
    for tbl in ("nba_player_games", "nba_team_game_stats", "nba_live_state", "nba_live_snapshots", "nba_games"):
        cur.execute(f"DELETE FROM {tbl} WHERE game_id LIKE 'P%%' AND NOT (game_id = ANY(%s))"
                    + (" AND game_id IN (SELECT game_id FROM nba_games WHERE season = %s)" if tbl != "nba_games" else " AND season = %s"),
                    (keep, SEASON))
    box_players = {}
    for tri, gid in PRIOR.items():
        live.MIRRORS[gid] = [(SEASON, "P")]
        cur.execute("SELECT game_id, season, game_type, game_date FROM nba_games WHERE game_id = %s", (gid,))
        live.pull_game(cur, dict(cur.fetchone()))
        cur.execute("UPDATE nba_games SET game_date = '2026-10-12', tipoff_utc = '2026-10-12T17:00:00Z' WHERE game_id = %s", ("P" + gid,))
        cur.execute("UPDATE nba_team_game_stats SET game_date = '2026-10-12' WHERE game_id = %s", ("P" + gid,))
        box = live.fetch(f"boxscore/boxscore_{gid}.json")["game"]
        t = box["homeTeam"] if box["homeTeam"]["teamTricode"] == tri else box["awayTeam"]
        box_players[tri] = {name_key(p["name"]): p for p in t["players"]}
    # teams + rosters
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (SCENARIO,))
    cur.execute("DELETE FROM fantasy_teams WHERE scenario = %s", (SCENARIO,))
    report = {}
    for key, (name, tri, starters, bench) in TEAMS.items():
        tid = f"{SCENARIO}:{key}"
        cur.execute("INSERT INTO fantasy_teams (id, scenario, owner_user_id, name, abbreviation, glyph) VALUES (%s, %s, NULL, %s, %s, 'swish')",
                    (tid, SCENARIO, name, tri))
        found, missing = [], []
        for n in starters + bench:
            p = box_players[tri].get(name_key(n))
            (found if p else missing).append((n, p))
        slots = ["G", "F", "C", "FLEX"]
        bench_left = SETTINGS["roster_slots"]["BENCH"]
        for i, (n, p) in enumerate(found):
            pid = str(p["personId"])
            pos = POS.get((p.get("position") or "").upper(), "F")
            cur.execute("INSERT INTO fantasy_players (id, name, position, nba_team) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                        (pid, p["name"], pos, tri))
            cur.execute("SELECT position FROM fantasy_players WHERE id = %s", (pid,))
            fpos = (cur.fetchone()["position"] or pos)[:1]
            want = n in starters
            slot = None
            if want:
                slot = fpos if fpos in slots else ("FLEX" if "FLEX" in slots else None)
                if slot:
                    slots.remove(slot)
            if not slot and bench_left:
                slot, bench_left = "BENCH", bench_left - 1
            if slot:
                cur.execute("""INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id) VALUES (%s, %s, %s, %s)
                               ON CONFLICT (scenario, player_id) DO NOTHING""", (SCENARIO, tid, slot, pid))
        cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, nba_team_id) VALUES (%s, %s, 'TEAM', %s)", (SCENARIO, tid, tri))
        report[key] = {"missing": [n for n, _ in missing], "open_starter_spots": slots}
    from .schema import assign_default_colors
    assign_default_colors(cur, SCENARIO)
    return report
