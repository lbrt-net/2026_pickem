"""The schedule feed's game status: postponed only when the status text says so (2026-10-10: the 2026-27 feed's
postponedStatus field marked every game postponed)."""
from backend.nba.schedule import _status


def test_status():
    assert _status({"gameStatusText": "7:00 pm ET", "gameStatus": 1, "postponedStatus": "N"}) == "scheduled"
    assert _status({"gameStatusText": "7:00 pm ET", "gameStatus": 1, "postponedStatus": "Y"}) == "scheduled"
    assert _status({"gameStatusText": "PPD", "gameStatus": 1}) == "postponed"
    assert _status({"gameStatusText": "Postponed", "gameStatus": 1}) == "postponed"
    assert _status({"gameStatusText": "Cancelled", "gameStatus": 1}) == "cancelled"
    assert _status({"gameStatusText": "Q3 5:12", "gameStatus": 2}) == "live"
    assert _status({"gameStatusText": "Final", "gameStatus": 3}) == "final"
