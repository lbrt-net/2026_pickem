"""Resetting the draft clears its recap too — a test draft's grades never outlive it (DECISIONS.md, 2026-10-15)."""
from psycopg2.extras import Json

from backend.fantasy_2026_27 import draft
from tests.integration.conftest import S


def test_reset_clears_the_draft_recap(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_recaps (scenario, kind, week, data) VALUES (%s, 'draft', 0, %s) ON CONFLICT DO NOTHING",
                (S, Json({"draft": {}})))
    draft.reset(cur, S)
    cur.execute("SELECT count(*) AS n FROM fantasy_recaps WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 0
