from typing import Optional

from pydantic import BaseModel


class PickPayload(BaseModel):
    matchup_id:  str
    winner:      Optional[str] = None
    games:       Optional[int] = None
    stat_leader: Optional[str] = None


class AdminPickItem(BaseModel):
    matchup_id:  str
    winner:      Optional[str] = None
    games:       Optional[int] = None
    stat_leader: Optional[str] = None


class ResultPayload(BaseModel):
    winner:      str
    games:       int
    stat_leader: str


class WinsPayload(BaseModel):
    wins_a: int
    wins_b: int


class StatLogPayload(BaseModel):
    log: dict  # { "1": [{"name": "OG Anunoby", "value": 8}, ...], "2": [...] }


class StatGuidePayload(BaseModel):
    matchups: list  # [{teams, stat, players: [{name, team, rs, post, r1}]}]


class MatchupPayload(BaseModel):
    id:         str
    label:      str
    team_a:     Optional[str] = None   # NULL = TBD, unclickable in frontend
    team_b:     Optional[str] = None
    seed_a:     Optional[int] = None
    seed_b:     Optional[int] = None
    conference: Optional[str] = None
    round:      Optional[int] = None
    stat_label: Optional[str] = None
    game_time:  Optional[str] = None   # Central Time, e.g. "2026-04-19T13:00"
    home_net_rating_a: Optional[float] = None
    home_net_rating_b: Optional[float] = None
    source_matchup_a: Optional[str] = None
    source_matchup_b: Optional[str] = None


class RosterPayload(BaseModel):
    team_name: str
    players:   list[str]
