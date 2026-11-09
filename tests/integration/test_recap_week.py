"""Weekly recap (recap.py): results, players of the week, free agents that beat a starter, the standings — and the
optional awards only when they qualify. Draft Value is live from Week 1's start."""
from datetime import date

from backend.fantasy_2026_27 import recap
from tests.integration.conftest import S


def test_week_report_after_the_week_ends(league):
    cur = league.cur
    assert recap.weekly(cur, S, 1) is None                       # week 1 isn't over
    league.clock(date(2025, 10, 27))
    r = recap.weekly(cur, S, 1)
    assert r and r["best"] in r["teams"] and r["worst"] in r["teams"]
    assert {p["position"] if p["kind"] == "player" else "TEAM" for p in r["players"]} <= {"G", "F", "C", "TEAM"}
    owned = {p["id"] for t in r["faces"].values() for p in t}
    assert all(f["id"] not in owned for f in r["free_agents"])    # free agents are nobody's
    assert len(r["standings"]) == len(r["teams"]) and r["gb"][-1]["week"] == 1
    assert "improbable" not in r["awards"] and "pickups" not in r["awards"]   # nothing qualified: no card
    assert recap.week_recap(cur, S, 1) == recap.week_recap(cur, S, 1)        # frozen once built
    assert [w["week"] for w in recap.recap(cur, S)["weeks"]] == [1]


def test_restat_rebuilds_a_frozen_week(league):
    """2026-10-26: a stat correction (clutch recount) reaches a frozen recap only through restat_week."""
    cur = league.cur
    league.clock(date(2025, 10, 27))
    before = recap.week_recap(cur, S, 1)
    star = before["players"][0]
    cur.execute("""UPDATE nba_player_games SET pts = pts + 50 WHERE player_id = %s AND game_id IN
                   (SELECT game_id FROM nba_games WHERE game_date BETWEEN '2025-10-20' AND '2025-10-26')""", (star["id"],))
    assert recap.week_recap(cur, S, 1) == before                     # still frozen
    out = recap.restat_week(cur, S, 1)
    assert out["old_recap"] == before
    new = next(p for p in out["recap"]["players"] if p["id"] == star["id"])
    assert new["score"] > star["score"]
    assert recap.week_recap(cur, S, 1) == out["recap"]               # frozen again


def test_draft_value_is_live(league):
    """2026-10-30: Draft Value counts the current week's games so far — no waiting for the week to end — and only
    regular-season weeks."""
    cur = league.cur
    from tests.integration.test_recap_draft import pool
    pool(cur)                                                     # a draft to value
    league.clock(date(2025, 10, 23))                              # mid week 1
    v = recap.draft_value(cur, S, recap.build_draft(cur, S))
    assert v is not None and "through" not in v
    assert isinstance(v["regrets"], list)                           # the Biggest regrets list (dropped picks)
    wk = [r["added_wk"] for r in v["regrets"]]
    assert wk == sorted(wk, reverse=True)                            # ranked by the per-week number it shows
    assert any(p["weeks"] == 1 for p in v["picks"])                  # week 1 counts while it's on


def test_commissioner_preview_from_saturday(league):
    """2026-10-31: the commissioner sees the week under way on Recap from its Saturday (noon Central since 2026-11-07; a sim-date
    league from that Saturday) until the real recap is ready; nobody else ever does."""
    cur = league.cur
    league.clock(date(2025, 10, 24))                              # Friday of week 1 (Oct 20–26)
    assert recap.recap(cur, S, admin=True)["preview"] is None
    league.clock(date(2025, 10, 25))                              # Saturday
    assert recap.recap(cur, S, admin=True)["preview"]["week"] == 1
    assert recap.recap(cur, S)["preview"] is None                  # not for everyone else
    league.clock(date(2025, 10, 27))                              # week over: the real recap, no preview
    assert recap.recap(cur, S, admin=True)["preview"] is None


