"""Rec bid (BIDDING_GUIDE.md): what a player or NBA team is worth to YOUR team right now, re-read after every buy.
Rebuilt 2026-10-15 as one ratio — value to you, not a guess at what the room will pay:

    Rec bid = $1 + your spare money × his gap ÷ (his gap + a typical gap at each of your other open starting spots)

- Weekly value: the draft list's rank value (board.py), the same number the list ranks by.
- Your spare money: what you have left minus the minimum bid for each of your open spots.
- His gap = his weekly value − the replacement for the spot he'd fill for you:
  - your own G / F / C / TM spot still open → the next starter left after every team fills that position
    (each team's open spots at that position, league-wide, taken best-first);
  - that spot already filled → he's a Flex: against the true replacement, the next player left once every team's
    open Flex spots are filled too from the players beyond the starters;
  - Flex filled too → he'd only sit on your bench, and bench players never score → the minimum bid.
- Typical gap at a spot: the middle of the players the room will take for that kind of spot (the starters still
  needed at that position, or the Flex group), against the same replacement. Using a typical player there — not the
  best — is what lets a star's share grow: you won't land the best player at every spot.
- Other teams' money never moves your numbers (a team that overspent on Jokić can't bid on Luka); only who's left does.
- Never under the minimum bid, never over your safe max.
"""
from .logic import SLOT_POSITIONS, open_slot


def _own(e) -> str | None:
    if e["kind"] == "nba_team":
        return "TEAM"
    return next((s for s, ps in SLOT_POSITIONS.items() if e.get("position") in ps), None)


def _middle(gaps: list) -> float:
    return sorted(gaps)[len(gaps) // 2] if gaps else 0.0


def rec_bids(pool: list, picks: list, settings: dict, budgets: dict, team_id: str) -> dict:
    """{entity id: recommended bid in dollars} for `team_id`; entities that fit none of its open spots are left out.
    pool = logic.draft_pool ranked by rank_points (e["pts"] = rank value); budgets = draft._budgets."""
    slots, mn = settings["roster_slots"], settings["auction_min_bid"]
    me = budgets.get(team_id)
    if not me or me["open_spots"] <= 0:
        return {}
    taken = {p["player_id"] or p["nba_team_id"] for p in picks}
    left = sorted((e for e in pool if e["id"] not in taken and e["pts"] not in (None, float("-inf"))), key=lambda e: -e["pts"])

    # league-wide open spots by kind
    open_ = {s: 0 for s in slots}
    for tid in budgets:
        for s in slots:
            open_[s] += max(slots[s] - sum(1 for p in picks if p["team_id"] == tid and p["slot"] == s), 0)

    # starters: each position's open spots, best-first; the next one left is that position's replacement
    starters, repl, beyond = {}, {}, []
    for q in ("G", "F", "C", "TEAM"):
        at = [e for e in left if _own(e) == q]
        n = open_.get(q, 0)
        starters[q], rest = at[:n], at[n:]
        repl[q] = rest[0]["pts"] if rest else 0.0
        beyond += rest
    # Flex: the players beyond the starters fill every open Flex spot; the next one left is the true replacement
    beyond.sort(key=lambda e: -e["pts"])
    nf = open_.get("FLEX", 0)
    flex_group = beyond[:nf]
    flex_repl = beyond[nf]["pts"] if len(beyond) > nf else 0.0

    def bar(spot, e):
        return flex_repl if spot == "FLEX" else repl.get(_own(e), 0.0)

    typical = {q: _middle([e["pts"] - repl[q] for e in starters[q]]) for q in starters}
    typical["FLEX"] = _middle([e["pts"] - flex_repl for e in flex_group])

    filled = {}
    for p in picks:
        if p["team_id"] == team_id:
            filled[p["slot"]] = filled.get(p["slot"], 0) + 1
    my_starting = [t for t in slots if t != "BENCH" for _ in range(max(slots[t] - filled.get(t, 0), 0))]
    spare = max(me["remaining"] - mn * me["open_spots"], 0)

    out = {}
    for e in left:
        spot = open_slot(filled, e, slots)
        if not spot:
            continue
        gap = max(e["pts"] - bar(spot, e), 0.0) if spot != "BENCH" else 0.0
        others = list(my_starting)
        if spot in others:
            others.remove(spot)
        weights = gap + sum(max(typical.get(t, 0.0), 0.0) for t in others)
        value = mn + (spare * gap / weights if weights > 0 else 0.0)
        out[e["id"]] = int(max(mn, min(round(value), me["safe_max"])))
    return out
