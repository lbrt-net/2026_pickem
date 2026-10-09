"""Rec bid (BIDDING_GUIDE.md): what a player or NBA team is worth in an auction right now, re-read after every buy.

    price = $1 + scale × (points over replacement) ^ 1.25

- Weekly value: PROJ MAX (the draft ranking), which already counts how often each player plays (availability.py).
- Replacement, per position (G / F / C / NBA team): fill every team's open roster spots league-wide with the undrafted
  best-first (own slot, then FLEX, then bench); replacement = the best one left at that position.
- Points over replacement = his weekly value − his position's replacement (0 if below).
- scale = all teams' money above the minimum bids for their open spots ÷ the sum of (points over replacement) ^ 1.25 of
  that fill — so the prices of everyone who'll be drafted add up to the money in the room.
- The ^1.25 bend and the method come from a mock 2026-27 auction where every team bid for its best whole roster
  (8–12 teams): it reproduces the stars' prices within a few dollars, and where it's lower (second-tier centers, NBA
  teams) the teams that paid more finished last.
- Your team only (2026-10-08): the spot he'd fill for you sets the bar — his own position's leftovers, or for Flex the
  best leftover of any position; a bench-only player is valued like a Flex, but a Flex/bench-only player is never
  recommended above the best player still available for any of your open G / F / C / TM spots. Then your share:
  your money above the minimums split across your open starting spots by what you'd get in each (him here, a typical
  pick of the room's fill in the others). Rec bid = the lower of the market price and your share, at least the minimum,
  never more than your safe max.
"""
from .logic import SLOT_POSITIONS, open_slot

AVAIL = 1.0  # availability is inside PROJ MAX (per player) since 2026-10-08
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
    my_open = {t: max(slots.get(t, 0) - filled.get(t, 0), 0) for t in slots}

    # Your bar for each kind of spot: his own slot → the players left at that position; Flex → the best leftover of
    # any position (a higher bar: the Flex can take anyone).
    flex_repl = max(repl.values(), default=0.0)

    def mine_over(e, spot):
        if spot == "FLEX":
            return max(e["val"] - flex_repl, 0.0)
        return over(e)

    # What you'd realistically land in each of your open starting spots: the middle of the players the room will
    # take for that kind of spot (the fill above), as (points over the bar) ^ BEND.
    typ = {}

    def typical(spot):
        if spot not in typ:
            vals = sorted((mine_over(e, spot) ** BEND for e in fill if spot == "FLEX" or _own(e) == spot), reverse=True)
            typ[spot] = vals[len(vals) // 2] if vals else 0.0
        return typ[spot]
    starters = [t for t in slots if t != "BENCH" for _ in range(my_open.get(t, 0))]
    spend = max(me["remaining"] - mn * me["open_spots"], 0)  # your money above the minimums

    out, flexish, best_need = {}, [], {}
    for e in left:
        spot = open_slot(filled, e, slots)
        if not spot:
            continue
        if spot == "BENCH":  # your starting spots for him are full: valued like a Flex (vs the best leftover of any position)
            spot = "FLEX"
        if spot == "FLEX":
            flexish.append(e["id"])
        his = mine_over(e, spot) ** BEND
        market = mn + scale * his
        # Your share: your spendable money split across your open starting spots by what you'd get in each —
        # him in this one, a typical player in the others. Few holes and money → full market price; many holes,
        # thin money, or good players still plentiful at your other spots → less.
        others = list(starters)
        if spot in others:
            others.remove(spot)
        weights = his + sum(typical(t) for t in others)
        share = mn + (spend * his / weights if weights > 0 else 0.0)
        out[e["id"]] = int(max(mn, min(round(min(market, share)), me["safe_max"])))
        if spot != "FLEX" and over(e) > 0:  # the best you can get for each of your open G / F / C / TM spots
            best_need[spot] = max(best_need.get(spot, 0), out[e["id"]])
    # Your open G / F / C / TM spots come first: a Flex- or bench-only player is never worth more than the best player
    # still available for any of them (a spot whose best is only replacement level doesn't hold him back).
    if best_need:
        cap = max(mn, min(best_need.values()) - 1)
        for i in flexish:
            out[i] = min(out[i], cap)
    return out
