"""Waivers.

- A drop is real once the player was really on the team: drafted, or locked into one of its weekly lineups
  (etched, etch.py). A real drop puts him on waivers for 2 days — nobody can just add him, not even the team that
  dropped him; teams put in claims instead. An add that's dropped again before any lock isn't a real drop: he goes
  straight back to free agents (both moves stay in the log).
- Claims: one per team per player, with an optional player to drop if it wins. When the 2 days are up, the claim
  from the team first in the claim order (_priority) that still fits its roster wins; the rest lose. No claims → he's
  a free agent. The order resets to reverse standings at each scoring period's first lock — the standings as they
  were then (only matchups from earlier periods count; a matchup that finishes mid-period never reshuffles it), in
  the Standings page's order (win %, then points for, then name) turned around; a winning team goes to the back of
  the line for the rest of the period. A period = one matchup unit: a 2-week playoff round is one period.
- Clock: the live league counts 48 hours from the drop; the replay counts 2 days on its own (simulated) date.
- Processing is lazy: process() runs before anything that reads or changes rosters (players list, checkout, claims,
  transaction log), the same way the draft catches up on reads.
"""
from datetime import datetime, timedelta, timezone

from .engine import as_of, kept_results, league

REPLAY = "replay"
WAIVER_DAYS = 2


def _open_sql(scenario: str) -> str:
    return "until_asof > %s" if scenario == REPLAY else "until_at > %s"


def _clock(lg, scenario):
    return as_of(lg) if scenario == REPLAY else datetime.now(timezone.utc)


def was_real(cur, scenario: str, team_id: str, row: dict, weeks: list) -> bool:
    """Was this a real drop: drafted, or locked into ANY team's weekly lineup in a week that ended on or after he joined
    this team (2026-10-27: Harper traded from nola, locked on nola's week 2 roster, then dropped in week 2 → waivers,
    even though he never locked for the team dropping him). Locks from weeks that ended before he joined don't count."""
    if row.get("added_asof") is None:
        return True
    since = [w["week"] for w in weeks if w["end"] >= row["added_asof"]]
    cur.execute("SELECT 1 FROM fantasy_lock_ledger WHERE scenario = %s AND entity_id = %s AND week = ANY(%s) LIMIT 1",
                (scenario, row["id"], since))
    return cur.fetchone() is not None


