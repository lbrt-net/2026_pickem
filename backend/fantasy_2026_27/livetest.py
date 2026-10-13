"""Throwaway live-test league (scenario `livetest`, season label "test-live"), 2026-10-12: Spurs Fans vs Jazz Fans scored
off tonight's SAS @ UTA preseason game (NBA 0012600044; first run used MIN @ NYK, 0012600043), to build and feel the live look (backend/nba/live.py).

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

SCENARIO, SEASON, TONIGHT = "livetest", "test-live", "0012600044"  # was MIN @ NYK (0012600043); now SAS @ UTA
PRIOR = {"SAS": "0012600039", "UTA": "0012600027"}  # SAS 10/10 @ PHX, UTA 10/6 vs DEN
TEAMS = {  # who's playing tonight (the Spurs' stars sat)
    "spurs": ("Spurs Fans", "SAS", ["Jordan McLaughlin", "Julian Champagnie", "Luke Kornet", "Harrison Barnes"],
              ["Keldon Johnson", "Ja'Kobi Gillespie", "Tarris Reed Jr.", "Maliq Brown", "David Jones Garcia"]),
    "jazz": ("Jazz Fans", "UTA", ["Keyonte George", "Lauri Markkanen", "Jaxson Hayes", "Jaren Jackson Jr."],
             ["Darryn Peterson", "Ace Bailey", "Svi Mykhailiuk", "Isaiah Collier"]),
}
SETTINGS = {"league_name": "Live test", "team_count": 2, "playoff_teams": 2, "playoff_rounds": [{"name": "Final", "weeks": 1}],
            "playoff_auto": False, "cutoff_days": 0, "fuse_all_star": False,
            "roster_slots": {"G": 1, "F": 1, "C": 1, "TEAM": 1, "FLEX": 1, "BENCH": 4}}
# Position fallback for players never listed as a starter: the nearest G / F / C centroid by height (in) and weight
# (lb), from the 2026-27 official rosters (nba-pipeline rosters/2026-27.csv): G 76.1 / 199, F 80.2 / 224, C 83.3 / 249.
CENTROIDS = {"G": (76.1, 199.3), "F": (80.2, 224.4), "C": (83.3, 248.9)}
HW = {"Jordan McLaughlin": (71, 185)}  # demo players with no position history: height (in), weight (lb) from the roster file


def by_height_weight(hw):
    if not hw:
        return "F"
    h, w = hw
    return min(CENTROIDS, key=lambda k: ((h - CENTROIDS[k][0]) / 3.5) ** 2 + ((w - CENTROIDS[k][1]) / 25) ** 2)


POS = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}


def setup(cur) -> dict:
    cur.execute("INSERT INTO fantasy_leagues (scenario, season) VALUES (%s, %s) ON CONFLICT (scenario) DO UPDATE SET season = EXCLUDED.season",
                (SCENARIO, SEASON))
    cur.execute("UPDATE fantasy_leagues SET settings = %s, sim_date = NULL WHERE scenario = %s", (Json(SETTINGS), SCENARIO))
    # start clean: drop every test-live game except the ones this setup makes
    keep_all = ["T" + TONIGHT, "TPLACE1"] + ["P" + g for g in PRIOR.values()]
    for tbl in ("nba_player_games", "nba_team_game_stats", "nba_live_state", "nba_live_snapshots"):
        cur.execute(f"DELETE FROM {tbl} WHERE game_id IN (SELECT game_id FROM nba_games WHERE season = %s) AND NOT (game_id = ANY(%s))", (SEASON, keep_all))
    cur.execute("DELETE FROM nba_games WHERE season = %s AND NOT (game_id = ANY(%s))", (SEASON, keep_all))
    cur.execute("UPDATE nba_games SET home_team = 'UTA', away_team = 'SAS' WHERE game_id = 'TPLACE1'")
    # tonight's game + the placeholder for the final week
    cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, tipoff_utc, status, status_text, home_team, away_team, label)
                   SELECT 'T' || game_id, %s, 'regular', game_date, tipoff_utc, status, status_text, home_team, away_team, 'Live test'
                   FROM nba_games WHERE game_id = %s ON CONFLICT (game_id) DO NOTHING""", (SEASON, TONIGHT))
    cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, tipoff_utc, status, home_team, away_team, label)
                   VALUES ('TPLACE1', %s, 'regular', '2026-10-19', '2026-10-20T00:00:00Z', 'scheduled', 'UTA', 'SAS', 'Live test final')
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
    tb = live.fetch(f"boxscore/boxscore_{TONIGHT}.json")["game"]
    for t in (tb["homeTeam"], tb["awayTeam"]):
        for p in t["players"]:
            k = name_key(p["name"])
            if p.get("position") or k not in box_players.get(t["teamTricode"], {}):  # tonight's listing wins when it has a position
                box_players.setdefault(t["teamTricode"], {})[k] = p
    live.pull_game(cur, {"game_id": TONIGHT, "season": "2026-27", "game_type": "preseason", "game_date": "2026-10-12"})
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
            listed = None  # never tonight's box score
            # his team now (traded since); position = what's on file from prior seasons, else by height / weight
            cur.execute("""INSERT INTO fantasy_players (id, name, position, nba_team) VALUES (%s, %s, NULL, %s)
                           ON CONFLICT (id) DO UPDATE SET nba_team = EXCLUDED.nba_team""", (pid, p["name"], tri))
            cur.execute("SELECT position FROM nba_player_games WHERE player_id = %s AND position IS NOT NULL AND substr(game_id, 1, 3) = '002' "
                        "GROUP BY position ORDER BY count(*) DESC LIMIT 1", (pid,))
            hist = cur.fetchone()
            pos = (hist and POS.get(hist["position"].upper())) or by_height_weight(HW.get(p["name"]))
            cur.execute("UPDATE fantasy_players SET position = %s WHERE id = %s", (pos, pid))
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
