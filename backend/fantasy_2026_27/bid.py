"""Rec bid (BIDDING_GUIDE.md): what a player or NBA team is worth in an auction right now, re-read after every buy.

    price = $1 + scale × (points over replacement) ^ 1.25

- Weekly value: PROJ MAX (the draft ranking); players × AVAIL (the share of weeks a player plays), NBA teams every week.
- Replacement, per position (G / F / C / NBA team): fill every team's open roster spots league-wide with the undrafted
  best-first (own slot, then FLEX, then bench); replacement = the best one left at that position.
- Points over replacement = his weekly value − his position's replacement (0 if below).
- scale = all teams' money above the minimum bids for their open spots ÷ the sum of (points over replacement) ^ 1.25 of
  that fill — so the prices of everyone who'll be drafted add up to the money in the room.
- The ^1.25 bend and the method come from a mock 2026-27 auction where every team bid for its best whole roster
  (8–12 teams): it reproduces the stars' prices within a few dollars, and where it's lower (second-tier centers, NBA
  teams) the teams that paid more finished last.
- Your team only: no bid if he fits none of your open spots; never more than your safe max.
"""
from .logic import SLOT_POSITIONS, open_slot

AVAIL = 0.86
BEND = 1.25


def _own(e) -> str | None:
    if e["kind"] == "nba_team":
        return "TEAM"
    return next((s for s, ps in SLOT_POSITIONS.items() if e.get("position") in ps), None)


def rec_bids(pool: list, picks: list, settings: dict, budgets: dict, team_id: str) -> dict:
    """{entity id: recommended bid in dollars} for `team_id`; entities that fit none of its open spots are left out.
    pool = logic.draft_pool ranked by rank_points (e["pts"] = PROJ MAX); budgets = draft._budgets."""
    slots, mn = settings["roster_slots"], settings["auction_min_bid"]
    taken = {p["player_id"] or p["nba_team_id"] for p in picks}
    left = [{**e, "val": e["pts"] * (AVAIL if e["kind"] == "player" else 1.0)}
            for e in pool if e["id"] not in taken and e["pts"] not in (None, float("-inf"))]
    left.sort(key=lambda e: -e["val"])

    # replacement: fill every team's open spots best-first (own slot, then FLEX, then bench)
    open_ = {s: 0 for s in slots}
    for tid in budgets:
        for s in slots:
            open_[s] += max(slots[s] - sum(1 for p in picks if p["team_id"] == tid and p["slot"] == s), 0)
    fill, rest = [], []
    for e in left:
        s = next((t for t in (_own(e), "FLEX", "BENCH") if t and open_.get(t, 0) > 0), None)
        if s:
            open_[s] -= 1
            fill.append(e)
        else:
            rest.append(e)
    repl = {q: max((e["val"] for e in rest if _own(e) == q), default=0.0) for q in ("G", "F", "C", "TEAM")}

    def over(e):
        return max(e["val"] - repl.get(_own(e), 0.0), 0.0)

    # scale: the room's money above minimums spread over the fill's (points over replacement)^BEND
    money = sum(max(b["remaining"] - mn * b["open_spots"], 0) for b in budgets.values())
    total = sum(over(e) ** BEND for e in fill)
    scale = money / total if total > 0 else 0.0

    me = budgets.get(team_id)
    if not me or me["open_spots"] <= 0:
        return {}
    filled = {}
    for p in picks:
        if p["team_id"] == team_id:
            filled[p["slot"]] = filled.get(p["slot"], 0) + 1
    out = {}
    for e in left:
        if not open_slot(filled, e, slots):
            continue
        out[e["id"]] = int(max(mn, min(round(mn + scale * over(e) ** BEND), me["safe_max"])))
    return out
