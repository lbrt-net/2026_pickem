"""Scoring as data: a league's rulesets and the one function that scores a game with them.

A league has two rulesets, "player" and "team" (fantasy_leagues.scoring; leagues without one use DEFAULT_RULES —
a future season can have different rules than this one). A ruleset is:

    {"week": "best_game" | "sum",            # how a week's games become the weekly score
     "components": [ ... ]}                   # display order = this order

Component types (every component has "id", "label" (short, column header), "name" (plain words)):

    per_stat   {"stat": "pts", "points": 0.5}                     stat × points
    threshold  {"stat": "pts_allowed", "below": 100, "points": 15} points when stat < below (or "at_least": n →
                                                                   stat >= n). Several thresholds on one stat stack.
    bonus      same test as threshold; separate type so pages can group "bonuses" apart from lines.
    steps      {"stat": "pts_allowed", "below": 125, "step": 5, "points": 2}  points for every full `step` the stat
                                                                   is under `below` (96 allowed → 29 under → 5 steps → +10).
                                                                   Optional "floor": count only down to it (below 125,
                                                                   floor 100 → at most 25 under).

A game is a stat line (dict) built by an input source: player_line() from a box score row (+ clutch columns when
loaded, e.g. "clutch_pts"), team_line() from a game's two scores (+ more defensive stats when their loaders land).
score_game() checks nothing silently: a component whose stat isn't in the line counts 0 and is reported as
missing, so a ruleset that needs a loader that isn't in yet is visible instead of quietly wrong.

Every ruleset has a version; stored scores (history, PROJ MAX, results) can record it and rebuild on change.
"""
import copy
import hashlib
import json

# The default rules (FANTASY_SCORING.md + SCORING_SCALE.md + TEAM_SCORING.md): the per-stat player weights plus
# clutch (+2 per point scored in clutch time, so a clutch point is worth 3); NBA teams = TEAM draft 7, best game of
# the week (set below, once TEAM_DRAFT7 is defined). The old team rule (point margin summed) is MARGIN_TEAM.
DEFAULT_RULES = {
    "player": {
        "week": "best_game",
        "components": [
            {"id": "pts", "type": "per_stat", "stat": "pts", "points": 1.0, "label": "PTS", "name": "Points"},
            {"id": "fgx", "type": "per_stat", "stat": "fgx", "points": -0.5, "label": "FG-", "name": "Missed field goals"},
            {"id": "blkd", "type": "per_stat", "stat": "blkd", "points": -0.5, "label": "BLKD", "name": "Own shot blocked"},
            {"id": "fg3m", "type": "per_stat", "stat": "fg3m", "points": 0.5, "label": "3PTM", "name": "3-pointers made"},
            {"id": "ftx", "type": "per_stat", "stat": "ftx", "points": -1.0, "label": "FT-", "name": "Missed free throws"},
            {"id": "oreb", "type": "per_stat", "stat": "oreb", "points": 1.5, "label": "OREB", "name": "Offensive rebounds"},
            {"id": "dreb", "type": "per_stat", "stat": "dreb", "points": 0.5, "label": "DREB", "name": "Defensive rebounds"},
            {"id": "ast", "type": "per_stat", "stat": "ast", "points": 1.0, "label": "AST", "name": "Assists"},
            {"id": "stl", "type": "per_stat", "stat": "stl", "points": 2.0, "label": "STL", "name": "Steals"},
            {"id": "blk", "type": "per_stat", "stat": "blk", "points": 1.5, "label": "BLK", "name": "Blocks"},
            {"id": "tov", "type": "per_stat", "stat": "tov", "points": -2.0, "label": "TO", "name": "Turnovers"},
            {"id": "clutch_pts", "type": "per_stat", "stat": "clutch_pts", "points": 2.0, "label": "CLUTCH",
             "name": "Points in clutch time (+2 on top of the point)"},
        ],
    },
}
MARGIN_TEAM = {
    "week": "sum",
    "components": [
        {"id": "margin", "type": "per_stat", "stat": "margin", "points": 1.0, "label": "Δ", "name": "Point margin"},
    ],
}

