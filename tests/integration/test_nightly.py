"""The nightly box score + play-by-play job (backend/nba/nightly.py, NIGHTLY.md), replaying a real saved CDN game."""
import copy
import json
from datetime import date, timedelta
from pathlib import Path

from backend.nba import nightly, shot_fields

DATA = Path(__file__).parent / "data"
GID = "0012600042"
BOX = json.loads((DATA / f"live_box_{GID}.json").read_text())
PBP = json.loads((DATA / f"live_pbp_{GID}.json").read_text())
DAY = date(2026, 10, 12)


def _setup(league, monkeypatch):
    league.cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team, home_score, away_score)
                          VALUES (%s, 'test-nightly', 'regular', %s, 'final', %s, %s, %s, %s)""",
                       (GID, DAY, BOX["game"]["homeTeam"]["teamTricode"], BOX["game"]["awayTeam"]["teamTricode"],
                        BOX["game"]["homeTeam"]["score"], BOX["game"]["awayTeam"]["score"]))
    league.commit()
    monkeypatch.setattr(nightly, "today_central", lambda: DAY + timedelta(days=1))


def _lines(league):
    league.cur.execute("SELECT player_id, ast, pts FROM nba_player_games WHERE game_id = %s", (GID,))
    return {r["player_id"]: (r["ast"], r["pts"]) for r in league.cur.fetchall()}


def test_loads_checks_and_reruns_cleanly(league, monkeypatch):
    _setup(league, monkeypatch)
    out = nightly.run("test", fetcher=lambda gid: (BOX, PBP))
    assert out["ok"] and out["games"] == 1 and out["changed"] == 0
    assert len(_lines(league)) > 10
    league.cur.execute("SELECT kind FROM nba_live_raw WHERE game_id = %s ORDER BY kind", (GID,))
    assert [r["kind"] for r in league.cur.fetchall()] == ["boxscore", "playbyplay"]
    again = nightly.run("test", fetcher=lambda gid: (BOX, PBP))  # same feed → nothing changes
    assert again["ok"] and again["changed"] == 0


def test_correction_is_written_and_counted(league, monkeypatch):
    _setup(league, monkeypatch)
    nightly.run("test", fetcher=lambda gid: (BOX, PBP))
    fixed = copy.deepcopy(BOX)
    p = next(p for p in fixed["game"]["homeTeam"]["players"] if (p.get("statistics") or {}).get("assists") is not None)
    p["statistics"]["assists"] += 1  # the NBA credits one more assist the next day
    out = nightly.run("test", fetcher=lambda gid: (fixed, PBP))
    assert out["ok"] and out["changed"] == 1
    assert _lines(league)[str(p["personId"])][0] == p["statistics"]["assists"]
    league.cur.execute("SELECT changed, attempts FROM nba_game_loads WHERE game_id = %s", (GID,))
    r = league.cur.fetchone()
    assert r["changed"] == 1 and r["attempts"] == 2


def test_bad_feed_writes_nothing(league, monkeypatch):
    _setup(league, monkeypatch)
    bad = copy.deepcopy(BOX)
    bad["game"]["homeTeam"]["players"][0].setdefault("statistics", {})["points"] = 999
    out = nightly.run("test", fetcher=lambda gid: (bad, PBP))
    assert not out["ok"] and "≠ score" in out["failed"][0]["problems"][0]
    assert _lines(league) == {}  # nothing written; tried again next night
    league.cur.execute("SELECT ok FROM nba_game_loads WHERE game_id = %s", (GID,))
    assert league.cur.fetchone()["ok"] is False


def test_shot_fields_from_play_by_play(league, monkeypatch):
    _setup(league, monkeypatch)
    monkeypatch.setattr(shot_fields, "MIN_SHOTS", 5)  # a preseason game: few shots per player
    out = nightly.run("test", fetcher=lambda gid: (BOX, PBP))
    assert out["shot_fields"]["test-nightly"] > 0
    league.cur.execute("SELECT data FROM nba_shot_fields WHERE season = 'test-nightly' LIMIT 1")
    d = league.cur.fetchone()["data"]
    assert len(d["lvl"]) == d["nx"] * d["ny"] and len(d["d"]) == sum(c != "0" for c in d["lvl"])


def test_only_real_nba_games(league, monkeypatch):
    _setup(league, monkeypatch)
    league.cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team)
                          VALUES ('P0012600027', 'test-nightly', 'regular', %s, 'final', 'AAA', 'BBB')""", (DAY,))
    league.commit()
    assert [g["game_id"] for g in nightly.games_to_pull(league.cur)] == [GID]
