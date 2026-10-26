"""Winnings (commissioner, 2026-10-13): the prize pool, who's in it and who collects.

Finance settings (fantasy_leagues.finance, commissioner only):
  buy_in        — dollars per team (25)
  paid          — owner Discord ids of league members who've paid in
  extras        — [{"name", "amount"}]: money from people not in the league (yet), or extra the commissioner adds
  weekly        — dollars to the top score of each regular-season week (5)
  split         — playoff split in percent, 1st / 2nd / 3rd (60 / 30 / 10)
  round_to      — playoff payouts rounded to this many dollars (5); 1st takes the rounding difference
Pool = buy_in × paid members + extras. Regular season = weekly × regular weeks (never more than the pool); playoffs =
the rest. Only paid members collect: a week's prize goes to the top score among paid teams; playoff prizes go to paid
teams in order of playoff finish (champion, runner-up, 3rd-place winner, 3rd-place loser, then the rest by seed).
`would` = the same payouts if everyone in the league had paid in.
"""
from psycopg2.extras import Json

from .engine import league, results, weeks_for_league

DEFAULTS = {"buy_in": 25, "paid": [], "extras": [], "weekly": 5, "split": [60, 30, 10], "round_to": 5}
# the 2026-27 league's starting state (commissioner, 2026-10-13): elbert paid; Cody and geimstopp paid, not joined yet
SEED = {"live": {"paid": ["97705344175702016"], "extras": [{"name": "Cody", "amount": 25}, {"name": "geimstopp", "amount": 25}]}}


def settings(cur, scenario: str) -> dict:
    cur.execute("SELECT finance FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    r = cur.fetchone()
    stored = (r and r["finance"]) or SEED.get(scenario, {})
    return {**DEFAULTS, **stored}


def save(cur, scenario: str, changes: dict) -> dict:
    s = settings(cur, scenario)
    for k, v in changes.items():
        if k not in DEFAULTS:
            raise ValueError(f"unknown setting: {k}")
        s[k] = v
    if not isinstance(s["buy_in"], (int, float)) or s["buy_in"] < 0:
        raise ValueError("buy_in must be a number")
    if not isinstance(s["paid"], list) or not isinstance(s["extras"], list):
        raise ValueError("paid and extras must be lists")
    for x in s["extras"]:
        if not isinstance(x, dict) or not str(x.get("name", "")).strip() or not isinstance(x.get("amount"), (int, float)):
            raise ValueError("each extra needs a name and an amount")
    if not isinstance(s["split"], list) or not all(isinstance(p, (int, float)) and p >= 0 for p in s["split"]):
        raise ValueError("split must be a list of percents")
    cur.execute("UPDATE fantasy_leagues SET finance = %s WHERE scenario = %s", (Json(s), scenario))
    return s


def _split(amount: float, pcts: list, round_to: float) -> list[float]:
    total = sum(pcts) or 1
    out = [round(amount * p / total / round_to) * round_to if round_to else round(amount * p / total, 2) for p in pcts]
    if out:
        out[0] += round(amount - sum(out), 2)  # 1st takes the rounding difference
    return out


def _finish_order(po: dict) -> list:
    """Team ids in order of playoff finish; [] until the playoffs are decided."""
    if not po or not po.get("champion") or not po.get("rounds"):
        return []
    tid = lambda x: (x or {}).get("team", x or {}).get("id") if isinstance(x, dict) else None
    champ = tid(po["champion"])
    final = po["rounds"][-1]["games"][0]
    runner = next((tid(s) for s in (final.get("a"), final.get("b")) if tid(s) and tid(s) != champ), None)
    order = [champ, runner]
    third = po.get("third") or {}
    if third.get("winner"):
        w = tid(third["winner"])
        order += [w, next((tid(s) for s in (third.get("a"), third.get("b")) if tid(s) and tid(s) != w), None)]
    for sd in po.get("seeds") or []:
        if tid(sd) not in order:
            order.append(tid(sd))
    return [t for t in order if t]


def winnings(cur, scenario: str) -> dict:
    s = settings(cur, scenario)
    lg = league(cur, scenario)
    res = results(cur, scenario)
    cur.execute("SELECT id, name, owner_user_id, color FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    teams = [dict(r) for r in cur.fetchall()]
    paid_ids = {t["id"] for t in teams if t["owner_user_id"] in set(s["paid"])}
    extras = [{"name": x["name"], "amount": x["amount"]} for x in s["extras"]]
    reg_weeks = [w for w in weeks_for_league(cur, lg) if w["kind"] == "regular"]

    def plan(eligible: set) -> dict:
        pool = s["buy_in"] * len(eligible) + sum(x["amount"] for x in extras)
        regular = min(s["weekly"] * len(reg_weeks), pool)
        playoff = round(pool - regular, 2)
        by_week = {w["week"]: w for w in res.get("weeks", [])}
        rows = []
        for w in reg_weeks:
            rw = by_week.get(w["week"])
            winner = None
            if rw:  # a live stat (2026-10-25): the week's top paid score as it stands — and later stat corrections move it
                sides = [sd for m in rw["matchups"] for sd in (m["home"], m["away"]) if sd["team"]["id"] in eligible]
                if sides:
                    top = max(sides, key=lambda sd: sd["score"])
                    winner = {"team": top["team"]["id"], "score": top["score"]}
            rows.append({"kind": "week", "label": w["label"], "week": w["week"], "start": w["start"].isoformat(),
                         "end": w["end"].isoformat(), "amount": s["weekly"] if s["weekly"] * len(reg_weeks) <= pool else round(regular / len(reg_weeks), 2),
                         "status": (rw or {}).get("status", "upcoming"), "winner": winner})
        order = [t for t in _finish_order(res.get("playoffs") or {}) if t in eligible]
        places = ["1st", "2nd", "3rd", "4th", "5th"]
        for i, amt in enumerate(_split(playoff, s["split"], s["round_to"])):
            rows.append({"kind": "playoff", "label": f"Playoffs · {places[i] if i < len(places) else f'{i + 1}th'}", "amount": amt,
                         "status": "final" if order else "upcoming", "winner": {"team": order[i]} if i < len(order) else None})
        totals = {}
        for r in rows:
            if r["winner"]:
                totals[r["winner"]["team"]] = totals.get(r["winner"]["team"], 0) + r["amount"]
        return {"pool": pool, "regular": regular, "playoff": playoff, "rows": rows, "totals": totals}

    return {"settings": s, "teams": [{**t, "paid": t["id"] in paid_ids} for t in teams], "extras": extras,
            "regular_weeks": len(reg_weeks), "actual": plan(paid_ids), "would": plan({t["id"] for t in teams})}