# TEAM draft 6 (TEAM_SCORING.md): a ready-made team ruleset for when its inputs are loaded (the opponent's fast-break /
# paint points, turnovers forced, shot clock violations forced, defensive rebounds). Not a default: until a league's
# team games carry those stats, the components that need them would score 0 (reported as missing).
TEAM_DRAFT6 = {
    "week": "best_game",
    "components": [
        {"id": "under125", "type": "steps", "stat": "pts_allowed", "below": 125, "step": 5, "points": 2,
         "label": "<125", "name": "Every 5 points the opponent finishes under 125"},
        {"id": "under100", "type": "threshold", "stat": "pts_allowed", "below": 100, "points": 10,
         "label": "<100", "name": "Hold them under 100"},
        {"id": "shot_clock", "type": "per_stat", "stat": "shot_clock_forced", "points": 2,
         "label": "SCV", "name": "Every shot clock violation forced"},
        {"id": "fast_break", "type": "bonus", "stat": "fb_pts_allowed", "below": 10, "points": 5,
         "label": "FB<10", "name": "Hold them to single-digit fast-break points"},
        {"id": "paint", "type": "bonus", "stat": "paint_pts_allowed", "below": 30, "points": 10,
         "label": "PNT<30", "name": "Hold them under 30 points in the paint"},
        {"id": "tov20", "type": "bonus", "stat": "tov_forced", "at_least": 20, "points": 10,
         "label": "TOV20", "name": "Force 20+ turnovers"},
        {"id": "glass", "type": "bonus", "stat": "dreb_margin", "at_least": 10, "points": 5,
         "label": "DREB+10", "name": "Win the defensive glass by 10+"},
    ],
}

# TEAM draft 7 (commissioner, 2026-10-08): same parts as draft 6, rescaled so a good TEAM's weekly best reads like a
# good player's (top TEAMs project ~33) and steadier week to week: a bigger points base, +2 bonuses (cutoffs set by
# the commissioner 2026-10-08: fast break ≤12, paint ≤40, 15+ turnovers, glass +10; TEAM_SCORING.md).
TEAM_DRAFT7 = {
    "week": "best_game",
    "components": [
        {"id": "under125", "type": "steps", "stat": "pts_allowed", "below": 125, "floor": 100, "step": 1, "points": 1,
         "label": "<125", "name": "Every point the opponent finishes under 125, down to 100 (at most +25)"},
        {"id": "under100", "type": "threshold", "stat": "pts_allowed", "below": 100, "points": 5,
         "label": "<100", "name": "Hold them under 100"},
        {"id": "shot_clock", "type": "per_stat", "stat": "shot_clock_forced", "points": 2,
         "label": "SCV", "name": "Every shot clock violation forced"},
        {"id": "fast_break", "type": "bonus", "stat": "fb_pts_allowed", "below": 13, "points": 2,
         "label": "FB≤12", "name": "Hold them to 12 or fewer fast-break points"},
        {"id": "paint", "type": "bonus", "stat": "paint_pts_allowed", "below": 41, "points": 2,
         "label": "PNT≤40", "name": "Hold them to 40 or fewer points in the paint"},
        {"id": "tov15", "type": "bonus", "stat": "tov_forced", "at_least": 15, "points": 2,
         "label": "TOV15", "name": "Force 15+ turnovers"},
        {"id": "glass", "type": "bonus", "stat": "dreb_margin", "at_least": 10, "points": 2,
         "label": "DREB+10", "name": "Win the defensive glass by 10+"},
    ],
}

DEFAULT_RULES["team"] = TEAM_DRAFT7

TYPES = {"per_stat", "threshold", "bonus", "steps"}
WEEK_MODES = {"best_game", "sum"}


def _g(p, *keys):
    for k in keys:
        if k in p and p[k] is not None:
            return p[k]
    return 0


# ---- input sources: one stat line per entity-game ----

