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


def test_counter(league):
    cur = league.cur
    done_draft(cur)
    tid = trades.propose(cur, S, owner(cur, A), A, B, ["pa1"], ["pb2"], [])
    trades.respond(cur, S, owner(cur, B), tid, "counter")
    cur.execute("SELECT status FROM fantasy_trades WHERE id = %s", (tid,))
    assert cur.fetchone()["status"] == "countered"
    trades.propose(cur, S, owner(cur, B), B, A, ["pb2"], ["pa1"], [])                  # the counter itself


def test_ir_locked_player_not_tradeable(league):
    cur = league.cur
    done_draft(cur)
    cur.execute("UPDATE fantasy_rosters SET slot = 'IR', ir_until = 4 WHERE scenario = %s AND player_id = 'pb1'", (S,))
    with pytest.raises(ValueError, match="locked on IR"):
        trades.propose(cur, S, owner(cur, A), A, B, ["pb1"], ["pa2"], [])               # week 1: locked through week 4


def test_drops_only_on_approval(league):
    cur = league.cur
    done_draft(cur)
    cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id) VALUES (%s, %s, 'BENCH', 'pc1')", (S, B))
    tid = trades.propose(cur, S, owner(cur, A), A, B, [], ["pa2", "pb2", "pc1"], ["pa1"])
    trades.respond(cur, S, owner(cur, B), tid, "accept")
    assert team_of(cur, "pa1")[0] == A                                                  # the drop waits for approval
    trades.decide(cur, S, ADMIN, tid, False)
    assert team_of(cur, "pa1")[0] == A                                                  # rejected: never dropped


def test_traded_player_locked_on_his_old_team_goes_to_waivers_when_dropped(league):
    """2026-10-27 (Zion for Dylan Harper, then Harper dropped): he's locked on his old team's roster this week, so the
    new team's drop is real — waivers, not straight to free agents — though he never locked for the team dropping him."""
    from datetime import date
    from backend.fantasy_2026_27 import transactions, waivers
    cur = league.cur
    done_draft(cur)
    league.commit()
    league.clock(date(2025, 10, 21))                                   # BBB plays: pb2 locks into B's week 1
    tid = trades.propose(cur, S, owner(cur, A), A, B, ["pa1"], ["pb2"], [])
    trades.respond(cur, S, owner(cur, B), tid, "accept")
    trades.decide(cur, S, ADMIN, tid, True)
    cur.execute("SELECT team_id FROM fantasy_lock_ledger WHERE scenario = %s AND entity_id = 'pb2' AND week = 1", (S,))
    assert [r["team_id"] for r in cur.fetchall()] == [B]
    transactions.checkout(cur, S, ADMIN, A, [], ["pb2"], apply=True)
    assert "pb2" in waivers.on_waivers(cur, S)