def put_on_waivers(cur, scenario: str, entity_id: str, team_id: str, today) -> None:
    now = datetime.now(timezone.utc)
    cur.execute("UPDATE fantasy_waivers SET status = 'cleared' WHERE scenario = %s AND entity_id = %s AND status = 'open'", (scenario, entity_id))
    cur.execute("""INSERT INTO fantasy_waivers (scenario, entity_id, from_team, dropped_at, until_at, until_asof)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (scenario, entity_id, team_id, now, now + timedelta(days=WAIVER_DAYS), today + timedelta(days=WAIVER_DAYS)))


def on_waivers(cur, scenario: str) -> dict:
    """entity id → {waiver_id, until (ISO, live) / until_date (replay), from_team} for players on waivers now."""
    lg = league(cur, scenario)
    cur.execute(f"SELECT id, entity_id, from_team, until_at, until_asof FROM fantasy_waivers WHERE scenario = %s AND status = 'open' AND {_open_sql(scenario)}",
                (scenario, _clock(lg, scenario)))
    return {r["entity_id"]: {"waiver_id": r["id"], "from_team": r["from_team"],
                             "until": r["until_at"].isoformat() if scenario != REPLAY else None,
                             "until_date": r["until_asof"].isoformat()} for r in cur.fetchall()}


def week_locks(cur, lg: dict, weeks: list, replay: bool) -> dict:
    """week number → lineup.first_lock(week) for every week, in one query (the same first game: earliest date, then
    tip time, TBD tips last)."""
    if not weeks:
        return {}
    cur.execute("""
        SELECT DISTINCT ON (w.i) w.i, g.game_date, g.tipoff_utc
        FROM unnest(%s::date[], %s::date[]) WITH ORDINALITY AS w(s, e, i)
        JOIN nba_games g ON g.season = %s AND g.game_type = 'regular' AND g.game_date BETWEEN w.s AND w.e
        ORDER BY w.i, g.game_date, g.tipoff_utc NULLS LAST
    """, ([w["start"] for w in weeks], [w["end"] for w in weeks], lg["season"]))
    from .weeks import LOCK_MINUTES
    out = {}
    for r in cur.fetchall():
        w = weeks[r["i"] - 1]
        out[w["week"]] = {"week": w["week"], "date": r["game_date"].isoformat(),
                          "at": (r["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES)).isoformat() if r["tipoff_utc"] and not replay else None}
    return out


def period(cur, scenario: str, at) -> tuple:
    """(start, week) of the scoring period holding `at`: start = the latest period's first lock (5 min before its first
    game, whatever day that is) at or before `at` (replay: the first game's date), week = that period's first week.
    (None, None) = before the first week's lock. A 2-week playoff round is one period: only its first leg starts one;
    a week whose tip time is still TBD hasn't started."""
    from .engine import weeks_for_league
    lg = league(cur, scenario)
    weeks = weeks_for_league(cur, lg)
    locks = week_locks(cur, lg, weeks, scenario == REPLAY)
    best = (None, None)
    for w in weeks:
        if (w.get("leg") or 1) > 1:  # a 2-week playoff round is one period: only its first leg resets
            continue
        fl = locks.get(w["week"])
        if not fl:
            continue
        if scenario == REPLAY:
            t = datetime.fromisoformat(fl["date"]).date()
        elif fl.get("at"):
            t = datetime.fromisoformat(fl["at"])
        else:  # tip time still TBD: a future week
            continue
        if t <= at:
            best = (t, w["week"])
    return best


def period_start(cur, scenario: str, at) -> "datetime | date | None":
    """When the scoring period holding `at` began (period()); None = before the first week's lock."""
    return period(cur, scenario, at)[0]


def base_standings(res: dict, week) -> list:
    """The standings at a period's first lock: regular-season matchups from weeks before `week` that are final (all
    of them, by then), in the Standings page's order (standings.js: win %, ties = half, then points for, then name).
    week None (before the first lock) = nobody has played: everyone 0-0."""
    rec = {}
    for wk in res["weeks"]:
        for m in wk["matchups"]:
            for me, op in ((m["home"], m["away"]), (m["away"], m["home"])):
                r = rec.setdefault(me["team"]["id"], {"team": me["team"], "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0})
                if week is None or wk["week"] >= week or wk["kind"] != "regular" or not m["final"]:
                    continue
                r["pf"] += me["score"]; r["pa"] += op["score"]
                r["w" if me["score"] > op["score"] else "l" if me["score"] < op["score"] else "t"] += 1
    for r in res["standings"]:  # teams with no matchup yet (e.g. a bye)
        rec.setdefault(r["team"]["id"], {"team": r["team"], "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0})
    pct = lambda r: (r["w"] + r["t"] / 2) / (r["w"] + r["l"] + r["t"]) if r["w"] + r["l"] + r["t"] else 0
    table = sorted(rec.values(), key=lambda r: (-pct(r), -r["pf"], r["team"]["name"].lower()))
    for r in table:
        r["pf"], r["pa"] = round(r["pf"], 1), round(r["pa"], 1)
    return table


def _priority(cur, scenario: str, at=None, res: dict | None = None, per: tuple | None = None) -> list:
    """Team ids, first claim first (commissioner, 2026-10-27). Each scoring period starts from reverse standings as they
    were at its first lock (base_standings — the Standings page's order turned around: worst win %, then fewest points
    for); within the period, a team that wins a claim goes to the back of the line (several winners: in the order they
    won). `at` = the moment the order is for (default now); `res` = results already in hand, `per` = period(at)."""
    lg = league(cur, scenario)
    at = at or _clock(lg, scenario)
    start, week = per if per is not None else period(cur, scenario, at)
    table = base_standings(res if res is not None else kept_results(cur, scenario), week)
    out = [r["team"]["id"] for r in reversed(table)]
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    out += [r["id"] for r in cur.fetchall() if r["id"] not in out]
    if start is not None:
        col = "until_asof" if scenario == REPLAY else "until_at"
        cur.execute(f"""SELECT claimed_by FROM fantasy_waivers WHERE scenario = %s AND status = 'claimed' AND claimed_by IS NOT NULL
                        AND {col} >= %s AND {col} <= %s ORDER BY {col}, id""", (scenario, start, at))
        for r in cur.fetchall():  # each win sends that team to the back
            if r["claimed_by"] in out:
                out.remove(r["claimed_by"])
                out.append(r["claimed_by"])
    return out


def process(cur, scenario: str) -> int:
    """Settle every waiver whose 2 days are up. Returns how many were settled."""
    from . import transactions
    lg = league(cur, scenario)
    done = "until_asof <= %s" if scenario == REPLAY else "until_at <= %s"
    cur.execute(f"SELECT * FROM fantasy_waivers WHERE scenario = %s AND status = 'open' AND {done} ORDER BY until_at FOR UPDATE",
                (scenario, _clock(lg, scenario)))
    due = cur.fetchall()
    if not due:
        return 0
    res = None  # the results, once: each period's base order only counts earlier periods (moves here can't change it)
    for w in due:
        cur.execute("SELECT * FROM fantasy_claims WHERE waiver_id = %s AND status = 'pending'", (w["id"],))
        claims = cur.fetchall()
        winner = None
        if claims:
            # the order when his waiver ended (its period, earlier wins in it already counted)
            res = res if res is not None else kept_results(cur, scenario)
            order = _priority(cur, scenario, w["until_asof"] if scenario == REPLAY else w["until_at"], res=res)
            rank = {t: i for i, t in enumerate(order)}
            for c in sorted(claims, key=lambda c: (rank.get(c["team_id"], 99), c["created_at"])):
                try:
                    cur.execute("SAVEPOINT claim")
                    transactions.checkout(cur, scenario, {"is_admin": True}, c["team_id"], [w["entity_id"]],
                                          [c["drop_id"]] if c["drop_id"] else [], apply=True, via="waivers")
                    cur.execute("RELEASE SAVEPOINT claim")
                    winner = c
                    break
                except ValueError as e:  # doesn't fit any more (roster changed): next claim
                    cur.execute("ROLLBACK TO SAVEPOINT claim")
                    cur.execute("UPDATE fantasy_claims SET status = 'failed', note = %s WHERE id = %s", (str(e)[:200], c["id"]))
            for c in claims:
                if winner and c["id"] == winner["id"]:
                    cur.execute("UPDATE fantasy_claims SET status = 'won' WHERE id = %s", (c["id"],))
                else:
                    cur.execute("UPDATE fantasy_claims SET status = 'lost' WHERE id = %s AND status = 'pending'", (c["id"],))
        cur.execute("UPDATE fantasy_waivers SET status = %s, claimed_by = %s WHERE id = %s",
                    ("claimed" if winner else "cleared", winner["team_id"] if winner else None, w["id"]))
    return len(due)


def _team(cur, scenario, team_id, user):
    cur.execute("SELECT id, owner_user_id FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    t = cur.fetchone()
    if not t:
        raise ValueError("no such team")
    if t["owner_user_id"] != user.get("discord_id") and not user.get("is_admin"):
        raise PermissionError("not your team")


def claim(cur, scenario: str, user: dict, team_id: str, entity_id: str, drop_id: str | None) -> dict:
    """Put in (or replace) this team's claim on a player on waivers, with an optional drop if it wins.
    Checked now against the roster (the same check runs again when it's settled)."""
    from . import transactions
    _team(cur, scenario, team_id, user)
    if not transactions._draft_done(cur, scenario):
        raise ValueError("adds and drops open once the draft is done")
    process(cur, scenario)
    w = on_waivers(cur, scenario).get(entity_id)
    if not w:
        raise ValueError("he isn't on waivers — add him as a free agent")
    preview = transactions.checkout(cur, scenario, user, team_id, [entity_id], [drop_id] if drop_id else [], apply=False, via="waivers")
    if not preview["ok"]:
        raise ValueError(preview["error"])
    cur.execute("DELETE FROM fantasy_claims WHERE waiver_id = %s AND team_id = %s AND status = 'pending'", (w["waiver_id"], team_id))
    cur.execute("""INSERT INTO fantasy_claims (scenario, waiver_id, team_id, entity_id, drop_id, by_user)
                   VALUES (%s, %s, %s, %s, %s, %s)""", (scenario, w["waiver_id"], team_id, entity_id, drop_id, user.get("discord_id")))
    return claims_for(cur, scenario, team_id)


def cancel(cur, scenario: str, user: dict, team_id: str, claim_id: int) -> dict:
    _team(cur, scenario, team_id, user)
    cur.execute("DELETE FROM fantasy_claims WHERE scenario = %s AND team_id = %s AND id = %s AND status = 'pending'", (scenario, team_id, claim_id))
    return claims_for(cur, scenario, team_id)


def prune(cur, scenario: str, team_id: str, skip: tuple = ()) -> None:
    """Cancel this team's pending claims that no longer work (2026-10-26): its drop player is gone from the roster,
    or the roster can't fit him any more. Runs after every roster move and before claims are shown.
    `skip` = players just won on waivers (their claims are being settled, not cancelled)."""
    from . import transactions
    cur.execute("SELECT id, entity_id, drop_id FROM fantasy_claims WHERE scenario = %s AND team_id = %s AND status = 'pending'",
                (scenario, team_id))
    for c in cur.fetchall():
        if c["entity_id"] in skip:
            continue
        try:
            ok = transactions.checkout(cur, scenario, {"is_admin": True}, team_id, [c["entity_id"]],
                                       [c["drop_id"]] if c["drop_id"] else [], apply=False, via="waivers")["ok"]
        except ValueError:
            ok = False
        if not ok:
            cur.execute("DELETE FROM fantasy_claims WHERE id = %s", (c["id"],))


def claims_for(cur, scenario: str, team_id: str) -> dict:
    """This team's pending claims (private) and its place in the claim order."""
    prune(cur, scenario, team_id)
    cur.execute("""
        SELECT c.id, c.entity_id, c.drop_id, c.created_at, w.until_at, w.until_asof,
               COALESCE(p.name, n.name) AS name, COALESCE(dp.name, dn.name) AS drop_name
        FROM fantasy_claims c JOIN fantasy_waivers w ON w.id = c.waiver_id
        LEFT JOIN fantasy_players p ON p.id = c.entity_id LEFT JOIN fantasy_nba_teams n ON n.id = c.entity_id
        LEFT JOIN fantasy_players dp ON dp.id = c.drop_id LEFT JOIN fantasy_nba_teams dn ON dn.id = c.drop_id
        WHERE c.scenario = %s AND c.team_id = %s AND c.status = 'pending' ORDER BY w.until_at
    """, (scenario, team_id))
    rows = [{"id": r["id"], "entity_id": r["entity_id"], "name": r["name"], "drop_id": r["drop_id"], "drop_name": r["drop_name"],
             "until": r["until_at"].isoformat() if scenario != REPLAY else None, "until_date": r["until_asof"].isoformat()}
            for r in cur.fetchall()]
    order = _priority(cur, scenario)
    return {"claims": rows, "priority": order.index(team_id) + 1 if team_id in order else None, "teams": len(order)}