def player_line(p) -> dict:
    """A box score row (or per-game average row) → the player stat line. Derived stats (misses) are made here
    and nowhere else. Extra columns (e.g. clutch_* once loaded) pass through."""
    line = {
        "pts": _g(p, "pts"), "fgm": _g(p, "fgm"), "fga": _g(p, "fga"), "fgx": _g(p, "fga") - _g(p, "fgm"),
        "fg3m": _g(p, "fg3m"), "ftm": _g(p, "ftm"), "fta": _g(p, "fta"), "ftx": _g(p, "fta") - _g(p, "ftm"),
        "oreb": _g(p, "oreb", "off_reb"), "dreb": _g(p, "dreb", "def_reb"), "ast": _g(p, "ast"),
        "stl": _g(p, "stl"), "blk": _g(p, "blk"), "tov": _g(p, "tov"), "blkd": _g(p, "blkd"),
    }
    for k, v in (p.items() if hasattr(p, "items") else []):
        if isinstance(k, str) and k.startswith("clutch_") and v is not None:
            line[k] = v
    return line


def team_line(pts: float, opp_pts: float, extra: dict | None = None) -> dict:
    """One NBA team's game → its stat line. Today: its score and the opponent's. The defensive loaders will add
    opponent turnovers, violations forced, fast-break / paint points allowed, rebounding margin via `extra`."""
    return {"pts": pts, "pts_allowed": opp_pts, "margin": pts - opp_pts, **(extra or {})}


def team_extras(cur, game_ids: list) -> dict:
    """{(game_id, team): the defensive stats loaded for that team-game} from nba_team_game_stats — the `extra` for
    team_line(). Stats not loaded stay out (their components report missing)."""
    if not game_ids:
        return {}
    cur.execute("""SELECT game_id, team, opp_pts_fb, opp_pts_paint, opp_tov, dreb, opp_dreb, shot_clock_forced
                   FROM nba_team_game_stats WHERE game_id = ANY(%s::text[])""", (list(game_ids),))
    out = {}
    for r in cur.fetchall():
        x = {"fb_pts_allowed": r["opp_pts_fb"], "paint_pts_allowed": r["opp_pts_paint"], "tov_forced": r["opp_tov"],
             "shot_clock_forced": r["shot_clock_forced"],
             "dreb_margin": r["dreb"] - r["opp_dreb"] if r["dreb"] is not None and r["opp_dreb"] is not None else None}
        out[(r["game_id"], r["team"])] = {k: v for k, v in x.items() if v is not None}
    return out


# ---- scoring ----

