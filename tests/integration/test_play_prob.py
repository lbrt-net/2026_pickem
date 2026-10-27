"""1+ Game % (lineup._play_prob): played once → 1; week over with no game → 0; a missed-game streak lowers it."""
from backend.fantasy_2026_27 import lineup
from tests.integration.conftest import S


def test_played_once_is_certain_and_no_games_left_is_zero(league):
    e = {"id": "pa1", "kind": "player", "nba_team": "AAA"}
    assert lineup._play_prob(league.cur, e, "2025-26", None, True, 2, True, None) == 1.0
    assert lineup._play_prob(league.cur, e, "2025-26", None, True, 0, False, None) == 0.0


def test_streak_math_lowers_the_chance():
    q = lineup.MISS_STREAK[0]
    healthy = 1 - (1 - q) ** 3
    one_miss = 1 - (1 - lineup.MISS_STREAK[1]) * (1 - lineup.MISS_STREAK[2]) * (1 - lineup.MISS_STREAK[3])
    assert one_miss < healthy and round(one_miss, 2) == 0.77


def test_a_game_cut_short_isnt_a_healthy_game():
    """2026-10-26 (Jaren Jackson Jr. 10 min, Markkanen 6 min, both left hurt): 1+ Game % = chance of a HEALTHY game."""
    assert lineup.is_short(6, 33) and not lineup.is_short(20, 33)        # under 40% of his usual minutes
    p, marg = lineup.healthy_chances([1.0])
    assert round(p, 3) == 0.98 and round(marg[0], 3) == 0.98             # 2% of played games are cut short
    after, _ = lineup.healthy_chances([0.96, 0.96], since_short=1)       # coming off a short game
    fresh, _ = lineup.healthy_chances([0.96, 0.96])
    assert after < fresh - 0.03


def test_doomsday_played_once_left_hurt(league):
    """Played Tuesday for 5 minutes and left: not 100% — his one game left is a first game after a short one."""
    from datetime import date
    cur = league.cur
    cur.execute("UPDATE nba_player_games SET minutes = 5 WHERE player_id = 'pa1' AND game_id = 'g1'")
    for gid in ("old1", "old2"):  # last season: a 36-minute starter (usual = 33 with this season's 2 games)
        cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team)
                       VALUES (%s, '2024-25', 'regular', '2025-03-01', 'final', 'AAA', 'BBB')""", (gid,))
        cur.execute("""INSERT INTO nba_player_games (game_id, player_id, season, player_name, team, starter, minutes, pts)
                       VALUES (%s, 'pa1', '2024-25', 'pa1', 'AAA', TRUE, 36, 20)""", (gid,))
    lineup._USUAL.clear()
    league.commit()
    league.clock(date(2025, 10, 22))
    e = next(x for x in lineup.week_view(cur, S, "", 1, entities=[
        {"id": "pa1", "kind": "player", "name": "Alpha One", "slot": "BENCH", "position": "G", "nba_team": "AAA"}])["entries"])
    assert e["week_score"] is not None and e["play_prob"] < 0.75
