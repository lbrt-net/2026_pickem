"""League engine: a sandbox's clock, and weekly results computed from real box scores.

- Every sandbox is a league row (fantasy_leagues): an NBA season + sim_date. sim_date NULL
  means "today" (the live league). The replay sandbox replays 2025-26 with a date an admin moves.
- Nothing after the league's as-of date is ever read, so a replay can't see the future.
- Weekly scores (FANTASY_SCORING.md): a player's week = his single best game that week;
  an NBA team slot's week = its point margin totaled over the week's games. A fantasy team's
  week = the sum over its roster. Regular-season matchups are a round-robin (same pairing
  rule as the frontend's weekPairings), so both sides agree on who plays whom.
- Rosters: a week's lineup comes from etch.py — entities etched when they locked (they still count after
  being dropped), plus live-roster entities not etched yet who joined before their lock.
- Playoff weeks are listed but their matchups aren't built yet.
"""
import itertools
import threading
from datetime import date, datetime, timedelta, timezone

from psycopg2.extras import Json

from . import etch as etch_mod
from .logic import player_points, team_game_points
from .scoring import league_rules, team_extras, week_score
from .weeks import DEFAULT_SETTINGS, LOCK_MINUTES, apply_auto_playoffs, normalize_settings, season_weeks, week_for

REPLAY = "replay"
# Settings that shape the draft: locked once it has started (save_settings).
DRAFT_LOCKED = ("roster_slots", "team_count", "draft_type", "pick_seconds", "pick_seconds_by_round", "missed_pick",
                "draft_start_at", "auction_budget", "auction_min_bid", "nomination_seconds", "late_nomination_seconds",
                "bid_seconds", "bid_increment_seconds")


def _locks(cur, season: str, weeks: list[dict], today, replay: bool) -> dict:
    from .lineup import first_lock
    cur_w = week_for(weeks, today) or next((w for w in weeks if w["start"] > today), None)
    nxt = next((w for w in weeks if cur_w and w["week"] == cur_w["week"] + 1), None)
    return {"week_lock": first_lock(cur, season, cur_w, replay), "next_lock": first_lock(cur, season, nxt, replay)}


