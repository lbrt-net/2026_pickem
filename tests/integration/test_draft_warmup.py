"""Every draft start opens with a 10-second warm-up: on (everyone's pulled into the room), no clock running, and no
pick / nomination counts until it ends."""
from datetime import timedelta

import pytest

from backend.fantasy_2026_27 import draft
from tests.integration.conftest import S

ADMIN = {"is_admin": True, "discord_id": "admin"}


def test_nothing_counts_during_the_warm_up(league):
    cur = league.cur
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (S,))
    draft.start(cur, S)
    d = draft._row(cur, S)
    assert d["status"] == "in_progress"
    warm = d["warmup_until"] - draft._now()
    assert timedelta(seconds=draft.WARMUP_SECONDS - 1) < warm <= timedelta(seconds=draft.WARMUP_SECONDS)
    assert d["clock_started_at"] == d["warmup_until"]          # the first clock starts when the warm-up ends
    with pytest.raises(ValueError, match="starts in"):
        draft.make_pick(cur, S, "pa1", ADMIN)
    cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 0
