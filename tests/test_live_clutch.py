"""Clutch time comes from the live box score, not the lagging play-by-play (2026-10-20)."""
from backend.nba import live
from backend.nba.live import clutch_time


def test_clutch_from_the_box_score():
    box = {"period": 4, "gameClock": "PT00M06.00S"}
    assert not clutch_time(box, {"score": 119}, {"score": 113})     # 6-point game: not clutch
    assert clutch_time(box, {"score": 118}, {"score": 113})         # 5: clutch
    assert not clutch_time({"period": 4, "gameClock": "PT05M01.00S"}, {"score": 100}, {"score": 100})  # 5:01 left
    assert clutch_time({"period": 5, "gameClock": "PT03M00.00S"}, {"score": 100}, {"score": 102})      # OT


def test_clutch_points_use_the_score_before_the_play():
    """2026-10-26 (Siakam, IND @ MIL, down 7 at 4:29): a 2 that cuts 7 to 5 isn't clutch; the free throw after it is.
    Matches nba.com's LeagueDashPlayerClutch on every player Oct 23–25 (210 of 210; the old count got 33 wrong)."""
    from backend.nba.live import clutch_and_violations
    acts = [{"period": 4, "clock": "PT05M30.00S", "actionType": "2pt", "shotResult": "Made", "personId": 9, "scoreHome": "101", "scoreAway": "94"},
            {"period": 4, "clock": "PT04M29.00S", "actionType": "2pt", "shotResult": "Made", "personId": 1, "scoreHome": "101", "scoreAway": "96"},
            {"period": 4, "clock": "PT04M29.00S", "actionType": "foul", "personId": 2, "scoreHome": "101", "scoreAway": "96"},
            {"period": 4, "clock": "PT03M54.00S", "actionType": "freethrow", "shotResult": "Made", "personId": 1, "scoreHome": "101", "scoreAway": "97"},
            {"period": 4, "clock": "PT03M00.00S", "actionType": "3pt", "shotResult": "Made", "personId": 3, "scoreHome": "104", "scoreAway": "97"}]
    clutch, _, _ = clutch_and_violations(acts)
    assert clutch == {1: 1, 3: 3}          # the leader's 3 from up 4 counts; up 7 after doesn't matter


def test_a_final_game_is_pulled_for_30_minutes():
    """2026-10-27 (Mobley at 29.5 all night): the NBA's scorers entered overtime stats up to 36 minutes after the buzzer."""
    assert live.FINAL_WINDOW == 1800