def test_improbable_win_is_a_long_climb_not_a_sunday_comeback(league):
    """2026-11-01: Improbable win reads Mon–Sat (Sunday's comeback is the Buzzer Beater): eligible once the winner was
    under 50% by 0.05+ in all, ranked by 0.5 − chance summed over those days (days as the favorite count against)."""
    from datetime import timedelta
    cur = league.cur
    league.clock(date(2025, 10, 27))
    from backend.fantasy_2026_27 import winprob
    score = recap.weekly(cur, S, 1)["scores"]
    pairs = [(m["a"], m["b"]) for m in winprob.week_probs(cur, S, 1)["matchups"]]
    a, b = pairs[0]
    w = a if score[a] > score[b] else b

    def curve(ps):
        cur.execute("DELETE FROM fantasy_winprob_daily WHERE scenario = %s", (S,))
        for i, p in enumerate(ps):
            cur.execute("INSERT INTO fantasy_winprob_daily (scenario, week, asof, team_a, team_b, p) VALUES (%s, 1, %s, %s, %s, %s)",
                        (S, date(2025, 10, 20) + timedelta(days=i), a, b, p if w == a else 1 - p))
        return recap.weekly(cur, S, 1)["awards"].get("improbable")
    assert curve([0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.05]) is None      # a Sunday comeback: the Buzzer Beater's
    assert curve([0.60, 0.60, 0.48, 0.60, 0.60, 0.60, 0.60]) is None      # barely behind once: not enough
    imp = curve([0.45, 0.42, 0.45, 0.48, 0.45, 0.40, 0.80])               # behind all week, lowest Saturday
    assert imp["winner"] == w and imp["low"] == 0.4
    # 2026-11-08: a day counts 7 ÷ days left — 30% on Saturday beats 30% on Monday
    early = curve([0.30, 0.50, 0.50, 0.50, 0.50, 0.50, 0.60])["score"]
    late = curve([0.50, 0.50, 0.50, 0.50, 0.50, 0.30, 0.60])["score"]
    assert late > early
    assert curve([0.15, 0.46, 0.46, 0.62, 0.65, 0.57, 0.73]) is None      # Deco wk 3: behind Monday, favorite late


def test_draft_value_saved_not_built_on_a_visit(league):
    """2026-11-01: the live league's Draft Value is saved (nightly job) and the Recap tab reads the saved copy."""
    cur = league.cur
    from tests.integration.test_recap_draft import pool
    pool(cur)
    league.clock(date(2025, 10, 23))
    draft = recap.build_draft(cur, S)
    first = recap.saved_value(cur, S, draft)                       # missing: built and saved
    cur.execute("UPDATE fantasy_recaps SET data = '{\"saved\": true}' WHERE scenario = %s AND kind = 'value'", (S,))
    assert recap.saved_value(cur, S, draft) == {"saved": True}      # then read, never rebuilt
    assert recap.save_value(cur, S, draft) == first                 # the nightly save rebuilds it


def test_bench_card_number_is_its_own_swap(league):
    """2026-11-08: the bench card shows one swap, so its number = benched score − started score (not the whole
    best-lineup gap, which other swaps can add to)."""
    cur = league.cur
    league.clock(date(2025, 10, 27))
    aw = recap.weekly(cur, S, 1)["awards"]
    for x in aw.get("bench_top", []):
        if x["sat"] and x["started"]:
            assert x["points"] == round(x["sat"]["score"] - x["started"]["score"], 1)


def test_draft_value_replacement_is_a_level_not_one_player(league):
    """2026-11-08: points above replacement use the replacement level each week (the drafted+1th best score at the
    position), so a draft-day replacement who never plays (Brandon Ingram) doesn't turn raw scores into 'above'."""
    cur = league.cur
    from tests.integration.test_recap_draft import pool
    pool(cur)
    league.clock(date(2025, 10, 26))
    draft = recap.build_draft(cur, S)
    a = recap.draft_value(cur, S, draft)
    for pos in draft["replacement"]:
        draft["replacement"][pos] = {**draft["replacement"][pos], "id": "never-played"}
    b = recap.draft_value(cur, S, draft)
    assert [p["actual"] for p in a["picks"]] == [p["actual"] for p in b["picks"]]
