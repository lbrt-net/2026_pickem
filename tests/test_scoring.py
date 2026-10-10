"""Scoring: a fixed set of 10 player games and 3 NBA-team games with varied data (zeros, big lines, missing stats).
The test computes every score itself from the raw columns and the CURRENT rules (scoring.DEFAULT), then checks the
site's scorer gets the same. Change the rules and the checks follow them; they fail only if the site miscalculates —
or if a rule uses a stat this calculator doesn't know yet (add it to RAW_* below, from its source column).
"""
import pytest

from backend.fantasy_2026_27 import scoring
from backend.fantasy_2026_27.logic import player_points, team_game_points

# How each stat comes out of a raw box-score row (independent of the site's own player_line()).
RAW_PLAYER = {
    "pts": lambda r: r.get("pts") or 0, "fg3m": lambda r: r.get("fg3m") or 0,
    "fgx": lambda r: (r.get("fga") or 0) - (r.get("fgm") or 0), "ftx": lambda r: (r.get("fta") or 0) - (r.get("ftm") or 0),
    "oreb": lambda r: r.get("oreb") or 0, "dreb": lambda r: r.get("dreb") or 0, "ast": lambda r: r.get("ast") or 0,
    "stl": lambda r: r.get("stl") or 0, "blk": lambda r: r.get("blk") or 0, "tov": lambda r: r.get("tov") or 0,
    "blkd": lambda r: r.get("blkd") or 0, "clutch_pts": lambda r: r.get("clutch_pts"),
}
# NBA team games: the score, the opponent's, and the defensive columns as stored (nba_team_game_stats).
RAW_TEAM = {
    "pts": lambda g: g["pts"], "pts_allowed": lambda g: g["opp_pts"], "margin": lambda g: g["pts"] - g["opp_pts"],
    "shot_clock_forced": lambda g: g.get("shot_clock_forced"), "fb_pts_allowed": lambda g: g.get("opp_pts_fb"),
    "paint_pts_allowed": lambda g: g.get("opp_pts_paint"), "tov_forced": lambda g: g.get("opp_tov"),
    "dreb_margin": lambda g: None if g.get("dreb") is None or g.get("opp_dreb") is None else g["dreb"] - g["opp_dreb"],
}

PLAYERS = [  # name, raw box score
    ("triple double", dict(pts=31, fgm=12, fga=21, fg3m=1, ftm=6, fta=7, oreb=3, dreb=11, ast=12, stl=2, blk=1, tov=4, blkd=1, clutch_pts=5)),
    ("scoring night", dict(pts=52, fgm=18, fga=34, fg3m=7, ftm=9, fta=10, oreb=1, dreb=5, ast=4, stl=1, blk=0, tov=3, blkd=2, clutch_pts=11)),
    ("all zeros", dict(pts=0, fgm=0, fga=0, fg3m=0, ftm=0, fta=0, oreb=0, dreb=0, ast=0, stl=0, blk=0, tov=0, blkd=0, clutch_pts=0)),
    ("bricklayer", dict(pts=6, fgm=2, fga=17, fg3m=0, ftm=2, fta=8, oreb=0, dreb=2, ast=1, stl=0, blk=0, tov=6, blkd=3, clutch_pts=0)),
    ("rim protector", dict(pts=11, fgm=5, fga=7, fg3m=0, ftm=1, fta=4, oreb=6, dreb=12, ast=1, stl=1, blk=7, tov=1, blkd=0, clutch_pts=2)),
    ("no clutch data", dict(pts=24, fgm=9, fga=18, fg3m=3, ftm=3, fta=3, oreb=1, dreb=6, ast=7, stl=2, blk=1, tov=2, blkd=1)),
    ("no blkd data", dict(pts=18, fgm=7, fga=14, fg3m=2, ftm=2, fta=2, oreb=2, dreb=4, ast=3, stl=0, blk=0, tov=1, clutch_pts=3)),
    ("garbage time", dict(pts=2, fgm=1, fga=1, fg3m=0, ftm=0, fta=0, oreb=0, dreb=1, ast=0, stl=0, blk=0, tov=0, blkd=0, clutch_pts=0)),
    ("all turnovers", dict(pts=4, fgm=2, fga=9, fg3m=0, ftm=0, fta=2, oreb=0, dreb=1, ast=9, stl=0, blk=0, tov=11, blkd=0, clutch_pts=0)),
    ("thief", dict(pts=14, fgm=5, fga=11, fg3m=2, ftm=2, fta=2, oreb=1, dreb=3, ast=5, stl=6, blk=2, tov=2, blkd=0, clutch_pts=4)),
]
TEAMS = [  # name, raw team game
    ("lockdown", dict(pts=104, opp_pts=88, opp_pts_fb=9, opp_pts_paint=34, opp_tov=18, dreb=40, opp_dreb=28, shot_clock_forced=3)),
    ("shootout loss", dict(pts=131, opp_pts=138, opp_pts_fb=24, opp_pts_paint=62, opp_tov=9, dreb=30, opp_dreb=33, shot_clock_forced=0)),
    ("no defensive data", dict(pts=112, opp_pts=109)),
]


