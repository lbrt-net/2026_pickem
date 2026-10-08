"""Shared by the 2026-27 projection build (scripts/build_projections.py runs the steps in order):

- paths: R = nba-pipeline raw data (inputs, and the outputs the loaders read), WORK = the build's own intermediate
  files (persistent, next to the raw data), HERE = these scripts.
- RULES: the scoring rules the build is for — WORK/rules.json, written by build_projections.py from the site's
  GET /scoring (or from backend scoring.py with --rules local). No file → scoring.py's defaults.
- fp(line): fantasy points of a (per-game) stat line under RULES, with the app's own scorer, so a rule change on the
  site flows into every projection number instead of a copy of the weights here.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.fantasy_2026_27 import scoring  # noqa: E402

HERE = Path(__file__).resolve().parent
R = str(Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw") + "/"
WORK = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "derived" / "projections_2026_27"
WORK.mkdir(parents=True, exist_ok=True)
W = str(WORK) + "/"
INPUTS = W + "inputs/"     # frozen study data the build reads but doesn't make ('23–'26 TEAM games, violations)
RULES_FILE = WORK / "rules.json"
RULES = scoring.validate(json.loads(RULES_FILE.read_text())) if RULES_FILE.exists() else scoring.DEFAULT
PLAYER, TEAM = RULES["player"], RULES["team"]


def fp(line) -> float:
    """Fantasy points of one stat line (a box score row or a projected per-game line) under the build's rules.
    Clutch stats are added separately (pmax27.py) — box scores and the per-game projection don't carry them."""
    return scoring.points(PLAYER, scoring.player_line(line))


def clutch_value(clutch_pts_pg: float) -> float:
    """What a projected clutch points per game is worth under the rules (every component on a clutch_* stat)."""
    return scoring.points({"components": [c for c in PLAYER["components"] if c["stat"].startswith("clutch_")]},
                          {"clutch_pts": clutch_pts_pg})


PLAYER_STATS = {"pts", "fgm", "fga", "fgx", "fg3m", "ftm", "fta", "ftx", "oreb", "dreb", "ast", "stl", "blk", "tov", "blkd",
                "clutch_pts"}
# TEAM line stats the build has per '23–'26 team-game (team_build.py → TEAM_LINE)
TEAM_STATS = {"pts", "pts_allowed", "margin", "shot_clock_forced", "fb_pts_allowed", "paint_pts_allowed", "tov_forced",
              "dreb_margin"}


def unsupported(rules: dict | None = None) -> list[str]:
    """Components the projection can't produce a number for (a stat it has no data for) — the build stops on these
    instead of quietly scoring them 0."""
    PLAYER, TEAM = (rules or RULES)["player"], (rules or RULES)["team"]
    # player side: a per-game projection is an average line, so only per-stat components apply to it (a game
    # threshold — e.g. a double-double bonus — needs game-level simulation the build doesn't do yet)
    return [f"player {c['id']} ({c['stat']})" for c in PLAYER["components"] if c["stat"] not in PLAYER_STATS] + \
           [f"player {c['id']} ({c['type']}: only per_stat can be projected)" for c in PLAYER["components"] if c["type"] != "per_stat"] + \
           [f"team {c['id']} ({c['stat']})" for c in TEAM["components"] if c["stat"] not in TEAM_STATS]