def _component_points(c: dict, line: dict) -> float | None:
    if c["stat"] not in line:
        return None
    v = line[c["stat"]] or 0
    if c["type"] == "per_stat":
        return c["points"] * v
    if c["type"] == "steps":
        v = max(v, c.get("floor", float("-inf")))  # counts only down to the floor (e.g. 125 → 100: at most 25 steps)
        return c["points"] * (max(0.0, c["below"] - v) // c["step"])
    hit = v < c["below"] if "below" in c else v >= c["at_least"]
    return c["points"] if hit else 0.0


def score_game(side: dict, line: dict) -> dict:
    """{"total": float, "breakdown": {component id: points}, "missing": [ids whose stat isn't in the line]}."""
    breakdown, missing = {}, []
    for c in side["components"]:
        pts = _component_points(c, line)
        if pts is None:
            missing.append(c["id"])
            pts = 0.0
        breakdown[c["id"]] = round(pts, 2) + 0.0  # +0.0: no "-0.0"
    return {"total": round(sum(breakdown.values()), 1), "breakdown": breakdown, "missing": missing}


def points(side: dict, line: dict) -> float:
    """Unrounded total of a stat line under a ruleset — for projections (a per-game projection is a fractional
    stat line; rounding each one to 0.1 would add noise). Same component math as score_game."""
    return sum(_component_points(c, line) or 0.0 for c in side["components"])


def week_score(side: dict, game_totals: list[float]) -> float | None:
    """A week's games → the weekly score, per the ruleset's week mode. None when there were no games."""
    if not game_totals:
        return None
    return round(max(game_totals) if side["week"] == "best_game" else sum(game_totals), 1)


# ---- rulesets ----

def validate(rules: dict) -> dict:
    """Raise ValueError on a malformed ruleset; return it with defaults filled in."""
    out = {}
    for side in ("player", "team"):
        s = rules.get(side) or DEFAULT_RULES[side]
        if s.get("week") not in WEEK_MODES:
            raise ValueError(f"{side}: week must be one of {sorted(WEEK_MODES)}")
        ids = set()
        for c in s.get("components") or []:
            if c.get("type") not in TYPES:
                raise ValueError(f"{side}: component type must be one of {sorted(TYPES)}")
            if not c.get("id") or c["id"] in ids or not c.get("stat") or not isinstance(c.get("points"), (int, float)):
                raise ValueError(f"{side}: every component needs a unique id, a stat and numeric points")
            if c["type"] == "steps" and not (isinstance(c.get("below"), (int, float)) and isinstance(c.get("step"), (int, float)) and c["step"] > 0):
                raise ValueError(f"{side}: {c['id']} needs below and a positive step")
            if c["type"] == "steps" and "floor" in c and not (isinstance(c["floor"], (int, float)) and c["floor"] < c["below"]):
                raise ValueError(f"{side}: {c['id']} floor has to be a number under below")
            if c["type"] in ("threshold", "bonus") and ("below" in c) == ("at_least" in c):
                raise ValueError(f"{side}: {c['id']} needs exactly one of below / at_least")
            ids.add(c["id"])
        out[side] = {"week": s["week"], "components": [{"label": c["id"].upper(), "name": c["id"], **c} for c in s["components"]]}
    out["version"] = version(out)
    return out


def version(rules: dict) -> str:
    body = json.dumps({k: rules[k] for k in ("player", "team")}, sort_keys=True)
    return hashlib.sha1(body.encode()).hexdigest()[:10]


SCORED_KEYS = ("type", "stat", "points", "below", "at_least", "step")


def _scored(side: dict) -> dict:
    return {"week": side["week"],
            "components": {c["id"]: {k: c[k] for k in SCORED_KEYS if k in c} for c in side["components"]}}


def side_version(side: dict) -> str:
    """Version of one ruleset (player or team) from what changes scores only — relabeling a component doesn't
    change it. Projections record the version they were built for (projections.record_build)."""
    return hashlib.sha1(json.dumps(_scored(side), sort_keys=True).encode()).hexdigest()[:10]


def changes(old: dict, new: dict) -> list[str]:
    """What differs between two versions of one ruleset, in plain words ("CLUTCH +2 → +3", "added TOV20")."""
    a, b = _scored(old), _scored(new)
    out = [f"week {a['week']} → {b['week']}"] if a["week"] != b["week"] else []
    label = {c["id"]: c.get("label", c["id"]) for c in old["components"] + new["components"]}
    for i in b["components"]:
        if i not in a["components"]:
            out.append(f"added {label[i]}")
        elif a["components"][i] != b["components"][i]:
            x, y = a["components"][i], b["components"][i]
            out.append(f"{label[i]} " + ", ".join(f"{k} {x.get(k, '—')} → {y.get(k, '—')}" for k in SCORED_KEYS if x.get(k) != y.get(k)))
    out += [f"removed {label[i]}" for i in a["components"] if i not in b["components"]]
    return out


DEFAULT = validate(copy.deepcopy(DEFAULT_RULES))


def league_rules(cur, scenario: str) -> dict:
    """The league's rulesets (fantasy_leagues.scoring) if it has its own, else the defaults."""
    cur.execute("SELECT scoring FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    r = cur.fetchone()
    custom = r["scoring"] if r else None
    return validate(custom) if custom else DEFAULT


def describe(rules: dict) -> dict:
    """For pages (GET /scoring): both rulesets' components in display order, plus the week modes."""
    return {"version": rules["version"],
            **{side: {"week": rules[side]["week"], "components": rules[side]["components"]} for side in ("player", "team")}}
