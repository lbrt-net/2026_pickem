"""Team rosters week by week: who sits in which spot, moving players, and the weekly lineup lock.

- Spots: G / F / C (players listed at that position), TEAM (an NBA team), FLEX (anyone),
  BENCH (anyone, doesn't score). Same rule as logic.open_slot, minus the "first fit" order.
- Lock (per NBA team): each player locks 5 minutes before his NBA team's first game of the week.
  A move that only involves unlocked players changes this week too; otherwise it applies from
  next week. (The replay treats a whole day as played, so it locks on the game day.)
- History (etch.py): fantasy_rosters is the live roster. Each entity's spot for a week is etched when he locks
  (or the week ends) and never rewritten; a week's lineup = etched entities + live ones not etched yet.
"""
from datetime import date, datetime, timedelta, timezone

from .engine import _prev_season, as_of, league, matchup_overrides, week_pairings, weeks_for_league
from .logic import SLOT_POSITIONS, player_points, score_breakdown, team_game_points
from . import opponent as game_factors, projections
from . import etch as etch_mod
from . import scoring as scoring_mod
from .settings import logo_url
from .weeks import IR_LOCK_WEEKS, LOCK_MINUTES, league_settings, slot_list, spot_caps, week_for


def expected_best(scores: list[float], n: int, floor: float | None = None) -> float | None:
    """Projected best single game over `n` games: the expected maximum of n draws from the player's
    own game scores (order statistics), never below `floor` (his best already this week)."""
    if n <= 0 or not scores:
        return floor
    v = sorted(max(x, floor) if floor is not None else x for x in scores)
    m = len(v)
    return sum(x * (((i + 1) / m) ** n - (i / m) ** n) for i, x in enumerate(v))


def _sim_scale(proj: float | None, current: float | None, scores: list, games: list, mode: str) -> float:
    """winprob's draws × this = his projected week (one truth: the win chance can't disagree with the projections).
    The sim's own expected week from his scores, the chance he plays each game and each game's factor, against
    `projected`; the spread stays his own games'."""
    if not proj or not scores or any(len(g) == 4 for g in games):
        return 1.0
    p = [g[0] for g in games]
    fm = (sum(g[0] * g[1] for g in games) / sum(p)) if sum(p) else 1.0
    if mode == "sum":
        e = sum(p) * fm * sum(scores) / len(scores)
        return max(0.0, (proj - (current or 0.0)) / e) if e > 0 else 1.0
    dist = [1.0]  # chance of playing k of the games (each with its own chance)
    for q in p:
        dist = [a * (1 - q) + (dist[i - 1] * q if i else 0.0) for i, a in enumerate(dist + [0.0])]
    sc = [x * fm for x in scores]

    def week(k_scale):
        v = [x * k_scale for x in sc]
        return sum(pk * (expected_best(v, k, current) if k else (current or 0.0)) for k, pk in enumerate(dist))
    lo, hi = 0.0, 4.0  # the expected best rises with the scale: find the one that lands on the projection
    if week(hi) < proj:
        return hi
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if week(mid) < proj else (lo, mid)
    return (lo + hi) / 2


def eligible(entry: dict, slot: str) -> bool:
    if slot in ("FLEX", "BENCH"):
        return True
    if entry["kind"] == "nba_team":
        return slot == "TEAM"
    return slot in SLOT_POSITIONS and entry.get("position") in SLOT_POSITIONS[slot]


def _roster(cur, scenario: str, team_id: str) -> list[dict]:
    """The team's live roster."""
    return etch_mod.live_rosters(cur, scenario, team_id).get(team_id, [])


def _week_games(cur, season: str, week: dict, tricodes: list[str]) -> dict:
    """tricode → that team's regular-season games in the week, in date order."""
    if not tricodes:
        return {}
    cur.execute("""
        SELECT game_id, game_date, tipoff_utc, status, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL
          AND game_date BETWEEN %s AND %s AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        ORDER BY game_date, tipoff_utc NULLS LAST
    """, (season, week["start"], week["end"], tricodes, tricodes))
    out = {}
    for g in cur.fetchall():
        for t in (g["home_team"], g["away_team"]):
            if t in tricodes:
                out.setdefault(t, []).append(g)
    return out


_started = etch_mod.started


def _locked(entry: dict, games: dict, today: date, replay: bool) -> bool:
    gs = games.get(entry["nba_team"]) or []
    return bool(gs) and _started(gs[0], today, replay)


IR_STATUSES = ("Out", "Out For Season", "Day-To-Day")  # the red / yellow dot — only these can go to IR


def ir_lock_week(cur, scenario: str) -> int:
    """The week a move to IR counts from: the current week (0 before the season)."""
    lg = league(cur, scenario)
    today, weeks = as_of(lg), weeks_for_league(cur, lg)
    current = week_for(weeks, today)
    if current:
        return current["week"]
    return 0 if not weeks or today < weeks[0]["start"] else weeks[-1]["week"]


