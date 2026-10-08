"""Rec bid: what an entity is worth to one team in an auction right now (BIDDING_GUIDE.md), re-read on every state.

1. Weekly value: PROJ MAX (the draft ranking) — players × AVAIL, the share of weeks a player actually plays; NBA teams
   play every week.
2. Replacement level per slot type, from the room as it stands: fill every team's open starting spots league-wide with
   the undrafted entities best-first (own slot, else FLEX); a slot's replacement = the best one left who fits it.
3. Going rate ($ per point a week) = all teams' money above the minimum bids for their open spots ÷ the points over
   replacement of that fill — so the room's inflation is in it: cheap stars early → more money chasing the rest.
4. For the viewer's team: the slot he'd fill (logic.open_slot — the draft's own rule); fair = min bid + rate × points
   over that slot's replacement; × money adjustment = (your $ − min × your open spots) ÷ (open spots × the average $ above
   the minimum per spot at the start); never above the safe max (your $ − min × your other open spots).
   A pick that only fits the bench is worth the minimum; one that fits no open spot gets no bid.
5. Never more than MAX_SHARE of the starting budget on one player ($140 of $200, commissioner 2026-10-08). A mock
   2025-26 auction backs it: a team that never bid over $100 against 11 teams bidding the uncapped formula won 50.5% of
   its weekly matchups (2 teams head to head: 10–10) — the top-end premium buys nothing.
"""
from .logic import SLOT_POSITIONS, open_slot

AVAIL = 0.86
MAX_SHARE = 0.70
STARTING = ("G", "F", "C", "TEAM", "FLEX")


def _own(e) -> str | None:
    if e["kind"] == "nba_team":
        return "TEAM"
    return next((s for s, ps in SLOT_POSITIONS.items() if e.get("position") in ps), None)


def _fits(e, slot: str) -> bool:
    return slot in ("FLEX", "BENCH") or _own(e) == slot


def rec_bids(pool: list, picks: list, settings: dict, budgets: dict, team_id: str) -> dict:
    """{entity id: recommended bid in dollars} for `team_id`; entities that fit none of its open spots are left out.
    pool = logic.draft_pool ranked by rank_points (e["pts"] = PROJ MAX); budgets = draft._budgets."""
    slots, mn = settings["roster_slots"], settings["auction_min_bid"]
    taken = {p["player_id"] or p["nba_team_id"] for p in picks}
    left = [{**e, "val": e["pts"] * (AVAIL if e["kind"] == "player" else 1.0)}
            for e in pool if e["id"] not in taken and e["pts"] not in (None, float("-inf"))]
    left.sort(key=lambda e: -e["val"])

    # 2. league-wide fill of the open starting spots
    open_ = {s: 0 for s in STARTING}
    for tid in budgets:
        for s in STARTING:
            open_[s] += max(slots.get(s, 0) - sum(1 for p in picks if p["team_id"] == tid and p["slot"] == s), 0)
    fill, rest = [], []
    for e in left:
        s = next((t for t in (_own(e), "FLEX") if t and open_.get(t, 0) > 0), None)
        if s:
            open_[s] -= 1
            fill.append((e, s))
        else:
            rest.append(e)
    repl = {s: max((e["val"] for e in rest if _fits(e, s)), default=0.0) for s in STARTING}

    # 3. going rate
    money = sum(max(b["remaining"] - mn * b["open_spots"], 0) for b in budgets.values())
    por = sum(max(e["val"] - repl[s], 0.0) for e, s in fill)
    rate = money / por if por > 0 else 0.0

    # 4. the viewer's team
    me = budgets.get(team_id)
    if not me or me["open_spots"] <= 0:
        return {}
    filled = {}
    for p in picks:
        if p["team_id"] == team_id:
            filled[p["slot"]] = filled.get(p["slot"], 0) + 1
    spots = sum(slots.values())
    per_spot = (settings["auction_budget"] - mn * spots) / spots if spots else 0
    adj = (me["remaining"] - mn * me["open_spots"]) / (me["open_spots"] * per_spot) if per_spot > 0 else 1.0
    out = {}
    for e in left:
        s = open_slot(filled, e, slots)
        if not s:
            continue
        fair = mn if s == "BENCH" else (mn + rate * max(e["val"] - repl[s], 0.0)) * adj
        out[e["id"]] = int(max(mn, min(round(fair), me["safe_max"], int(MAX_SHARE * settings["auction_budget"]))))
    return out
