"""Trades (2026-10-17): propose → accept → commissioner approves; both rosters must end up legal; nothing moves before
approval; an approval that's no longer legal is refused. Slots here: G, F, C, Bench (4)."""
import pytest

from backend.fantasy_2026_27 import trades
from tests.integration.conftest import A, B, C, S

ADMIN = {"is_admin": True, "discord_id": "admin"}


def owner(cur, team):
    cur.execute("SELECT owner_user_id FROM fantasy_teams WHERE id = %s", (team,))
    return {"discord_id": cur.fetchone()["owner_user_id"]}


def team_of(cur, pid):
    cur.execute("SELECT team_id, slot FROM fantasy_rosters WHERE scenario = %s AND player_id = %s", (S, pid))
    r = cur.fetchone()
    return (r["team_id"], r["slot"]) if r else None


def done_draft(cur):
    cur.execute("UPDATE fantasy_drafts SET status = 'complete' WHERE scenario = %s", (S,))


def test_propose_accept_approve(league):
    cur = league.cur
    done_draft(cur)
    tid = trades.propose(cur, S, owner(cur, A), A, B, ["pa1"], ["pb2"], [])        # G for G
    trades.respond(cur, S, owner(cur, B), tid, "accept")
    assert team_of(cur, "pa1")[0] == A                                               # nothing moves until approved
    with pytest.raises(PermissionError):
        trades.decide(cur, S, owner(cur, A), tid, True)
    trades.decide(cur, S, ADMIN, tid, True)
    assert team_of(cur, "pa1")[0] == B and team_of(cur, "pb2")[0] == A
    cur.execute("SELECT count(*) AS n FROM fantasy_transactions WHERE scenario = %s AND via = 'trade'", (S,))
    assert cur.fetchone()["n"] == 4                                                   # an add and a drop per player


def test_illegal_roster_refused(league):
    cur = league.cur
    done_draft(cur)
    cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id) VALUES (%s, %s, 'BENCH', 'pc1')", (S, B))
    r = trades.check(cur, S, A, B, [], ["pa2", "pb2", "pc1"], ())                      # A: 2 + 3 = 5 players, 4 spots
    assert not r["from"]["ok"]
    with pytest.raises(ValueError, match="your roster"):
        trades.propose(cur, S, owner(cur, A), A, B, [], ["pa2", "pb2", "pc1"], [])
    trades.propose(cur, S, owner(cur, A), A, B, [], ["pa2", "pb2", "pc1"], ["pa1"])     # dropping a guard makes it legal


def test_only_the_right_people_act(league):
    cur = league.cur
    done_draft(cur)
    tid = trades.propose(cur, S, owner(cur, A), A, B, ["pa1"], ["pb2"], [])
    with pytest.raises(PermissionError):
        trades.respond(cur, S, owner(cur, A), tid, "accept")                          # can't accept your own offer
    trades.respond(cur, S, owner(cur, A), tid, "cancel")
    with pytest.raises(ValueError):
        trades.respond(cur, S, owner(cur, B), tid, "accept")                          # cancelled


def test_approval_rechecks_rosters(league):
    cur = league.cur
    done_draft(cur)
    tid = trades.propose(cur, S, owner(cur, A), A, B, ["pa1"], ["pb2"], [])
    trades.respond(cur, S, owner(cur, B), tid, "accept")
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s AND player_id = 'pb2'", (S,))  # B dropped him meanwhile
    with pytest.raises(ValueError, match="can't go through"):
        trades.decide(cur, S, ADMIN, tid, True)
