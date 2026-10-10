"""Weekly win probability (winprob.py) never does anything absurd."""
import random

import pytest

from backend.fantasy_2026_27.winprob import win_prob

RUNS = 2000


def player(current=None, left=0, p=1.0, scores=(30, 40, 50)):
    return {"current": current, "games": [(p, 1.0)] * left, "scores": list(scores)}


def team(*players):
    return list(players)


def test_always_between_0_and_1():
    rnd = random.Random(1)
    for _ in range(60):
        a = team(*[player(rnd.choice([None, rnd.uniform(10, 60)]), rnd.randint(0, 4), rnd.random(), [rnd.uniform(0, 80) for _ in range(8)]) for _ in range(5)])
        b = team(*[player(rnd.choice([None, rnd.uniform(10, 60)]), rnd.randint(0, 4), rnd.random(), [rnd.uniform(0, 80) for _ in range(8)]) for _ in range(5)])
        assert 0.0 <= win_prob(a, b, runs=300) <= 1.0


def test_both_sides_add_up_to_100_percent():
    a = team(player(35, 2), player(None, 3, 0.8))
    b = team(player(50, 1), player(20, 2))
    assert win_prob(a, b, runs=RUNS, seed=3) + win_prob(b, a, runs=RUNS, seed=3) == pytest.approx(1.0, abs=0.04)


def test_decided_week_is_exact():
    a, b = team(player(60), player(40)), team(player(50), player(45))   # 100 vs 95, nothing left
    assert win_prob(a, b) == 1.0 and win_prob(b, a) == 0.0
    assert win_prob(team(player(50)), team(player(50))) == 0.5


def test_cant_catch_up_means_zero():
    leader = team(player(200))                          # done for the week
    trailer = team(player(10, left=4, scores=[20, 30]))  # best possible 30
    assert win_prob(trailer, leader, runs=RUNS) == 0.0


def test_identical_teams_are_a_coin_flip():
    a = team(player(None, 3), player(None, 2, scores=(10, 60)))
    assert win_prob(a, [dict(x) for x in a], runs=RUNS, seed=5) == pytest.approx(0.5, abs=0.05)


def test_bigger_lead_never_lowers_your_chance():
    b = team(player(None, 3), player(None, 3))
    ps = [win_prob(team(player(lead, 1), player(None, 3)), b, runs=RUNS, seed=9) for lead in (0, 20, 40, 60, 80)]
    assert ps == sorted(ps)


def test_more_games_left_never_lowers_your_chance():
    b = team(player(30, 2))
    ps = [win_prob(team(player(20, left)), b, runs=RUNS, seed=11) for left in (0, 1, 2, 3, 4)]
    assert all(later >= earlier - 0.01 for earlier, later in zip(ps, ps[1:]))


def test_injured_out_games_count_for_nothing():
    b = team(player(35))
    hurt = team(player(20, left=3, p=0.0))
    assert win_prob(hurt, b, runs=RUNS) == win_prob(team(player(20)), b, runs=RUNS) == 0.0


def test_adding_a_good_player_helps():
    b = team(player(None, 3), player(None, 3))
    base = team(player(None, 3))
    assert win_prob(base + [player(None, 3, scores=(60, 70))], b, runs=RUNS, seed=2) > win_prob(base, b, runs=RUNS, seed=2)


def test_same_inputs_same_answer():
    a, b = team(player(None, 3)), team(player(None, 3, scores=(20, 70)))
    assert win_prob(a, b, seed=4) == win_prob(a, b, seed=4)


def test_calibrated_on_made_up_weeks():
    """Weeks generated from known player ranges: of the matchups it calls ~X%, about X% must actually be won."""
    rnd = random.Random(21)
    bins = {}
    for _ in range(300):
        mk = lambda: [player(None, rnd.randint(1, 4), 1.0, [rnd.gauss(35, 12) for _ in range(30)]) for _ in range(5)]
        a, b = mk(), mk()
        p = win_prob(a, b, runs=400, seed=rnd.randrange(10 ** 6))
        play = lambda t: sum(max(rnd.choice(s["scores"]) for _ in s["games"]) for s in t)  # the real week, same ranges
        won = play(a) > play(b)
        bins.setdefault(min(int(p * 5), 4), []).append((p, won))
    for rows in bins.values():
        if len(rows) >= 30:
            said = sum(p for p, _ in rows) / len(rows)
            got = sum(w for _, w in rows) / len(rows)
            assert abs(said - got) < 0.15, f"said {said:.0%}, won {got:.0%}"