def move(cur, scenario: str, user: dict, team_id: str, entity_id: str, to_slot: str, swap_with: str | None = None,
         week_no: int | None = None, confirm: bool = False) -> dict:
    """Move a player into `to_slot`; if it's full, swap with `swap_with` (who must fit the spot
    he's leaving). Owner or commissioner. Returns {"applies": "now" | "next_week"}.
    `week_no` = the week being viewed: on the current week a locked player can't be moved at all.
    IR: only a player the injury report has out or day-to-day, only with confirm=True; he's then locked on IR (no
    moves, no drop) for the next IR_LOCK_WEEKS weeks."""
    cur.execute("SELECT owner_user_id FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    team = cur.fetchone()
    if not team:
        raise ValueError("no such team")
    if team["owner_user_id"] != user.get("discord_id") and not user.get("is_admin"):
        raise PermissionError("not your team")
    settings = league_settings(cur, scenario)
    caps = spot_caps(settings)
    if to_slot not in caps:
        raise ValueError("this league has no such spot")
    roster = _roster(cur, scenario, team_id)
    by_id = {e["id"]: e for e in roster}
    mover = by_id.get(entity_id)
    if not mover:
        raise ValueError("he isn't on this roster")
    if mover["slot"] == to_slot:
        return {"applies": "now"}
    week_now = ir_lock_week(cur, scenario)
    # IR lock: frozen for every lineup through Week ir_until. Viewing a later week (e.g. Week 6 while Week 5 = his last
    # IR week is being played), he can be moved for that week; his current week keeps the IR spot (applies next week).
    view_week = week_no or week_now
    ir_locked = lambda e: e["slot"] == "IR" and e.get("ir_until") is not None and view_week <= e["ir_until"]
    if ir_locked(mover):
        raise ValueError(f"{mover['name']} is locked on IR through Week {mover['ir_until']}")
    if to_slot == "IR":
        if mover["kind"] != "player":
            raise ValueError("only players can go to IR")
        cur.execute("SELECT status FROM nba_injuries WHERE player_id = %s", (mover["id"],))
        inj = cur.fetchone()
        if not inj or inj["status"] not in IR_STATUSES:
            raise ValueError(f"{mover['name']} isn't on the injury report as out or day-to-day")
        if not confirm:
            raise ValueError(f"confirm first: {mover['name']} will be locked on IR through Week {week_now + IR_LOCK_WEEKS}")
    elif not eligible(mover, to_slot):
        raise ValueError(f"{mover['name']} can't play {to_slot}")
    in_slot = [e for e in roster if e["slot"] == to_slot]
    partner = None
    if len(in_slot) >= caps[to_slot]:
        partner = by_id.get(swap_with) if swap_with else (in_slot[0] if len(in_slot) == 1 else None)
        if not partner or partner["slot"] != to_slot:
            raise ValueError("that spot is full — pick who to swap with")
        if ir_locked(partner):
            raise ValueError(f"{partner['name']} is locked on IR through Week {partner['ir_until']}")
        if mover["slot"] == "IR" or not eligible(partner, mover["slot"]):
            raise ValueError(f"{partner['name']} can't play {mover['slot']}")

    lg = league(cur, scenario)
    today, weeks = as_of(lg), weeks_for_league(cur, lg)
    current = week_for(weeks, today)
    moved = [mover] + ([partner] if partner else [])
    games = _week_games(cur, lg["season"], current, [e["nba_team"] for e in moved]) if current else {}
    now_ok = not current or not any(_locked(e, games, today, scenario == "replay") for e in moved)
    if current and any(e["slot"] == "IR" and e.get("ir_until") is not None and current["week"] <= e["ir_until"] for e in moved):
        now_ok = False  # his last IR week stays IR: the move counts from next week
    if current and week_no == current["week"] and not now_ok:
        raise ValueError("locked for this week — switch to next week to change next week's lineup")

    etch_mod.etch(cur, scenario, lg["season"], weeks, today, team_id)  # history first: whoever locked keeps this week's spot
    if current and not now_ok:  # someone involved is locked: the whole move is next week's, so this week keeps both spots
        for e in moved:
            cur.execute("""INSERT INTO fantasy_lineups (scenario, team_id, week, entity_id, slot) VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""", (scenario, team_id, current["week"], e["id"], e["slot"]))
    old_slot = mover["slot"]
    ir_until = week_now + IR_LOCK_WEEKS if to_slot == "IR" else None  # locked from next week, 4 weeks
    cur.execute("UPDATE fantasy_rosters SET slot = %s, ir_until = %s WHERE id = %s", (to_slot, ir_until, mover["row_id"]))
    if partner:
        cur.execute("UPDATE fantasy_rosters SET slot = %s, ir_until = NULL WHERE id = %s", (old_slot, partner["row_id"]))
    return {"applies": "now" if now_ok else "next_week", "ir_until": ir_until}


def _availability(cur, e: dict, season: str, today) -> float:
    """Chance he plays a game: his share of his NBA team's last 20 finished games (NBA teams always play). With fewer
    than 5 team games to go on, 0.9. Games the injury report has him out for are 0 before this is used."""
    if e["kind"] == "nba_team" or not e.get("nba_team"):
        return 1.0
    key = (e["id"], season, today)
    if key in _AVAIL:
        return _AVAIL[key]
    cur.execute("""SELECT game_id FROM nba_games WHERE season = %s AND game_type = 'regular' AND status = 'final'
                   AND game_date <= %s AND (home_team = %s OR away_team = %s) ORDER BY game_date DESC LIMIT 20""",
                (season, today, e["nba_team"], e["nba_team"]))
    ids = [r["game_id"] for r in cur.fetchall()]
    if len(ids) < 5:
        val = 0.9
    else:
        cur.execute("SELECT count(*) AS n FROM nba_player_games WHERE player_id = %s AND minutes > 0 AND game_id = ANY(%s)", (e["id"], ids))
        val = cur.fetchone()["n"] / len(ids)
    if len(_AVAIL) > 5000:
        _AVAIL.clear()
    _AVAIL[key] = val
    return val


_AVAIL: dict = {}


# Chance a player plays his team's next game after missing its last n games in a row (box scores '22–'25,
# scripts/projection_study/miss_streak.py; '26 checked: 88 / 53 / 39 / 29 / 26 / 20 / 15%). 0 = played the last one.
MISS_STREAK = {0: 0.879, 1: 0.481, 2: 0.359, 3: 0.312, 4: 0.271, 5: 0.230, 6: 0.154}


def _miss_streak(cur, e: dict, season: str, today) -> int:
    """How many of his NBA team's most recent finished games in a row he didn't play (capped at 6)."""
    if e["kind"] == "nba_team" or not e.get("nba_team"):
        return 0
    cur.execute("""SELECT g.game_id, EXISTS (SELECT 1 FROM nba_player_games pg WHERE pg.game_id = g.game_id AND pg.player_id = %s
                                             AND pg.minutes > 0) AS played
                   FROM nba_games g WHERE g.season = %s AND g.game_type = 'regular' AND g.status = 'final' AND g.game_date <= %s
                     AND (g.home_team = %s OR g.away_team = %s) ORDER BY g.game_date DESC LIMIT 6""",
                (e["id"], season, today, e["nba_team"], e["nba_team"]))
    n = 0
    for r in cur.fetchall():
        if r["played"]:
            break
        n += 1
    return n


def _play_prob(cur, e: dict, season: str, today, has_games: bool, k: int, week_score, avail: dict | None) -> float | None:
    """Roster's 1+ Game %: chance he plays at least once this week — live, like win %. Played once → 100%; the week
    over without a game → 0%. Otherwise, over the k games he isn't ruled out for (ESPN Out = 0 before its return
    date): if he played his team's last game, his preseason availability (no zero-game week, then at least one game at
    chance q each); if he's missed its last n in a row, each next game in turn at MISS_STREAK[n], [n+1], … scaled by
    his own availability. NBA teams always play; a player without preseason numbers uses his recent share."""
    if week_score is not None:
        return 1.0
    if not k:
        return 0.0 if has_games else None
    if e["kind"] == "nba_team":
        return 1.0
    q = avail["q"] if avail else _availability(cur, e, season, today)
    streak = _miss_streak(cur, e, season, today)
    if streak == 0:
        if avail:
            return round((1 - avail["zero"]) * (1 - (1 - q) ** k), 3)
        return round(1 - (1 - q) ** k, 3)
    scale = q / MISS_STREAK[0]
    miss_all = 1.0
    for i in range(k):
        miss_all *= 1 - min(1.0, MISS_STREAK[min(streak + i, 6)] * scale)
    return round(1 - miss_all, 3)


def _game_period(cur, game_id: str) -> int:
    cur.execute("SELECT period FROM nba_live_state WHERE game_id = %s", (game_id,))
    st = cur.fetchone()
    return (st and st["period"]) or 1


def _game_fraction(cur, game_id: str) -> float:
    """Share of regulation played so far (from the live state), at least 10% so an early pace doesn't explode."""
    cur.execute("SELECT period, clock FROM nba_live_state WHERE game_id = %s", (game_id,))
    st = cur.fetchone()
    if not st:
        return 1.0
    m = __import__("re").match(r"PT(\d+)M([\d.]+)S", st["clock"] or "")
    left_q = (int(m.group(1)) * 60 + float(m.group(2))) / 60 if m else 0.0
    played = min(48.0, ((st["period"] or 1) - 1) * 12 + (12 - left_q))
    return max(0.1, played / 48)


SNAP_STATS = ("pts", "fgm", "fga", "fg3m", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "blkd", "clutch_pts")


def _updates(cur, game_id: str, player_id: str, rules: dict, labels: dict, n: int = 20) -> list[dict]:
    """His last n changes between pulls (nba_live_snapshots, every 30s): what each update added or took away, by
    category — e.g. +2.5 = AST +1, DREB +0.5, PTS +1 — and his game total after it. Newest first. Up to 20, so a page
    that comes back can replay what it missed."""
    weight = {c["id"]: c["points"] for c in rules["player"]["components"] if c.get("type", "per_stat") == "per_stat" and c.get("points")}
    cur.execute("SELECT pulled_at, period, clock, players FROM nba_live_snapshots WHERE game_id = %s ORDER BY pulled_at DESC LIMIT 200", (game_id,))
    snaps = cur.fetchall()
    lines = [(s_["pulled_at"], s_["period"], s_["clock"], next((p for p in s_["players"] if p["player_id"] == player_id), None)) for s_ in snaps]
    out = []
    for (t, per, clk, now), (_, _, _, before) in zip(lines, lines[1:]):
        if not now:
            continue
        before = before or {k: 0 for k in SNAP_STATS}
        diff = {k: (now.get(k) or 0) - (before.get(k) or 0) for k in SNAP_STATS}
        if not any(diff.values()):
            continue
        bd = scoring_mod.score_game(rules["player"], scoring_mod.player_line(diff))["breakdown"]
        # n = how many of that stat (points ÷ the category's points each): "1 STL +2", "2 FG- −1"
        parts = [{"label": labels.get(k, k), "points": round(v, 1), "n": round(abs(v / weight[k])) if weight.get(k) else None}
                 for k, v in bd.items() if round(v, 1) != 0]
        parts.sort(key=lambda x: -abs(x["points"]))
        total = scoring_mod.score_game(rules["player"], scoring_mod.player_line(now))["total"]
        out.append({"at": t.isoformat(), "period": per, "clock": clk, "delta": round(sum(bd.values()), 1), "parts": parts,
                    "total": round(total, 1)})
        if len(out) >= n:
            break
    return out


def _live_info(cur, e: dict, gl: list[dict], box_rows: dict, rules: dict, labels: dict,
               team_bd: dict | None = None, tlabels: dict | None = None) -> dict | None:
    """While his game is live (live.py pulls every 30s): the clock, on the floor, clutch time, tonight's points against
    his best game this week ("12.5 to beat" / "new best"), and his last updates — what each pull added or took away by
    category. An NBA team shows no score before the 4th quarter, only its pace projection."""
    g = next((x for x in gl if x.get("live")), None)
    if not g:
        return None
    cur.execute("SELECT period, clock, clutch, oncourt, home_score, away_score FROM nba_live_state WHERE game_id = %s", (g["game_id"],))
    st = cur.fetchone() or {}
    best = max((x["points"] for x in gl if x is not g and x["points"] is not None), default=None)
    info = {"period": st.get("period") or 1, "clock": st.get("clock") or "", "clutch": bool(st.get("clutch")),
            "now": round(g["points"], 1) if g["points"] is not None else None, "pace": g.get("pace"),
            "best": round(best, 1) if best is not None else None, "oncourt": False, "min": None, "updates": [],
            # the game's score from his team's side: "MIN 28 – 24 NYK"
            "team": e.get("nba_team"), "opp": g["opp"], "home": g["home"],
            "score": ([st.get("home_score"), st.get("away_score")] if g["home"] else [st.get("away_score"), st.get("home_score")])}
    # the prior best game (players and NBA teams): its date / opponent / minutes for the schedule cell
    pb = max((x for x in gl if x is not g and x["points"] is not None), key=lambda x: x["points"], default=None)
    info["best_game"] = {"date": pb["date"], "opp": pb["opp"], "home": pb["home"], "min": pb.get("min")} if pb else None
    if e["kind"] == "player":
        r = box_rows.get((e["id"], g["game_id"]))
        # tonight's game by category, for the live bar (same blocks as the best-game bar)
        bd = scoring_mod.score_game(rules["player"], scoring_mod.player_line(r))["breakdown"] if r else {}
        parts = [{"label": labels.get(k, k), "points": round(v, 1)} for k, v in bd.items() if k != "blkd" and round(v, 1) != 0]
        parts.sort(key=lambda x: (x["points"] < 0, -abs(x["points"])))
        # the Best bar = his best game before tonight (so it holds still even if tonight slides back under it)
        prior = max((x for x in gl if x is not g and x["points"] is not None), key=lambda x: x["points"], default=None)
        pr = box_rows.get((e["id"], prior["game_id"])) if prior else None
        pbd = scoring_mod.score_game(rules["player"], scoring_mod.player_line(pr))["breakdown"] if pr else {}
        info["best_parts"] = sorted(({"label": labels.get(k, k), "points": round(v, 1)} for k, v in pbd.items() if k != "blkd" and round(v, 1) != 0),
                                    key=lambda x: (x["points"] < 0, -abs(x["points"])))
        info.update(oncourt=e["id"] in (st.get("oncourt") or []), min=round(float(r["minutes"])) if r else 0, parts=parts,
                    updates=_updates(cur, g["game_id"], e["id"], rules, labels))
    elif team_bd is not None:  # an NBA team: its scoring parts tonight (counted from the 4th) and in its prior best game
        def tparts(gid):
            bd = team_bd.get(gid) or {}
            ps = [{"label": (tlabels or {}).get(k, k), "points": round(v, 1)} for k, v in bd.items() if round(v, 1) != 0]
            return sorted(ps, key=lambda x: (x["points"] < 0, -abs(x["points"])))
        info["parts"] = tparts(g["game_id"]) if g["points"] is not None else []
        if pb and pb.get("game_id") in team_bd:
            info["best_parts"] = tparts(pb["game_id"])
    return info


def week_view(cur, scenario: str, team_id: str, week_no: int | None = None, injuries: bool = False, sim: bool = False) -> dict:
    """One team's lineup for one week: each spot's player, his games that week (opponent, date,
    played or not, fantasy points / margin), best game, season points per game, the projection and the lock.
    injuries=True (GET /team/{id}/week/outlook): also each player's current injury (nba_injuries), games he's out for
    marked out, and the projection counting only the games he's expected to play."""
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    replay = scenario == "replay"
    weeks = weeks_for_league(cur, lg)
    current = week_for(weeks, today)
    rules = scoring_mod.league_rules(cur, scenario)
    label = {c["id"]: c["label"] for c in rules["player"]["components"]}
    tlabel = {c["id"]: c["label"] for c in rules["team"]["components"]}
    if week_no is None:
        week = current or (weeks[0] if weeks and today < weeks[0]["start"] else (weeks[-1] if weeks else None))
        # Forward-looking: once every starter on this team has locked this week, open next week.
        if current and week is current:
            nxt = next((w for w in weeks if w["week"] == current["week"] + 1), None)
            starters = [e for e in _roster(cur, scenario, team_id) if e["slot"] not in ("BENCH", "IR")]
            g = _week_games(cur, season, current, sorted({e["nba_team"] for e in starters if e["nba_team"]}))
            if nxt and starters and all(_locked(e, g, today, replay) or not g.get(e["nba_team"]) for e in starters):
                week = nxt
    else:
        week = next((w for w in weeks if w["week"] == week_no), None)
    if not week:
        raise ValueError("no such week")
    settings = league_settings(cur, scenario)
    live = _roster(cur, scenario, team_id)
    waiting = []  # current week: on the team now, counting from next week (joined after his lock, or his spot is taken)
    if week["start"] <= today:  # begun: the week's lineup (etched + live not etched yet), dropped players included
        roster = etch_mod.week_lineups(cur, scenario, season, weeks, today, team_id).get((team_id, week["week"]), [])
        if current and week["week"] == current["week"]:
            ids = {e["id"] for e in roster}
            waiting = [{k: e[k] for k in ("id", "kind", "name", "slot", "position", "nba_team")} for e in live if e["id"] not in ids]
    else:
        roster = live
    is_current = bool(current and current["week"] == week["week"])
    games = _week_games(cur, season, week, sorted({e["nba_team"] for e in roster if e["nba_team"]}))

    pids = [e["id"] for e in roster if e["kind"] == "player"]
    box = {}  # (player_id, game_id) -> points
    box_rows = {}  # (player_id, game_id) -> the box score row
    scores = {}  # player id / tricode -> game scores (this season, + last season when thin)
    season_scores = {}  # player id -> this season's game scores only (the blend toward the season, below)
    season_pts = {}
    # preseason availability (projection input: chance of a zero-game week, else each game with chance q)
    pre_avail = {}
    pre_game = {}  # id -> preseason PROJ AVG (one game), blended with his season by projections.blend
    if pids:
        cur.execute("SELECT player_id, proj_week, proj_avg FROM fantasy_pool WHERE season = %s AND player_id = ANY(%s::text[])",
                    (season, pids))
        curves = {}
        for r in cur.fetchall():
            pre_game[r["player_id"]] = r["proj_avg"]
            if r["proj_week"]:
                curves[r["player_id"]] = r["proj_week"]
                if r["proj_week"].get("avail"):
                    pre_avail[r["player_id"]] = r["proj_week"]["avail"]
    else:
        curves = {}
    if pids:
        cur.execute("""
            SELECT pg.player_id, pg.game_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb,
                   pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts, pg.minutes
            FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
            WHERE pg.season = %s AND g.game_type = 'regular' AND g.game_date <= %s AND pg.player_id = ANY(%s::text[])
        """, (season, today, pids))
        sums = {}
        for r in cur.fetchall():
            if r["minutes"] > 0:
                p = player_points(r, rules)
                box[(r["player_id"], r["game_id"])] = p
                box_rows[(r["player_id"], r["game_id"])] = r
                scores.setdefault(r["player_id"], []).append(p)
                season_scores.setdefault(r["player_id"], []).append(p)
                s = sums.setdefault(r["player_id"], [0.0, 0])
                s[0] += p
                s[1] += 1
            else:
                box[(r["player_id"], r["game_id"])] = None  # dressed, didn't play
        season_pts = {k: round(v[0] / v[1], 1) for k, v in sums.items() if v[1]}
        # Projection input: this season's games, topped up with last season's when there are few.
        thin = [pid for pid in pids if len(scores.get(pid, [])) < 10]
        if thin:
            cur.execute("""
                SELECT pg.player_id, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
                FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND pg.player_id = ANY(%s::text[])
            """, (_prev_season(season), thin))
            for r in cur.fetchall():
                scores.setdefault(r["player_id"], []).append(player_points(r, rules))
        # Still nothing (missed all of last season — Haliburton, Lillard): the most recent season he played, up to three
        # back, so his week isn't projected as zero (2026-10-17: Hit and Run read 23% with Haliburton at 0).
        back = _prev_season(season)
        for _ in range(2):
            empty = [pid for pid in pids if not scores.get(pid)]
            if not empty:
                break
            back = _prev_season(back)
            cur.execute("""
                SELECT pg.player_id, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
                FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND pg.player_id = ANY(%s::text[])
            """, (back, empty))
            for r in cur.fetchall():
                scores.setdefault(r["player_id"], []).append(player_points(r, rules))

    tris = [e["id"] for e in roster if e["kind"] == "nba_team"]
    if tris:
        cur.execute("SELECT team, proj_avg FROM fantasy_team_pool WHERE season = %s AND team = ANY(%s::text[])", (season, tris))
        pre_game.update({r["team"]: r["proj_avg"] for r in cur.fetchall()})
        cur.execute("""
            SELECT game_id, home_team, away_team, home_score, away_score FROM nba_games
            WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL AND game_date <= %s
              AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        """, (season, today, tris, tris))
        tot = {}
        tgames = cur.fetchall()
        tx = scoring_mod.team_extras(cur, [g["game_id"] for g in tgames])
        for g in tgames:
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
                if t in tris:
                    m = team_game_points(mine > theirs, mine, theirs, rules, tx.get((g["game_id"], t)))
                    scores.setdefault(t, []).append(m)
                    season_scores.setdefault(t, []).append(m)
                    s = tot.setdefault(t, [0.0, 0])
                    s[0] += m
                    s[1] += 1
        season_pts.update({k: round(v[0] / v[1], 1) for k, v in tot.items() if v[1]})
        thin_t = [t for t in tris if len(scores.get(t, [])) < 10]
        if thin_t:
            cur.execute("""
                SELECT game_id, home_team, away_team, home_score, away_score FROM nba_games
                WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
                  AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
            """, (_prev_season(season), thin_t, thin_t))
            pgames = cur.fetchall()
            px = scoring_mod.team_extras(cur, [g["game_id"] for g in pgames])
            for g in pgames:
                for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
                    if t in thin_t:
                        scores.setdefault(t, []).append(team_game_points(mine > theirs, mine, theirs, rules, px.get((g["game_id"], t))))

    wx = scoring_mod.team_extras(cur, [g["game_id"] for gs in games.values() for g in gs]) if tris else {}
    # Current injuries (nba.injuries, present state only). Out → each game before ESPN's estimated return date
    # (every game when there's none) is marked out and left out of his projection; Day-To-Day projects as usual.
    # The report is always read for 1+ Game % (games he's out for = 0); injuries=False leaves the rest untouched.
    inj_all = {}
    if pids:
        cur.execute("""SELECT player_id, status, short, injury, return_date, reported_at FROM nba_injuries
                       WHERE player_id = ANY(%s::text[])""", (pids,))
        inj_all = {r["player_id"]: r for r in cur.fetchall()}
    inj = inj_all if injuries else {}
    OUT = ("Out", "Out For Season", "Suspension")
    # this week's game factors (opponent, home, opponent's back-to-back) for players' numbers: opponent.py
    opp_tbl = game_factors.table(cur, season, today) if pids else None
    out = []
    for e in roster:
        gl = []
        team_bd = {}  # game_id -> that game's team breakdown (NBA team entries)
        hurt = inj.get(e["id"]) if e["kind"] == "player" else None
        hurt_now = inj_all.get(e["id"]) if e["kind"] == "player" else None
        can_play = 0  # games left this week he isn't on the report as out for
        for g in games.get(e["nba_team"], []):
            home = g["home_team"] == e["nba_team"]
            opp = g["away_team"] if home else g["home_team"]
            played = g["game_date"] <= today and g["status"] == "final" if not replay else g["game_date"] <= today
            live_now = not played and g["status"] == "live"  # in progress: its points so far count, updated every pull
            pts = None
            team_end = None
            pace = None  # an NBA team before the 4th quarter: a projection only (its pace), not counted yet
            if played or live_now:
                if e["kind"] == "player":
                    pts = box.get((e["id"], g["game_id"]))
                elif g["home_score"] is not None:
                    mine, theirs = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
                    extra = wx.get((g["game_id"], e["nba_team"]))
                    if live_now and _game_period(cur, g["game_id"]) < 4:
                        # points allowed so far look like a shutout: no score until the 4th, just its pace
                        frac = _game_fraction(cur, g["game_id"])
                        pace = scoring_mod.score_game(rules["team"], scoring_mod.team_line(round(mine / frac), round(theirs / frac), extra))["total"]
                    else:
                        full = scoring_mod.score_game(rules["team"], scoring_mod.team_line(mine, theirs, extra))
                        pts, team_bd[g["game_id"]] = full["total"], full["breakdown"]
                        if live_now:  # 4th quarter on: the score counts as it stands; its projected end = every stat on
                            # pace to the end except shot clock violations (counted as they are)
                            frac = _game_fraction(cur, g["game_id"])
                            ex = {k: (v if k == "shot_clock_forced" or v is None else round(v / frac)) for k, v in (extra or {}).items()}
                            team_end = scoring_mod.score_game(rules["team"], scoring_mod.team_line(round(mine / frac), round(theirs / frac), ex))["total"]
            missing = bool(not played and hurt and hurt["status"] in OUT
                           and (hurt["return_date"] is None or g["game_date"] < hurt["return_date"]))
            can_play += not played and not (hurt_now and hurt_now["status"] in OUT
                                            and (hurt_now["return_date"] is None or g["game_date"] < hurt_now["return_date"]))
            gl.append({"game_id": g["game_id"], "date": g["game_date"].isoformat(), "opp": opp, "home": home, "played": played,
                       "out": missing,
                       "tipoff": g["tipoff_utc"].isoformat() if g.get("tipoff_utc") else None,
                       "points": round(pts, 1) if pts is not None else None,
                       "live": live_now,
                       "pace": round(pace, 1) if pace is not None else None,
                       **({"proj_end": round(team_end, 1)} if team_end is not None else {}),
                       # minutes played (players): shown next to the game's date — a low score in few minutes reads
                       # differently from a bad full game
                       "min": round(box_rows[(e["id"], g["game_id"])]["minutes"])
                              if e["kind"] == "player" and (e["id"], g["game_id"]) in box_rows else None})
        vals = [x["points"] for x in gl if x["points"] is not None]
        side = rules["team" if e["kind"] == "nba_team" else "player"]
        week_score = scoring_mod.week_score(side, vals)
        remaining = sum(1 for x in gl if not x["played"] and not x["out"])  # games he's expected to play
        hist = scores.get(e["id"], [])
        # one game's projection: preseason PROJ AVG blended with this season's games (projections.blend); no
        # preseason number (test leagues) = his own games
        game_proj = projections.blend(pre_game.get(e["id"]), season_scores.get(e["id"], [])) if pre_game.get(e["id"]) is not None else (
            sum(hist) / len(hist) if hist else None)
        if hist and game_proj is not None:  # his week = his own game spread, centred on that number (one truth)
            shift = game_proj - sum(hist) / len(hist)
            hist = [x + shift for x in hist]
        # each game still to come: his number × that game's factor (players; an NBA team's games stay 1.0)
        gf = {}
        for x, g in zip(gl, games.get(e["nba_team"], [])):
            if not x["played"]:
                gf[g["game_id"]] = game_factors.factor(opp_tbl, x["opp"], x["home"], g["game_date"]) if e["kind"] == "player" else 1.0
                if game_proj is not None:
                    x["proj"] = round(game_proj * gf[g["game_id"]], 1)
        ahead = [gf[g["game_id"]] for x, g in zip(gl, games.get(e["nba_team"], [])) if not x["played"] and not x["out"] and not x.get("live")]
        fm = sum(ahead) / len(ahead) if ahead else 1.0  # the week's games, on average: scales what's still to come
        live_proj = None
        if e["kind"] == "player":
            lg_ = next((x for x in gl if x.get("live")), None)
            if lg_:
                # a game in progress, projected to its end: minutes-weighted blend of tonight and his average game —
                # tonight's points so far + his average × the share of his usual minutes still to come
                r_ = box_rows.get((e["id"], lg_["game_id"]))
                played_min = float(r_["minutes"]) if r_ else 0.0
                cur.execute("""SELECT avg(minutes) AS m FROM nba_player_games pg JOIN nba_games ng ON ng.game_id = pg.game_id
                               WHERE pg.player_id = %s AND pg.minutes > 0 AND ng.game_type = 'regular' AND pg.season IN (%s, %s)""",
                            (e["id"], season, _prev_season(season)))
                usual = float((cur.fetchone() or {}).get("m") or 28.0)
                # minutes he's likely to play tonight: his usual; the live demo plays preseason games, where starters
                # go about 20
                tonight = min(usual, 20.0) if season == "test-live" else usual
                avg = sum(hist) / len(hist) if hist else 0.0
                share_left = max(0.0, tonight - played_min) / usual  # his average game per usual minute × minutes left
                live_proj = round((lg_["points"] or 0.0) + avg * share_left, 1)
                lg_["proj_end"] = live_proj
                lg_["min_left"] = share_left
            # the week: the best of (his best so far, tonight's projected end), then the games still to come lift it
            floor = max(x for x in (week_score, live_proj) if x is not None) if (week_score is not None or live_proj is not None) else None
            left = remaining - (1 if lg_ else 0)
            curve = curves.get(e["id"])
            if curve and curve.get("e"):
                # the projection model (projections.py), 2026-10-17: the curve's expected best game at each number of
                # games he plays, weighted by the chance of playing each of the games left (his availability), never
                # below his best this week
                c = [v * fm for v in curve["e"]]
                dist = projections._games_dist(left, curve.get("avail")) if left else [1.0]
                proj = sum(p * (max(c[min(k, len(c)) - 1], floor or 0.0) if k else (floor or 0.0)) for k, p in enumerate(dist))
                # blend toward this season's own games by games PLAYED (commissioner, 2026-10-18): 1/14 per game,
                # all his season after 14; no games (injured, not debuted) = the preseason model unchanged
                mine = season_scores.get(e["id"])
                w = projections.season_weight(len(mine or []))
                if w and left:
                    proj = (1 - w) * proj + w * expected_best([x * fm for x in mine], left, floor)
                if not left and floor is None:
                    proj = None
            else:  # no model (test leagues): his own game scores
                proj = expected_best(hist, left, floor) if left else floor
            best_game = next((x for x in gl if x["points"] is not None and round(x["points"], 1) == week_score), None)
            r = box_rows.get((e["id"], best_game["game_id"])) if best_game else None
            box_line = (f"{r['pts']} PTS · {r['oreb'] + r['dreb']} REB · {r['ast']} AST"
                        + (f" · {r['stl']} STL" if r["stl"] >= 3 else "") + (f" · {r['blk']} BLK" if r["blk"] >= 3 else "")) if r else None
            # Best game's fantasy-point categories (either sign), biggest first, for the matchup page.
            contrib = ([{"label": label.get(k, k), "points": v} for k, v in sorted(score_breakdown(r, rules).items(), key=lambda kv: -abs(kv[1])) if v]
                       if r else [])
            # Same game, every category in rules order (Roster's Points view). BLKD stays out until it's loaded.
            breakdown = {k: v for k, v in score_breakdown(r, rules).items() if k != "blkd"} if r else None
        else:
            avg = sum(hist) / len(hist) if hist else 0.0
            if side["week"] == "best_game":  # a team scored like a player: expected best game
                lg_t = next((x for x in gl if x.get("live") and x.get("proj_end") is not None), None)
                if lg_t:  # 4th quarter: tonight's projected end stands in for that game; later games still lift it
                    floor = max(v for v in (week_score, lg_t["proj_end"]) if v is not None)
                    proj = expected_best(hist, remaining - 1, floor) if remaining > 1 else floor
                else:
                    proj = expected_best(hist, remaining, week_score) if remaining else week_score
            else:  # summed: what's in + the average for each game left
                proj = (week_score or 0.0) + avg * remaining if (remaining or week_score is not None) else None
            box_line = None
            # The team's scoring parts: its best game's (best_game week) or every game's added up (sum week) —
            # today that's the point margin (Δ); with TEAM draft 6, the lines and bonuses it earned.
            played_bd = [team_bd[x["game_id"]] for x in gl if x["game_id"] in team_bd]
            if side["week"] == "best_game":
                best_game = next((x for x in gl if x["game_id"] in team_bd and round(x["points"], 1) == week_score), None)
                bd = team_bd[best_game["game_id"]] if best_game else None
            else:
                bd = {k: round(sum(b[k] for b in played_bd), 1) for k in played_bd[0]} if played_bd else None
            contrib = [{"label": tlabel.get(k, k), "points": v} for k, v in sorted((bd or {}).items(), key=lambda kv: -abs(kv[1])) if v]
            breakdown = bd
        out.append({**{k: v for k, v in e.items() if k not in ("row_id", "added_asof", "added_at")}, "games": [{k: v for k, v in x.items() if k != "game_id"} for x in gl],
                    "week_score": week_score, "box_line": box_line, "contrib": contrib, "breakdown": breakdown,
                    "games_done": sum(1 for x in gl if x["played"]),
                    # the dots: white = finished, orange = live right now, outline = not started (games_left − live)
                    "games_today": sum(1 for x in gl if x.get("live")),
                    "projected": round(proj, 1) if proj is not None else None, "games_left": remaining,
                    "games_out": sum(1 for x in gl if x["out"]),
                    "injury": ({"status": hurt["status"], "short": hurt["short"], "injury": hurt["injury"],
                                "return_date": hurt["return_date"].isoformat() if hurt["return_date"] else None,
                                "reported_at": hurt["reported_at"].isoformat() if hurt["reported_at"] else None} if hurt else None),
                    "season_ppg": season_pts.get(e["id"]),
                    "live": _live_info(cur, e, gl, box_rows, rules, label, team_bd, tlabel),
                    # Roster's "1+ Game %": chance he plays at least once this week (already played → 1)
                    "play_prob": _play_prob(cur, e, season, today, bool(gl), can_play, week_score, pre_avail.get(e["id"])),
                    # One game's projection (shown under each future game): the average game in the projection input.
                    "game_proj": round(game_proj, 1) if game_proj is not None else None,
                    "locked": is_current and _locked(e, games, today, replay),
                    # for winprob.py (sim=True only): his game scores and each remaining game's chance he plays it
                    **({"_sim": {"current": week_score, "scores": hist, "mode": side["week"], "proj": proj,
                                 "games": [((1.0, 1.0, (x.get("proj_end") if e["kind"] == "nba_team" and x.get("proj_end") is not None else x["points"] or 0.0),
                                             x.get("min_left", 0.0)) if x.get("live")
                                            else (0.0 if x["out"] else _availability(cur, e, season, today), gf.get(g["game_id"], 1.0)))
                                           for x, g in zip(gl, games.get(e["nba_team"], [])) if not x["played"]]}}
                       if sim else {})})
    starters = sum(x["week_score"] or 0 for x in out if x["slot"] not in ("BENCH", "IR"))
    starters_proj = sum(x["projected"] or 0 for x in out if x["slot"] not in ("BENCH", "IR"))
    # When this team's lineup starts locking this week: 5 min before its earliest first game.
    firsts = [gs[0] for t, gs in games.items() if gs and t in {e["nba_team"] for e in roster}]
    first = min(firsts, key=lambda g: (g["game_date"], g["tipoff_utc"] or datetime.max.replace(tzinfo=timezone.utc)), default=None)
    lock = None
    if first:
        lock = {"date": first["game_date"].isoformat(),
                "at": (first["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES)).isoformat() if first["tipoff_utc"] and not replay else None}
    # When rosters league-wide start locking this week: 5 min before the week's first game of any team.
    def first_lock(w):
        if not w:
            return None
        cur.execute("""
            SELECT game_date, tipoff_utc FROM nba_games WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s
            ORDER BY game_date, tipoff_utc NULLS LAST LIMIT 1
        """, (season, w["start"], w["end"]))
        g0 = cur.fetchone()
        return ({"week": w["week"], "date": g0["game_date"].isoformat(),
                 "at": (g0["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES)).isoformat() if g0["tipoff_utc"] and not replay else None} if g0 else None)
    week_lock = first_lock(week)
    # Once this week has started locking, the clock counts to the next week's first lock.
    next_lock = first_lock(next((w for w in weeks if w["week"] == week["week"] + 1), None))
    # This week's opponent (same round-robin as the results engine).
    cur.execute("SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url, picture_mode FROM fantasy_teams WHERE scenario = %s", (scenario,))
    teams = []
    for t in cur.fetchall():
        t = dict(t)
        t["logo_url"] = logo_url(t)  # uploaded logo, else the owner's picture (TeamIcon falls back to the glyph)
        del t["logo_updated"], t["picture_url"], t["picture_mode"]
        teams.append(t)
    opponent = None
    if week["kind"] == "regular":
        for a, b in week_pairings(teams, week["week"], matchup_overrides(cur, scenario)):
            if a["id"] == team_id or b["id"] == team_id:
                opponent = b if a["id"] == team_id else a
    return {
        "team_id": team_id, "week": {"week": week["week"], "label": week["label"], "kind": week["kind"],
                                     "start": week["start"].isoformat(), "end": week["end"].isoformat()},
        "current_week": current["week"] if current else None, "as_of": today.isoformat(), "is_current": is_current,
        "weeks": [{"week": w["week"], "label": w["label"], "start": w["start"].isoformat(), "end": w["end"].isoformat()} for w in weeks],
        "roster_slots": settings["roster_slots"], "slot_list": slot_list(settings), "entries": out, "waiting": waiting,
        "ir_list": ["IR"] * settings.get("ir_slots", 0), "ir_week_now": ir_lock_week(cur, scenario), "ir_lock_weeks": IR_LOCK_WEEKS,
        "starters_score": round(starters, 1), "starters_projected": round(starters_proj, 1), "season": season,
        "lock": lock, "week_lock": week_lock, "next_lock": next_lock, "opponent": opponent, "replay": replay,
    }