def league(cur, scenario: str) -> dict:
    cur.execute("SELECT * FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"no league for scenario {scenario}")
    return dict(row)


def as_of(lg: dict) -> date:
    """The league's today: its sim date, else today in Central time (a 9 PM game is still today, not UTC's tomorrow)."""
    if lg["sim_date"]:
        return lg["sim_date"]
    from datetime import datetime
    from backend.config import CENTRAL
    return datetime.now(CENTRAL).date()


def settings(lg: dict, cur=None) -> dict:
    """The league's commissioner settings, defaults filled in (with cur: automatic playoffs applied — weeks.py)."""
    s = normalize_settings(lg.get("settings") or {})
    return apply_auto_playoffs(cur, lg["scenario"], s) if cur is not None else s


def weeks_for_league(cur, lg: dict) -> list[dict]:
    return season_weeks(cur, lg["season"], settings(lg, cur))


def save_settings(cur, scenario: str, changes: dict) -> dict:
    """Merge commissioner changes into a league's settings, validate, and check the season still
    fits (e.g. enough weeks for the playoff rounds). Raises ValueError; nothing saved on error."""
    lg = league(cur, scenario)
    # Once the draft has started, the settings that shape it are locked (reset the draft first),
    # so a finished draft never turns into "16 of 28 picks".
    cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    row = cur.fetchone()
    cur.execute("SELECT 1 FROM fantasy_rosters WHERE scenario = %s LIMIT 1", (scenario,))
    drafted = (row and row["status"] != "not_started") or cur.fetchone() is not None
    current = normalize_settings(lg.get("settings") or {})
    touched = [k for k in DRAFT_LOCKED if k in changes and changes[k] != current.get(k)]
    if drafted and touched:
        raise ValueError(f"the draft has started — reset it to change {', '.join(touched)}")
    stored = {**(lg.get("settings") or {}), **changes}
    new = normalize_settings(stored)
    season_weeks(cur, lg["season"], apply_auto_playoffs(cur, scenario, dict(new)))  # raises if the playoffs don't fit this season
    overrides = {k: v for k, v in new.items() if v != DEFAULT_SETTINGS[k]}
    cur.execute("UPDATE fantasy_leagues SET settings = %s, updated_at = now() WHERE scenario = %s",
                (Json(overrides), scenario))
    return new


def _prev_season(season: str) -> str:
    if not season[:4].isdigit():  # the live-test league ("test-live"): last real season for history
        return "2025-26"
    y = int(season[:4]) - 1
    return f"{y}-{str(y + 1)[2:]}"


def pairings(teams: list[dict], week: int) -> list[tuple]:
    """Round-robin by the circle method, teams sorted by name — mirrors data.js weekPairings."""
    ids = sorted(teams, key=lambda t: t["name"].lower())
    if len(ids) % 2:
        ids.append(None)
    n = len(ids)
    if n < 2:
        return []
    rest = ids[1:]
    r = (week - 1) % (n - 1)
    rot = [ids[0]] + [rest[(i + r) % len(rest)] for i in range(len(rest))]
    return [(rot[i], rot[n - 1 - i]) for i in range(n // 2) if rot[i] and rot[n - 1 - i]]


def matchup_overrides(cur, scenario: str) -> dict:
    """The commissioner's hand-set weeks: {week number: [(team_id, team_id), ...]}."""
    cur.execute("SELECT matchups FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    r = cur.fetchone()
    return {int(k): [tuple(p) for p in v] for k, v in ((r and r["matchups"]) or {}).items()}


def week_pairings(teams: list[dict], week: int, overrides: dict) -> list[tuple]:
    """A week's matchups: the commissioner's pairs if he set that week, else the round robin."""
    if week in overrides:
        by_id = {t["id"]: t for t in teams}
        return [(by_id[a], by_id[b]) for a, b in overrides[week] if a in by_id and b in by_id]
    return pairings(teams, week)


def set_matchups(cur, scenario: str, week: int, pairs: list | None, team_ids: set) -> None:
    """Set one week's matchups by hand (pairs of team ids), or put it back on the round robin (pairs=None).
    Each team plays at most once; a team left out has no game that week."""
    cur.execute("SELECT matchups FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    current = dict((cur.fetchone() or {}).get("matchups") or {})
    if pairs is None:
        current.pop(str(week), None)
    else:
        seen = set()
        for pr in pairs:
            if not isinstance(pr, (list, tuple)) or len(pr) != 2 or pr[0] == pr[1]:
                raise ValueError("each matchup is two different teams")
            for t in pr:
                if t not in team_ids:
                    raise ValueError("unknown team")
                if t in seen:
                    raise ValueError("a team can only play once a week")
                seen.add(t)
        current[str(week)] = [list(pr) for pr in pairs]
    cur.execute("UPDATE fantasy_leagues SET matchups = %s, updated_at = now() WHERE scenario = %s", (Json(current) if current else None, scenario))


def set_clock(cur, scenario: str, sim_date: date | None) -> None:
    if scenario != REPLAY:
        raise ValueError("only the replay sandbox has a movable clock")
    lg = league(cur, scenario)
    new_today = sim_date or date.today()
    if new_today < as_of(lg):  # moving back: weeks not over yet as of the new date get re-etched as they lock again
        etch_mod.rewind(cur, scenario, weeks_for_league(cur, lg), new_today)
    cur.execute("UPDATE fantasy_leagues SET sim_date = %s, updated_at = now() WHERE scenario = %s", (sim_date, scenario))


def reset_replay(cur) -> dict:
    """Fresh replay: empty rosters and a not-started draft (draft it in the Draft Room with the
    Replay sandbox selected — rankings use the prior season), clock back to the day before
    the first fantasy week."""
    lg = league(cur, REPLAY)
    weeks = weeks_for_league(cur, lg)
    if not weeks:
        raise ValueError(f"no schedule loaded for {lg['season']}")
    from . import draft  # local import: draft is a sibling module that doesn't import engine
    draft.reset(cur, REPLAY)  # empty rosters, draft not started, saved order kept
    start = weeks[0]["start"] - timedelta(days=1)
    set_clock(cur, REPLAY, start)
    return {"season": lg["season"], "sim_date": start.isoformat(), "draft": "not_started"}


def _team_margins(cur, season: str) -> dict:
    cur.execute("""
        SELECT home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
    """, (season,))
    tot, n = {}, {}
    for g in cur.fetchall():
        for team, m in ((g["home_team"], g["home_score"] - g["away_score"]), (g["away_team"], g["away_score"] - g["home_score"])):
            tot[team] = tot.get(team, 0) + m
            n[team] = n.get(team, 0) + 1
    return {t: tot[t] / n[t] for t in tot}


def home_week(cur, season: str, weeks: list[dict], today: date, replay: bool):
    """The league-wide current week (Home): week N until 5 min before week N+1's first game.
    The replay plays whole days, so a week starts on its first day."""
    if not weeks:
        return None
    started = [w for w in weeks if w["start"] <= today]
    if not started:
        return weeks[0]["week"]
    w = started[-1]
    if replay or w is weeks[0]:
        return w["week"]
    cur.execute("SELECT MIN(tipoff_utc) AS t FROM nba_games WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s",
                (season, w["start"], w["end"]))
    first = cur.fetchone()["t"]
    if first and datetime.now(timezone.utc) < first - timedelta(minutes=LOCK_MINUTES):
        return started[-2]["week"]
    return w["week"]


_KEPT_RESULTS = {}  # scenario -> (fingerprint, results, build number)
_KEPT_MISS: dict = {}  # scenario -> (fingerprint, threading.Event): the rebuild under way
_KEPT_LOCK = threading.Lock()
_KEPT_SEQ = itertools.count()
_GAME_PARTS = 3  # the fingerprint's last parts: games, box scores, league date (what a live pull changes)


def _results_fingerprint(cur, scenario: str, lg: dict) -> tuple:
    """Everything the results depend on, in one cheap query: rosters and spots, moves, locks and pins, teams' looks,
    league settings, the league date, and every game / box score update (live pulls included)."""
    cur.execute("""
        SELECT
          (SELECT md5(coalesce(string_agg(id || ':' || team_id || ':' || slot || ':' || coalesce(player_id, nba_team_id) || ':' || coalesce(ir_until::text, ''), ',' ORDER BY id), ''))
             FROM fantasy_rosters WHERE scenario = %(s)s) AS r,
          (SELECT count(*) || ':' || coalesce(max(id), 0) FROM fantasy_transactions WHERE scenario = %(s)s) AS t,
          (SELECT count(*) FROM fantasy_lock_ledger WHERE scenario = %(s)s) AS l,
          (SELECT md5(coalesce(string_agg(team_id || week || entity_id || slot, ',' ORDER BY team_id, week, entity_id), '')) FROM fantasy_lineups WHERE scenario = %(s)s) AS p,
          (SELECT count(*) FROM fantasy_lineup_weeks WHERE scenario = %(s)s) AS c,
          (SELECT md5(coalesce(string_agg(id || name || coalesce(color, '') || coalesce(abbreviation, '') || coalesce(glyph, '') || coalesce(logo_updated::text, '') || coalesce(picture_url, '') || coalesce(picture_mode, ''), ',' ORDER BY id), ''))
             FROM fantasy_teams WHERE scenario = %(s)s) AS tm,
          (SELECT row_to_json(x)::text FROM fantasy_leagues x WHERE scenario = %(s)s) AS lg,
          (SELECT max(updated_at)::text || ':' || count(*) FROM nba_games WHERE season = %(season)s) AS g,
          (SELECT count(*) FROM nba_player_games WHERE season = %(season)s) AS b
    """, {"s": scenario, "season": lg["season"]})
    return tuple(cur.fetchone().values()) + (as_of(lg).isoformat(),)


def kept_results(cur, scenario: str) -> dict:
    """results(), kept until something it depends on changes (2026-10-25: rebuilt from scratch on every page load,
    2.5–6 s with everyone on). Live games still update it at every pull (their game rows change).
    One rebuild at a time (2026-10-29): while one request rebuilds, a request whose only change is games / box scores
    (a live pull) gets the copy from before that pull (at most one rebuild old); one with the same fingerprint as the
    rebuild waits for it. A change to rosters, moves, locks, lineups, teams or settings is never served stale."""
    lg = league(cur, scenario)
    fp = _results_fingerprint(cur, scenario, lg)
    hit = _KEPT_RESULTS.get(scenario)
    if hit and hit[0] == fp:
        return hit[1]
    with _KEPT_LOCK:
        busy = _KEPT_MISS.get(scenario)
        if not busy:
            ev = threading.Event()
            _KEPT_MISS[scenario] = (fp, ev)
    if busy:
        if hit and hit[0][:-_GAME_PARTS] == fp[:-_GAME_PARTS]:
            return hit[1]
        if busy[0] == fp:
            busy[1].wait()
            got = _KEPT_RESULTS.get(scenario)
            if got and got[0] == fp:
                return got[1]
    try:
        seq = next(_KEPT_SEQ)
        out = results(cur, scenario)
        with _KEPT_LOCK:
            old = _KEPT_RESULTS.get(scenario)
            if not old or old[2] < seq:  # never replace a copy begun after this one
                _KEPT_RESULTS[scenario] = (fp, out, seq)
        return out
    finally:
        if not busy:
            with _KEPT_LOCK:
                _KEPT_MISS.pop(scenario, None)
            ev.set()


def results(cur, scenario: str) -> dict:
    """Every week up to the league's as-of date: matchups with each slot's weekly score, plus standings."""
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    weeks = weeks_for_league(cur, lg)

    cur.execute("""
        SELECT t.id, t.name, t.abbreviation, t.color, t.glyph, t.owner_user_id, u.username AS owner_name,
               t.logo_updated, t.picture_url, t.picture_mode
        FROM fantasy_teams t LEFT JOIN users u ON u.discord_id = t.owner_user_id WHERE t.scenario = %s
    """, (scenario,))
    from .settings import logo_url
    teams = {}
    for t in cur.fetchall():
        t = dict(t)
        t["logo_url"] = logo_url(t)  # uploaded picture / Discord picture; TeamIcon falls back to the glyph
        for k in ("logo_updated", "picture_url", "picture_mode"):
            t.pop(k)
        teams[t["id"]] = t
    # Each begun week's lineup per team: etched entities (even if dropped since) + live ones not etched yet (etch.py).
    lineups = etch_mod.week_lineups(cur, scenario, season, weeks, today)
    every = {e["id"]: e for es in lineups.values() for e in es}
    player_ids = sorted(eid for eid, e in every.items() if e["kind"] == "player")
    team_ids = sorted(eid for eid, e in every.items() if e["kind"] == "nba_team")

    # Every game's fantasy points per entity per week, under the league's rulesets; the weekly score comes from
    # the ruleset's week mode (today: players = best game, NBA teams = sum).
    rules = league_rules(cur, scenario)
    overrides = matchup_overrides(cur, scenario)
    games_wk = {}  # (entity id, week) -> [(points, date)]
    if player_ids:
        cur.execute("""
            SELECT pg.player_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb,
                   pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
            FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
            WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0
              AND g.game_date <= %s AND pg.player_id = ANY(%s::text[])
        """, (season, today, player_ids))
        for r in cur.fetchall():
            w = week_for(weeks, r["game_date"])
            if w:
                games_wk.setdefault((r["player_id"], w["week"]), []).append((player_points(r, rules), r["game_date"].isoformat()))
    if team_ids:
        cur.execute("""
            SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
            WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
              AND game_date <= %s AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        """, (season, today, team_ids, team_ids))
        tgames = cur.fetchall()
        extras = team_extras(cur, [g["game_id"] for g in tgames])
        for g in tgames:
            w = week_for(weeks, g["game_date"])
            if not w:
                continue
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]),
                                    (g["away_team"], g["away_score"], g["home_score"])):
                if t in team_ids:
                    pts = team_game_points(mine > theirs, mine, theirs, rules, extras.get((g["game_id"], t)))
                    games_wk.setdefault((t, w["week"]), []).append((pts, g["game_date"].isoformat()))

    def side(team, week):
        slots = []
        for e in lineups.get((team["id"], week), []):
            e = {k: e[k] for k in ("id", "kind", "name", "slot")}
            gs = games_wk.get((e["id"], week), [])
            score = week_score(rules["player" if e["kind"] == "player" else "team"], [p for p, _ in gs]) or 0.0
            if e["kind"] == "player":
                best = max(gs, key=lambda g: g[0], default=None)
                slots.append({**e, "score": score, "best_game_date": best[1] if best else None})
            else:
                slots.append({**e, "score": score, "games": len(gs)})
        # Bench and IR spots are shown but don't count toward the team's score.
        return {"team": team, "score": round(sum(s["score"] for s in slots if s.get("slot") not in ("BENCH", "IR")), 1), "slots": slots}

    standings = {tid: {"team": t, "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0} for tid, t in teams.items()}
    out_weeks = []
    for w in weeks:
        if w["start"] > today:
            break
        status = "final" if w["end"] < today else "in_progress"
        entry = {"week": w["week"], "label": w["label"], "kind": w["kind"], "start": w["start"].isoformat(),
                 "end": w["end"].isoformat(), "status": status, "matchups": []}
        open_teams = set()  # NBA teams with a game this week still in progress or yet to be played
        if status != "final":
            cur.execute("""SELECT home_team, away_team FROM nba_games WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL
                           AND game_date BETWEEN %s AND %s AND status <> 'final'""", (season, w["start"], w["end"]))
            for g in cur.fetchall():
                open_teams.update((g["home_team"], g["away_team"]))

        def done(team_id):
            """No starter of this team has a game in progress or yet to be played this week (2026-10-25)."""
            for e in lineups.get((team_id, w["week"]), []):
                if e["slot"] not in ("BENCH", "IR") and (e.get("nba_team") or e["id"]) in open_teams:
                    return False
            return True
        if w["kind"] == "regular":
            for a, b in week_pairings(list(teams.values()), w["week"], overrides):
                sa, sb = side(a, w["week"]), side(b, w["week"])
                # a matchup counts in the standings once neither side has a game in progress or to play — not only at
                # the week's end (commissioner, 2026-10-25)
                m_final = status == "final" or (done(a["id"]) and done(b["id"]))
                entry["matchups"].append({"home": sa, "away": sb, "final": m_final})
                if m_final:
                    ra, rb = standings[a["id"]], standings[b["id"]]
                    ra["pf"] += sa["score"]; ra["pa"] += sb["score"]; rb["pf"] += sb["score"]; rb["pa"] += sa["score"]
                    if sa["score"] > sb["score"]:
                        ra["w"] += 1; rb["l"] += 1
                    elif sb["score"] > sa["score"]:
                        rb["w"] += 1; ra["l"] += 1
                    else:
                        ra["t"] += 1; rb["t"] += 1
        out_weeks.append(entry)

    # Same order as the Standings page (standings.js): win % (ties = half), then points for, then name.
    pct = lambda r: (r["w"] + r["t"] / 2) / (r["w"] + r["l"] + r["t"]) if r["w"] + r["l"] + r["t"] else 0
    table = sorted(standings.values(), key=lambda r: (-pct(r), -r["pf"], r["team"]["name"].lower()))
    for r in table:
        r["pf"], r["pa"] = round(r["pf"], 1), round(r["pa"], 1)
    playoffs = _bracket(weeks, today, [r["team"] for r in table], settings(lg, cur)["playoff_teams"], side)
    current = week_for(weeks, today)
    return {
        "scenario": scenario, "season": season, "as_of": today.isoformat(), "sim_date": lg["sim_date"].isoformat() if lg["sim_date"] else None,
        "current_week": current["week"] if current else None,
        # the lock countdown (Players page): the same week_lock / next_lock as Home and Roster (lineup.first_lock)
        **_locks(cur, season, weeks, today, scenario == REPLAY),
        "home_week": home_week(cur, season, weeks, today, scenario == REPLAY),
        "season_start": weeks[0]["start"].isoformat() if weeks else None,
        "season_end": weeks[-1]["end"].isoformat() if weeks else None,
        "weeks": out_weeks, "standings": table, "settings": settings(lg, cur), "playoffs": playoffs,
    }


# Bracket shapes by playoff team count (weeks.auto_playoffs: <4 teams → a final, 4–6 → top 4, 7+ → top 6).
# A game's side is a seed number, or ("W", i) = the winner of the previous round's game i. Seeds 1 and 2 get a bye in
# the 6-team bracket; the higher seed wins a tie.
BRACKETS = {
    2: [[(1, 2)]],
    4: [[(1, 4), (2, 3)], [(("W", 0), ("W", 1))]],
    6: [[(4, 5), (3, 6)], [(1, ("W", 0)), (2, ("W", 1))], [(("W", 0), ("W", 1))]],
}


def _bracket(weeks: list, today, seeds: list, n: int, side) -> dict:
    """The playoff bracket: seeds from the standings (final once the regular season ends), each round's games with
    scores once its week begins, winners once it's over, and the champion."""
    shape = BRACKETS.get(n) or BRACKETS[2]
    # each round's weeks (a 2-week round = 2 legs, scored separately and added up)
    legs = {}
    for w in weeks:
        if w["kind"] == "playoffs":
            legs.setdefault(w.get("round_index", len(legs)), []).append(w)
    rounds_w = [legs[k] for k in sorted(legs)]
    regular = [w for w in weeks if w["kind"] == "regular"]
    done = sum(1 for w in regular if w["end"] < today)
    seeded = seeds[:n]
    winners_prev, losers_prev, rounds, third = [], [], [], None
    for i, games in enumerate(shape):
        lw = rounds_w[i] if i < len(rounds_w) else []
        w = {"week": lw[0]["week"], "start": lw[0]["start"], "end": lw[-1]["end"], "label": lw[0].get("round") or lw[0]["label"]} if lw else None
        status = "upcoming" if not w or w["start"] > today else ("final" if w["end"] < today else "in_progress")
        out, winners, losers = [], [], []
        last = i == len(shape) - 1

        def score(game, a, b):
            begun = [x for x in lw if x["start"] <= today]
            la = [side(a["team"], x["week"])["score"] for x in begun]
            lb = [side(b["team"], x["week"])["score"] for x in begun]
            game["a_score"], game["b_score"] = round(sum(la), 1), round(sum(lb), 1)
            if len(lw) > 1:
                game["legs"] = [{"leg": x.get("leg", j + 1), "a": la[j], "b": lb[j]} for j, x in enumerate(begun)]
            if status == "final":
                first = a if a["seed"] < b["seed"] else b
                game["winner"] = a if game["a_score"] > game["b_score"] else b if game["b_score"] > game["a_score"] else first
        # 3rd place: the semifinal losers, played over the championship's weeks (needs semis: 4+ teams)
        if last and n >= 4 and len(losers_prev) == 2:
            a3, b3 = losers_prev
            third = {"a": a3, "b": b3, "a_score": None, "b_score": None, "winner": None, "from": [0, 1]}
            if a3 and b3 and w and status != "upcoming":
                score(third, a3, b3)
        for g in games:
            pair = []
            for x in g:
                if isinstance(x, tuple):  # ("W", i)
                    pair.append(winners_prev[x[1]] if x[1] < len(winners_prev) else None)
                else:
                    pair.append({"seed": x, "team": seeded[x - 1]} if x - 1 < len(seeded) else None)
            a, b = pair
            game = {"a": a, "b": b, "a_score": None, "b_score": None, "winner": None,
                    "from": [x[1] if isinstance(x, tuple) else None for x in g]}  # which earlier game feeds each side
            if a and b and w and status != "upcoming":
                score(game, a, b)
            winners.append(game["winner"])
            losers.append((b if game["winner"] is a else a) if game["winner"] else None)
            out.append(game)
        rounds.append({"name": w["label"] if w else f"Round {i + 1}", "week": w["week"] if w else None, "legs": len(lw) or 1,
                       "start": w["start"].isoformat() if w else None, "end": w["end"].isoformat() if w else None,
                       "status": status, "games": out, "byes": [seeded[k] for k in (0, 1)] if n == 6 and i == 0 and len(seeded) >= 2 else []})
        winners_prev, losers_prev = winners, losers
    final = rounds[-1]["games"][0] if rounds else None
    return {"teams": n, "seeds": [{"seed": k + 1, "team": t} for k, t in enumerate(seeded)], "rounds": rounds,
            "champion": final["winner"] if final and final["winner"] else None, "third": third,
            "regular_weeks": len(regular), "regular_done": done, "open": done * 2 >= len(regular) and len(regular) > 0,
            "set": done == len(regular)}