def expected(side: dict, raw: dict, how: dict) -> float:
    total = 0.0
    for c in side["components"]:
        assert c["stat"] in how, f"rule {c['id']} uses stat {c['stat']!r} — add it to the test's calculator"
        v = how[c["stat"]](raw)
        if v is None:
            continue  # stat not loaded for this game: the part scores nothing
        if c["type"] == "per_stat":
            total += c["points"] * v
        elif c["type"] == "steps":
            v = max(v, c.get("floor", float("-inf")))
            total += c["points"] * (max(0.0, c["below"] - v) // c["step"])
        else:  # threshold / bonus
            hit = v < c["below"] if "below" in c else v >= c["at_least"]
            total += c["points"] if hit else 0.0
    return total


@pytest.mark.parametrize("name, raw", PLAYERS, ids=[p[0] for p in PLAYERS])
def test_player_game_scores(name, raw):
    rules = scoring.DEFAULT
    assert player_points(raw, rules) == pytest.approx(expected(rules["player"], raw, RAW_PLAYER))


class FakeCursor:
    """Stands in for the database: hands team_extras() the team's stored defensive row."""
    def __init__(self, rows):
        self.rows = rows

    def execute(self, *_):
        pass

    def fetchall(self):
        return self.rows


@pytest.mark.parametrize("name, raw", TEAMS, ids=[t[0] for t in TEAMS])
def test_team_game_scores(name, raw):
    rules = scoring.DEFAULT
    stored = [] if "dreb" not in raw else [{"game_id": "g1", "team": "AAA", **{k: raw.get(k) for k in
              ("opp_pts_fb", "opp_pts_paint", "opp_tov", "dreb", "opp_dreb", "shot_clock_forced")}}]
    extra = scoring.team_extras(FakeCursor(stored), ["g1"]).get(("g1", "AAA"))
    got = team_game_points(raw["pts"] > raw["opp_pts"], raw["pts"], raw["opp_pts"], rules, extra)
    assert got == pytest.approx(expected(rules["team"], raw, RAW_TEAM))


def test_week_score_is_the_best_game():
    # Players and NBA teams are both scored by their best game of the week today.
    assert scoring.DEFAULT["player"]["week"] == "best_game"
    assert scoring.DEFAULT["team"]["week"] == "best_game"
    games = [player_points(raw, scoring.DEFAULT) for _, raw in PLAYERS[:4]]
    assert scoring.week_score(scoring.DEFAULT["player"], games) == max(games)


def test_version_stamp_follows_the_rules():
    side = scoring.DEFAULT["team"]
    v = scoring.side_version(side)
    relabeled = {**side, "components": [{**c, "label": c.get("label", "") + "!"} for c in side["components"]]}
    assert scoring.side_version(relabeled) == v, "renaming a rule doesn't make projections stale"
    changed = {**side, "components": [{**side["components"][0], "points": side["components"][0]["points"] + 1}] + side["components"][1:]}
    assert scoring.side_version(changed) != v, "changing points does"
