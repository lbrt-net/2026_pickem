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


def _hist_var(hist: list, n: int, qs: list | None, floor: float | None) -> float:
    """Variance of the best of n games drawn like his own games (normal, his own mean and spread) — the swing of a
    projection built from his game scores (NBA teams, test leagues)."""
    if n <= 0 or not hist:
        return 0.0
    m = sum(hist) / len(hist)
    sd = (sum((x - m) ** 2 for x in hist) / len(hist)) ** 0.5
    if m <= 0:
        return n * sd * sd
    return projections.week_dist(m, sd / m, [1.0] * n, None, floor, qs)[1]


def first_lock(cur, season: str, w: dict | None, replay: bool = False) -> dict | None:
    """When rosters league-wide start locking week w: 5 min before its first game of any team. The one lock time for
    every countdown (Home, Roster, Players)."""
    if not w:
        return None
    cur.execute("""
        SELECT game_date, tipoff_utc FROM nba_games WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s
        ORDER BY game_date, tipoff_utc NULLS LAST LIMIT 1
    """, (season, w["start"], w["end"]))
    g0 = cur.fetchone()
    return ({"week": w["week"], "date": g0["game_date"].isoformat(),
             "at": (g0["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES)).isoformat() if g0["tipoff_utc"] and not replay else None} if g0 else None)


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
    lg = league(cur, scenario)
    today, weeks = as_of(lg), weeks_for_league(cur, lg)
    current = week_for(weeks, today)
    if current and week_no == current["week"] and to_slot != "IR" and mover["slot"] != "IR":
        done = _move_this_week(cur, scenario, lg, weeks, today, current, team_id, mover, to_slot, swap_with, caps)
        if done:
            return done
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

    moved = [mover] + ([partner] if partner else [])
    games = _week_games(cur, lg["season"], current, [e["nba_team"] for e in moved]) if current else {}
    now_ok = not current or not any(_locked(e, games, today, scenario == "replay") for e in moved)
    if current and any(e["slot"] == "IR" and e.get("ir_until") is not None and current["week"] <= e["ir_until"] for e in moved):
        now_ok = False  # his last IR week stays IR: the move counts from next week
    if current and week_no == current["week"] and not now_ok:
        raise ValueError("locked for this week — switch to next week to change next week's lineup")

    etch_mod.etch(cur, scenario, lg["season"], weeks, today, team_id)  # history first: whoever locked keeps this week's spot
    before = etch_mod.week_spots(cur, scenario, lg["season"], weeks, today, team_id)
    old_slot = mover["slot"]
    ir_until = week_now + IR_LOCK_WEEKS if to_slot == "IR" else None  # locked from next week, 4 weeks
    cur.execute("UPDATE fantasy_rosters SET slot = %s, ir_until = %s WHERE id = %s", (to_slot, ir_until, mover["row_id"]))
    if partner:
        cur.execute("UPDATE fantasy_rosters SET slot = %s, ir_until = NULL WHERE id = %s", (old_slot, partner["row_id"]))
    # 2026-10-26: a move made for next week never changes the week under way (everyone keeps this week's spot); a move
    # made on this week's view changes both, except that nobody else's spot this week shifts
    this_week = current and (week_no is None or week_no == current["week"]) and now_ok
    etch_mod.keep_week(cur, scenario, lg["season"], weeks, today, team_id, before,
                       skip={e["id"] for e in moved} if this_week else ())
    return {"applies": "now" if now_ok else "next_week", "ir_until": ir_until}


def _move_this_week(cur, scenario, lg, weeks, today, current, team_id, mover, to_slot, swap_with, caps) -> dict | None:
    """A move on this week's view once the week's lineup has split from the roster (someone pinned, 2026-10-26):
    rearranges this week only — players not locked yet, into an open spot or a swap with another one not locked yet.
    None = nobody involved is pinned: the ordinary move (roster and this week together)."""
    wk, spots = etch_mod.week_spots(cur, scenario, lg["season"], weeks, today, team_id)
    cur.execute("SELECT entity_id FROM fantasy_lineups WHERE scenario = %s AND team_id = %s AND week = %s", (scenario, team_id, wk))
    pinned = {r["entity_id"] for r in cur.fetchall()}
    week = etch_mod.week_lineups(cur, scenario, lg["season"], weeks, today, team_id).get((team_id, wk), [])
    there = [e for e in week if e["slot"] == to_slot]
    if mover["id"] not in pinned and not any(e["id"] in pinned for e in there):
        return None
    if mover["id"] not in spots:
        raise ValueError(f"{mover['name']} is locked for this week — switch to next week to change next week's lineup")
    from_slot = spots[mover["id"]]
    if from_slot == to_slot:
        return {"applies": "now"}
    partner = None
    if len(there) >= caps.get(to_slot, 0):
        partner = next((e for e in there if e["id"] == swap_with), None) if swap_with else (there[0] if len(there) == 1 else None)
        if not partner:
            raise ValueError("that spot is full — pick who to swap with")
        if partner["etched"]:
            raise ValueError(f"{partner['name']} is locked for this week")
        if not eligible(partner, from_slot):
            raise ValueError(f"{partner['name']} can't play {from_slot}")
    etch_mod.etch(cur, scenario, lg["season"], weeks, today, team_id)
    for eid, slot in [(mover["id"], to_slot)] + ([(partner["id"], from_slot)] if partner else []):
        cur.execute("""INSERT INTO fantasy_lineups (scenario, team_id, week, entity_id, slot) VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (scenario, team_id, week, entity_id) DO UPDATE SET slot = EXCLUDED.slot""",
                    (scenario, team_id, wk, eid, slot))
    return {"applies": "now"}


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
# A game cut short (2026-10-26, Jaren Jackson Jr. 10 min / Markkanen 6 min, both left hurt): under 40% of his usual
# minutes. scripts/projection_study/injury_exit.py, '21–'25: 2.0% of played games ('26 check 2.3%), worth ~11% of his
# average. After one he plays his team's next 1 / 2 / 3 games 59 / 64 / 65% of the time vs 94 / 92 / 90% after a full
# game: × 0.63 / 0.70 / 0.72.
SHORT_MIN = 0.4
SHORT_SHARE = 0.020
AFTER_SHORT = (0.63, 0.70, 0.72)


def healthy_chances(qs: list[float], since_short: int = 0) -> tuple[float, list[float]]:
    """From each game's chance of playing: (chance of at least one healthy game, each game's chance of being a healthy
    one). A played game is cut short at SHORT_SHARE; the games after a short one play at AFTER_SHORT × their chance.
    since_short = his last short game was this many team games ago (1 = his team's last game), 0 = none lately."""
    dist = {min(since_short, 4) if since_short else 0: 1.0}  # games since a short game (0 = none / long ago) → chance
    none_healthy = dict(dist)  # the same, only the paths with no healthy game yet
    marg = []
    for q in qs:
        nxt, nxt_none, h = {}, {}, 0.0
        for src, out in ((dist, nxt), (none_healthy, nxt_none)):
            for s, p in src.items():
                play = min(1.0, q * (AFTER_SHORT[s - 1] if 1 <= s <= 3 else 1.0))
                full, short = play * (1 - SHORT_SHARE), play * SHORT_SHARE
                if src is dist:
                    h += p * full
                    out[0] = out.get(0, 0.0) + p * full
                out[1] = out.get(1, 0.0) + p * short
                miss_to = (s + 1 if s else 0) if s < 4 else 0
                out[miss_to] = out.get(miss_to, 0.0) + p * (1 - play)
        marg.append(h)
        dist, none_healthy = nxt, nxt_none
    return 1 - sum(none_healthy.values()), marg


_USUAL: dict = {}


def usual_minutes(cur, pid: str, season: str) -> float | None:
    """His median minutes in games he played, this season and last (regular season)."""
    key = (pid, season)
    if key not in _USUAL:
        if len(_USUAL) > 5000:
            _USUAL.clear()
        cur.execute("""SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY pg.minutes) AS m FROM nba_player_games pg
                       JOIN nba_games g ON g.game_id = pg.game_id
                       WHERE pg.player_id = %s AND pg.minutes > 0 AND g.game_type = 'regular' AND pg.season IN (%s, %s)""",
                    (pid, season, _prev_season(season)))
        m = (cur.fetchone() or {}).get("m")
        _USUAL[key] = float(m) if m is not None else None
    return _USUAL[key]


def is_short(minutes, usual: float | None) -> bool:
    return usual is not None and minutes is not None and float(minutes) < SHORT_MIN * usual


def _since_short(cur, e: dict, season: str, today) -> int:
    """How many of his team's finished games ago his last short game was (1 = the last one), if he hasn't played a
    full game since; 0 otherwise. Looks back 4 games."""
    if e["kind"] == "nba_team" or not e.get("nba_team"):
        return 0
    usual = usual_minutes(cur, e["id"], season)
    cur.execute("""SELECT (SELECT pg.minutes FROM nba_player_games pg WHERE pg.game_id = g.game_id AND pg.player_id = %s) AS m
                   FROM nba_games g WHERE g.season = %s AND g.game_type = 'regular' AND g.status = 'final' AND g.game_date <= %s
                     AND (g.home_team = %s OR g.away_team = %s) ORDER BY g.game_date DESC LIMIT 4""",
                (e["id"], season, today, e["nba_team"], e["nba_team"]))
    for i, r in enumerate(cur.fetchall(), 1):
        if r["m"] and float(r["m"]) > 0:
            return i if is_short(r["m"], usual) else 0
    return 0


_STREAK: dict = {}


def _miss_streak(cur, e: dict, season: str, today) -> int:
    """How many of his NBA team's most recent finished games in a row he didn't play (capped at 6)."""
    if e["kind"] == "nba_team" or not e.get("nba_team"):
        return 0
    key = (e["id"], e["nba_team"], season, today)
    if key in _STREAK:
        return _STREAK[key]
    if len(_STREAK) > 5000:
        _STREAK.clear()
    _STREAK[key] = _miss_streak_q(cur, e, season, today)
    return _STREAK[key]


def _miss_streak_q(cur, e: dict, season: str, today) -> int:
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


def _chances(cur, e: dict, season: str, today, k: int, avail: dict | None, hurt: dict | None = None,
             out_now: int = 0) -> tuple[float, list[float]]:
    """The one availability for a week's k games still to play (games ESPN has him Out for are already left out):
    (chance he's out all week, each game's chance). The weekly number, 1+ Game % and the win chance all use this
    (2026-10-18). Misses stack only for an injury: healthy (played his team's last game, not on the report) = each
    game independently at his own per-game chance q (his SCATTERED misses, availability_patterns 2026-10-12 — Kawhi
    ~90%, Haliburton 96%), no week-out chance (the season model's stretch share is a season average, used for season
    value, not for a healthy player's week). Missed his team's last n in a row: each next game in turn at
    MISS_STREAK[n], [n+1], … scaled by his q. ESPN Out games are already left out. No preseason numbers: recent share."""
    if e["kind"] == "nba_team":
        return 0.0, [1.0] * k
    q = avail["q"] if avail else _availability(cur, e, season, today)
    streak = _miss_streak(cur, e, season, today)
    # On the injury report (2026-10-26, week 1 check: Knueppel, Lively, Porter Jr. read 100% and never played — the
    # season had no games yet, so no miss streak, and ESPN's return date was taken as a sure thing): Out → his games
    # after ESPN's estimated return are first games back after a run of misses (at least 2, plus each game he's out
    # this week); Day-To-Day → his next game is one after a miss.
    if hurt and hurt.get("status") in ("Out", "Out For Season", "Suspension"):
        streak = max(streak, 2 + out_now)
    elif hurt:
        streak = max(streak, 1)
    if streak == 0:
        return 0.0, [q] * k
    scale = q / MISS_STREAK[0]
    return 0.0, [min(1.0, MISS_STREAK[min(streak + i, 6)] * scale) for i in range(k)]


def _healthy(cur, e: dict, season: str, today, k: int, avail: dict | None, hurt: dict | None = None,
             out_now: int = 0) -> tuple[float, list[float]]:
    """_chances, then games cut short (2026-10-26): (chance of 1+ healthy game, each game's chance of a healthy one).
    Coming off a short game: each next game at the lower of the miss-streak / injury report chance and AFTER_SHORT."""
    zero, qs = _chances(cur, e, season, today, k, avail, hurt, out_now)
    if e["kind"] == "nba_team":
        return 1.0 if k else 0.0, qs
    since = _since_short(cur, e, season, today)
    if since and (hurt or _miss_streak(cur, e, season, today)):
        # already on the report / missing games: those chances stand for the injury; no second cut
        p, marg = healthy_chances(qs)
    else:
        p, marg = healthy_chances(qs, since)
    return (1 - zero) * p, [(1 - zero) * m for m in marg]


def _play_prob(cur, e: dict, season: str, today, has_games: bool, k: int, healthy_played: bool, avail: dict | None,
               hurt: dict | None = None, out_now: int = 0) -> float | None:
    """Roster's 1+ Game %: chance he plays at least one HEALTHY game this week (2026-10-26: one cut short by an
    injury doesn't count — Jaren Jackson Jr., Markkanen) — live, like win %. A full game played → 100%; the week over
    without one → 0%. Otherwise, over the k games he isn't ruled out for: _healthy (miss streak / injury report
    chances, a 2% chance any game is cut short, and lower chances right after a short game). NBA teams always play."""
    if healthy_played:
        return 1.0
    if not k:
        return 0.0 if has_games else None
    if e["kind"] == "nba_team":
        return 1.0
    return round(_healthy(cur, e, season, today, k, avail, hurt, out_now)[0], 3)


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
               team_bd: dict | None = None, tlabels: dict | None = None, team_lines: dict | None = None) -> dict | None:
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
        # each scoring category: its count now and on pace to the end, and what each is worth (2026-10-20). Before
        # the 4th nothing counts yet (pts_now None), only the pace projection.
        tl = (team_lines or {}).get(g["game_id"])
        if tl:
            now_bd = scoring_mod.score_game(rules["team"], tl["now"])["breakdown"]
            end_bd = scoring_mod.score_game(rules["team"], tl["end"])["breakdown"]
            info["cats"] = [{"label": c["label"], "name": c["name"], "now": tl["now"].get(c["stat"]), "end": tl["end"].get(c["stat"]),
                             "line": c.get("below", c.get("at_least")), "type": c["type"],
                             "pts_now": round(now_bd[c["id"]], 1) if tl["counts"] else None, "pts_end": round(end_bd[c["id"]], 1)}
                            for c in rules["team"]["components"] if c["stat"] in tl["now"]]
            info["proj_end"] = round(sum(end_bd.values()), 1)
    return info


def week_view(cur, scenario: str, team_id: str, week_no: int | None = None, injuries: bool = False, sim: bool = False,
              entities: list | None = None) -> dict:
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
    # entities (projection_log.py): project these instead of a team's roster — rostered or not, week_no required
    live = entities if entities is not None else _roster(cur, scenario, team_id)
    waiting = []  # current week: on the team now, counting from next week (joined after his lock, or his spot is taken)
    if entities is not None:
        roster = entities
    elif week["start"] <= today:  # begun: the week's lineup (etched + live not etched yet), dropped players included
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
    season_scores = {}  # id -> his game scores in the last 4 weeks (this week and the 3 before) — the blend's recent part
    recent_from = projections.recent_start(weeks, today)
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
                if recent_from and r["game_date"] >= recent_from:
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
            SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
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
                    if recent_from and g["game_date"] >= recent_from:
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
        team_lines = {}  # game_id -> a live NBA team game's stat line now and on pace to the end (the category grid)
        hurt = inj.get(e["id"]) if e["kind"] == "player" else None
        hurt_now = inj_all.get(e["id"]) if e["kind"] == "player" else None
        can_play = 0  # games left this week he isn't on the report as out for
        for g in games.get(e["nba_team"], []):
            home = g["home_team"] == e["nba_team"]
            opp = g["away_team"] if home else g["home_team"]
            played = g["game_date"] <= today and g["status"] == "final" if not replay else g["game_date"] <= today
            live_now = not played and g["status"] == "live"  # in progress: its points so far count, updated every pull
            sits = bool(e["kind"] == "player" and hurt_now and hurt_now["status"] in OUT
                        and (hurt_now["return_date"] is None or g["game_date"] < hurt_now["return_date"])
                        and not (box_rows.get((e["id"], g["game_id"])) or {}).get("minutes"))
            if live_now and sits:  # ruled out and hasn't checked in: his game isn't live for him (2026-10-24: LeBron, back)
                live_now = False
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
                        ex = {k: (v if k == "shot_clock_forced" or v is None else round(v / frac)) for k, v in (extra or {}).items()}
                        end_line = scoring_mod.team_line(round(mine / frac), round(theirs / frac), ex)
                        pace = scoring_mod.score_game(rules["team"], end_line)["total"]
                        team_lines[g["game_id"]] = {"now": scoring_mod.team_line(mine, theirs, extra), "end": end_line, "counts": False}
                    else:
                        full = scoring_mod.score_game(rules["team"], scoring_mod.team_line(mine, theirs, extra))
                        pts, team_bd[g["game_id"]] = full["total"], full["breakdown"]
                        if live_now:  # 4th quarter on: it counts at its projected end — every stat on pace to the end
                            # except shot clock violations (counted as they are). Not the score as it stands, which can
                            # still fall (2026-10-23: Raptors read 45 while on pace for 33)
                            frac = _game_fraction(cur, g["game_id"])
                            ex = {k: (v if k == "shot_clock_forced" or v is None else round(v / frac)) for k, v in (extra or {}).items()}
                            end_line = scoring_mod.team_line(round(mine / frac), round(theirs / frac), ex)
                            end_score = scoring_mod.score_game(rules["team"], end_line)
                            team_end = end_score["total"]
                            pts, team_bd[g["game_id"]] = team_end, end_score["breakdown"]
                            team_lines[g["game_id"]] = {"now": scoring_mod.team_line(mine, theirs, extra), "end": end_line, "counts": True}
            missing = bool(not played and hurt and hurt["status"] in OUT
                           and (hurt["return_date"] is None or g["game_date"] < hurt["return_date"])) or (
                not played and sits and g["status"] == "live")
            can_play += not played and not (hurt_now and hurt_now["status"] in OUT
                                            and (hurt_now["return_date"] is None or g["game_date"] < hurt_now["return_date"]))
            # this game's fantasy points by category (Matchup's Schedule view: hovering a day's game, 2026-10-23)
            if e["kind"] == "player":
                r_g = box_rows.get((e["id"], g["game_id"])) if pts is not None else None
                bd_g = score_breakdown(r_g, rules) if r_g else {}
                glabel = label
            else:
                bd_g, glabel = team_bd.get(g["game_id"]) or {}, tlabel
            gl.append({"game_id": g["game_id"], "date": g["game_date"].isoformat(), "opp": opp, "home": home, "played": played,
                       "out": missing,
                       "tipoff": g["tipoff_utc"].isoformat() if g.get("tipoff_utc") else None,
                       "points": round(pts, 1) if pts is not None else None,
                       "live": live_now,
                       "pace": round(pace, 1) if pace is not None else None,
                       "parts": [{"label": glabel.get(k, k), "points": v} for k, v in bd_g.items() if v],
                       **({"proj_end": round(team_end, 1)} if team_end is not None else {}),
                       # minutes played (players): shown next to the game's date — a low score in few minutes reads
                       # differently from a bad full game
                       "min": round(box_rows[(e["id"], g["game_id"])]["minutes"])
                              if e["kind"] == "player" and (e["id"], g["game_id"]) in box_rows else None})
        vals = [x["points"] for x in gl if x["points"] is not None]
        side = rules["team" if e["kind"] == "nba_team" else "player"]
        # a healthy game this week (2026-10-26): finished, or live, with 40%+ of his usual minutes; NBA teams: any game
        usual = usual_minutes(cur, e["id"], season) if e["kind"] == "player" else None
        healthy_played = bool(vals) if e["kind"] != "player" else any(
            x["points"] is not None and x["min"] is not None and (x["played"] or x.get("live"))
            and not is_short(box_rows[(e["id"], x["game_id"])]["minutes"], usual) for x in gl)
        week_score = scoring_mod.week_score(side, vals)
        remaining = sum(1 for x in gl if not x["played"] and not x["out"])  # games he's expected to play
        hist = scores.get(e["id"], [])
        pvar = 0.0
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
            if curve and curve.get("e") and game_proj is not None:
                # the week from each game's own number (commissioner, 2026-10-18): game_proj × that game's factor,
                # the model's game-to-game spread (from its curve: best of 2 − best of 1 = 0.564 SD), blended into his
                # own spread by games played like the level; his chance of playing each game; never below his best
                cv = projections.game_cv(curve, season_scores.get(e["id"]) or [])
                # availability: _healthy — each game's chance of a healthy one (a game cut short barely scores)
                _, qs = _healthy(cur, e, season, today, left, pre_avail.get(e["id"]), hurt_now,
                                 sum(1 for x in gl if x["out"] and not x["played"]))
                proj, pvar = projections.week_dist(game_proj, cv, ahead, {"zero": 0.0, "q": 1.0}, floor, qs) if left else (floor, 0.0)
            else:  # no model (test leagues): his own game scores
                proj = expected_best(hist, left, floor) if left else floor
                pvar = _hist_var(hist, left, _chances(cur, e, season, today, left, None)[1], floor)
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
                if lg_t:  # 4th quarter: tonight's projected end stands in for that game; later games still lift it.
                    # The floor is the best FINISHED game and tonight's projected end — not tonight's score as it stands,
                    # which can still fall (2026-10-23: Magic at 37 now, on pace for 20, projected 37.4)
                    prior = [x["points"] for x in gl if x is not lg_t and x["points"] is not None]
                    floor = max(prior + [lg_t["proj_end"]])
                    proj = expected_best(hist, remaining - 1, floor) if remaining > 1 else floor
                    pvar = _hist_var(hist, remaining - 1, None, floor)
                else:
                    proj = expected_best(hist, remaining, week_score) if remaining else week_score
                    pvar = _hist_var(hist, remaining, None, week_score)
            else:  # summed: what's in + the average for each game left
                proj = (week_score or 0.0) + avg * remaining if (remaining or week_score is not None) else None
                pvar = remaining * (sum((x - avg) ** 2 for x in hist) / len(hist)) if hist else 0.0
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
        if proj is None and week_score is None and any(x["out"] for x in gl) and all(x["out"] or x["played"] for x in gl):
            proj = 0.0  # out for every game he has left this week (injury report): projected 0, not blank
        out.append({**{k: v for k, v in e.items() if k not in ("row_id", "added_asof", "added_at")}, "games": [{k: v for k, v in x.items() if k != "game_id"} for x in gl],
                    "week_score": week_score, "box_line": box_line, "contrib": contrib, "breakdown": breakdown,
                    # white dots = games he actually played; a game he missed (out, DNP) isn't one (2026-10-25)
                    "games_done": sum(1 for x in gl if x["played"] and (e["kind"] != "player" or x["points"] is not None)),
                    # the dots: white = finished, orange = live right now, outline = not started (games_left − live)
                    "games_today": sum(1 for x in gl if x.get("live")),
                    "projected": round(proj, 1) if proj is not None else None, "games_left": remaining,
                    "games_out": sum(1 for x in gl if x["out"]),
                    "injury": ({"status": hurt["status"], "short": hurt["short"], "injury": hurt["injury"],
                                "return_date": hurt["return_date"].isoformat() if hurt["return_date"] else None,
                                "reported_at": hurt["reported_at"].isoformat() if hurt["reported_at"] else None} if hurt else None),
                    "season_ppg": season_pts.get(e["id"]),
                    "live": _live_info(cur, e, gl, box_rows, rules, label, team_bd, tlabel, team_lines),
                    # Roster's "1+ Game %": chance he plays at least once this week (already played → 1)
                    "play_prob": _play_prob(cur, e, season, today, bool(gl), can_play, healthy_played, pre_avail.get(e["id"]),
                                            hurt_now if e["kind"] == "player" else None,
                                            sum(1 for x in gl if x["out"] and not x["played"])),
                    # One game's projection (shown under each future game): the average game in the projection input.
                    "game_proj": round(game_proj, 1) if game_proj is not None else None,
                    "locked": is_current and _locked(e, games, today, replay),
                    # how much his week can still swing (variance of `projected`): the win chance (winprob.py)
                    "proj_var": round(pvar, 2)})
    starters = sum(x["week_score"] or 0 for x in out if x["slot"] not in ("BENCH", "IR"))
    starters_proj = sum(x["projected"] or 0 for x in out if x["slot"] not in ("BENCH", "IR"))
    # When this team's lineup starts locking this week: 5 min before its earliest first game.
    firsts = [gs[0] for t, gs in games.items() if gs and t in {e["nba_team"] for e in roster}]
    first = min(firsts, key=lambda g: (g["game_date"], g["tipoff_utc"] or datetime.max.replace(tzinfo=timezone.utc)), default=None)
    lock = None
    if first:
        lock = {"date": first["game_date"].isoformat(),
                "at": (first["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES)).isoformat() if first["tipoff_utc"] and not replay else None}
    week_lock = first_lock(cur, season, week, replay)
    # Once this week has started locking, the clock counts to the next week's first lock.
    next_lock = first_lock(cur, season, next((w for w in weeks if w["week"] == week["week"] + 1), None), replay)
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
