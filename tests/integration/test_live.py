"""Live pull (backend/nba/live.py) on a real finished game's feed (London @ Portland preseason, 2026-10-12, saved)."""
import json
from pathlib import Path

from backend.nba import live

DATA = Path(__file__).parent / "data"


def fake_fetch(path):
    kind = "box" if path.startswith("boxscore") else "pbp"
    return json.loads((DATA / f"live_{kind}_0012600042.json").read_text())


def test_pull_writes_player_lines_team_stats_state_and_snapshot(league, monkeypatch):
    cur = league.cur
    monkeypatch.setattr(live, "fetch", fake_fetch)
    cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team)
                   VALUES ('0012600042', '2026-27', 'preseason', '2026-10-12', 'scheduled', 'POR', 'LON') ON CONFLICT DO NOTHING""")
    out = live.pull_game(cur, {"game_id": "0012600042", "season": "2026-27", "game_type": "preseason", "game_date": "2026-10-12"})
    assert out["status"] == "final" and out["players"] > 20
    box = fake_fetch("boxscore")["game"]
    p = box["homeTeam"]["players"][0]
    cur.execute("SELECT pts, minutes, oreb FROM nba_player_games WHERE game_id = '0012600042' AND player_id = %s", (str(p["personId"]),))
    r = cur.fetchone()
    assert r["pts"] == p["statistics"]["points"] and r["oreb"] == p["statistics"]["reboundsOffensive"] and r["minutes"] > 0
    cur.execute("SELECT status, home_score FROM nba_games WHERE game_id = '0012600042'")
    g = cur.fetchone()
    assert g["status"] == "final" and g["home_score"] == box["homeTeam"]["score"]
    cur.execute("SELECT count(*) AS n FROM nba_team_game_stats WHERE game_id = '0012600042'")
    assert cur.fetchone()["n"] == 2
    cur.execute("SELECT count(*) AS n FROM nba_live_snapshots WHERE game_id = '0012600042'")
    assert cur.fetchone()["n"] == 1


def test_clutch_is_last_five_minutes_within_five():
    # in game order: the score before a play is the one after the play before it
    acts = [{"actionType": "2pt", "shotResult": "Made", "period": 4, "clock": "PT06M00.00S", "scoreHome": "97", "scoreAway": "98", "personId": 8},
            {"actionType": "3pt", "shotResult": "Made", "period": 4, "clock": "PT02M00.00S", "scoreHome": "100", "scoreAway": "98", "personId": 7},
            {"actionType": "rebound", "period": 4, "clock": "PT01M30.00S", "scoreHome": "110", "scoreAway": "100", "personId": 5},
            {"actionType": "2pt", "shotResult": "Made", "period": 4, "clock": "PT01M00.00S", "scoreHome": "112", "scoreAway": "100", "personId": 9},
            {"actionType": "turnover", "subType": "shot clock", "teamTricode": "NYK", "period": 2, "clock": "PT05M00.00S"}]
    clutch, scv, now = live.clutch_and_violations(acts)
    assert clutch == {7: 3} and scv == {"NYK": 1} and now is False
