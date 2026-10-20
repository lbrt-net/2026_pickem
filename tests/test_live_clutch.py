"""Clutch time comes from the live box score, not the lagging play-by-play (2026-10-20)."""
from backend.nba.live import clutch_time


def test_clutch_from_the_box_score():
    box = {"period": 4, "gameClock": "PT00M06.00S"}
    assert not clutch_time(box, {"score": 119}, {"score": 113})     # 6-point game: not clutch
    assert clutch_time(box, {"score": 118}, {"score": 113})         # 5: clutch
    assert not clutch_time({"period": 4, "gameClock": "PT05M01.00S"}, {"score": 100}, {"score": 100})  # 5:01 left
    assert clutch_time({"period": 5, "gameClock": "PT03M00.00S"}, {"score": 100}, {"score": 102})      # OT
