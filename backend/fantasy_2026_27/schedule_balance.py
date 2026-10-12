"""Balanced matchup schedule (commissioner, 2026-10-12): every team should face about the same strength of schedule.

- Strength = the manager's average win % over the last 3 fantasy seasons (2026 / 2025 / 2024, standings in ROADMAP.md);
  a season he wasn't in counts as .400. New managers = .400.
- Candidates: the round robin (circle method; an odd team count gives one bye a week) with the teams shuffled and the
  rounds of each cycle in a random order, laid over the regular-season weeks. Kept: byes as even as possible, the extra
  byes on the strongest teams (a bye doesn't change expected win %, but fewer games = more luck and less total points
  for, so it handicaps the strong), then the smallest spread in each team's average opponent strength.
- Written as the commissioner's week-by-week matchups (engine.set_matchups), so League Settings → Matchups shows and
  can still edit them. Runs when the draft completes (all teams known) and from League Settings (admin).
"""
import random
import statistics

from . import engine

# owner Discord id → 3-season strength (missing seasons = .400)
STRENGTH_BY_OWNER = {
    "97705344175702016": 0.732,   # elbert
    "91556991276699648": 0.657,   # wonton
    "149247446759768064": 0.591,  # deco
    "148225059696148480": 0.539,  # mits
    "186984468991574016": 0.497,  # notre
    "93280783308951552": 0.454,   # awesomeus prime
    "183328043488509953": 0.446,  # chika
    "186970106557890560": 0.369,  # silversephiroth (darius)
    "227923441469227009": 0.400,  # driller22001 — new
}
# by name, for managers not in the league yet (matched on owner / team name when they join)
STRENGTH_BY_NAME = {"nana": 0.559, "hannaioop": 0.559, "reptar": 0.477, "king midas": 0.454, "kingmidasw": 0.454,
                    "gashee": 0.446, "cody": 0.444, "kitten": 0.421, "lunar": 0.358, "zuotiandenixi": 0.358,
                    "nacho": 0.350, "nachodemacho": 0.350, "weinis": 0.172, "weinis_": 0.172}
DEFAULT = 0.400


def strength(team: dict) -> float:
    if team.get("owner_user_id") in STRENGTH_BY_OWNER:
        return STRENGTH_BY_OWNER[team["owner_user_id"]]
    for key in ((team.get("owner_name") or "").lower(), (team.get("name") or "").lower()):
        for name, v in STRENGTH_BY_NAME.items():
            if name and name in key:
                return v
    return DEFAULT


def _rounds(ids: list) -> list[list[tuple]]:
    ids = list(ids) + ([None] if len(ids) % 2 else [])
    n, out = len(ids), []
    for r in range(n - 1):
        rot = [ids[0]] + ids[1:][r:] + ids[1:][:r]
        out.append([(rot[i], rot[n - 1 - i]) for i in range(n // 2)])
    return out


def build(teams: list[dict], n_weeks: int, tries: int = 20000, seed: int = 2026) -> tuple[list[list[tuple]], dict]:
    """Best of `tries` candidate schedules: (weeks of pairs with None = bye, report)."""
    rng = random.Random(seed)
    s = {t["id"]: strength(t) for t in teams}
    ids = [t["id"] for t in teams]
    best, best_key = None, None
    for _ in range(tries):
        order = ids[:]
        rng.shuffle(order)
        rounds = _rounds(order)
        weeks = []
        while len(weeks) < n_weeks:
            cyc = rounds[:]
            rng.shuffle(cyc)
            weeks += cyc
        weeks = weeks[:n_weeks]
        opp, byes = {i: [] for i in ids}, {i: 0 for i in ids}
        for wk in weeks:
            for a, b in wk:
                if a is None or b is None:
                    byes[a or b] += 1
                else:
                    opp[a].append(s[b])
                    opp[b].append(s[a])
        means = [statistics.mean(v) for v in opp.values() if v]
        # extra byes go to the strongest teams (fewer games = more luck in their record and less total points for — a
        # handicap): count pairs where a weaker team has more byes than a stronger one
        strong_first = sorted(ids, key=lambda i: -s[i])
        misplaced = sum(1 for a in range(len(ids)) for b in range(a + 1, len(ids)) if byes[strong_first[b]] > byes[strong_first[a]])
        key = (max(byes.values()) - min(byes.values()), misplaced, round(max(means) - min(means), 4))
        if best_key is None or key < best_key:
            best, best_key = (weeks, opp, byes), key
    weeks, opp, byes = best
    report = {i: {"strength": s[i], "opp_avg": round(statistics.mean(opp[i]), 3) if opp[i] else None, "games": len(opp[i]), "byes": byes[i]}
              for i in ids}
    return weeks, {"spread": best_key[2], "teams": report}


def apply(cur, scenario: str) -> dict:
    """Balance and save the regular-season schedule for the league's current teams."""
    lg = engine.league(cur, scenario)
    reg = [w for w in engine.weeks_for_league(cur, lg) if w["kind"] == "regular"]
    cur.execute("SELECT t.id, t.name, t.owner_user_id, u.username AS owner_name FROM fantasy_teams t LEFT JOIN users u ON u.discord_id = t.owner_user_id WHERE t.scenario = %s", (scenario,))
    teams = [dict(r) for r in cur.fetchall()]
    if len(teams) < 2 or not reg:
        return {"ok": False, "reason": "need 2+ teams and a regular season"}
    weeks, report = build(teams, len(reg))
    ids = {t["id"] for t in teams}
    for w, pairs in zip(reg, weeks):
        engine.set_matchups(cur, scenario, w["week"], [[a, b] for a, b in pairs if a and b], ids)
    names = {t["id"]: t["name"] for t in teams}
    report["teams"] = {names[k]: v for k, v in report["teams"].items()}
    return {"ok": True, "weeks": len(reg), **report}
