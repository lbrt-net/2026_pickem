"""Per-game projection for any player, any target season ('26 for validation, '27 forward).

Inputs: the 3 seasons before the target (rates), 5 for zone mix. Seasons with 0 GP drop out (weights are GP/POSS-based).
Base season (minutes, usage, career features) = most recent input season with 20+ GP; if none, most recent with any GP.
Age = base-season age + seasons between base and target - 1 (gap counts).
  MPG:     base MPG + career model (age / years / production tier / prior trend), trained on healthy transitions
           that end before the target (no peeking).
  pace:    own on-court PACE, minutes-weighted, recency 3.        poss/G = MPG x pace / 48
  usage:   resplit of base-season usage on the target-season roster ('26: first-game team; '27: 2026-27 roster);
           stayers only, half strength on FGA/FTA, full on TOV.
  FGA/75, FTA/75 recency 2; zone share 5 seasons recency 5; zone FG% 3 seasons attempt-weighted k=25 (none at 200+);
  FT% same; AST/75 recency 5, STL/75 equal, BLK/75 recency 5, TOV/75 recency 2; OREB/75, DREB/75 recency 2
  (DREB teammate effect not applied yet).  BLKD not included (data pending).
"""
import contextlib
import io
import json
import runpy
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from load_historical_boxscores import minutes  # noqa: E402
from backend.fantasy_2026_27.logic import SCORING  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
SEAS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
BOX = {"2021-22": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2021_22.parquet",
       "2022-23": R + "box_scores_traditional/trad_box_scores_2022_23.parquet",
       "2023-24": R + "box_scores_traditional/trad_box_scores_2023_24.parquet",
       "2024-25": R + "box_scores_traditional/trad_box_scores_2024_25.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2025_26.parquet"}
STATS = ["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pts"]
ZONES = ["RA", "Paint", "Mid", "Corner3", "Other3"]
VAL = np.array([2, 2, 2, 3, 3], float)


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


A = {s: tab("player_advanced", s).astype({"GP": float, "POSS": float}) for s in SEAS}
BT, BG, FIRST = {}, {}, {}
for s, f in BOX.items():
    d = pd.read_parquet(f)
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    d = d[d.m > 0]
    BT[s] = d.groupby("player_id")[STATS].sum().astype(float)
    BG[s] = d  # per game, for actuals
    FIRST[s] = d.sort_values("game_id").groupby("player_id").team_tricode.first()

# ---- late-season jumps: nothing in the first 80% of the schedule, real minutes in the final fifth ----
# (tank-time runway). Those player-seasons are rewritten with the final fifth counted at LATE_W weight,
# so everything downstream (base season, minutes, rates, career features) follows his first-80% role.
LATE_W, JUMP_EARLY_MAX, JUMP_LATE_MIN = 0.1, 10.0, 15.0
LATE_JUMPS = {}
import os as _os
APPLY_LATE = _os.environ.get('APPLY_LATE', '1') == '1'
for s in BOX:
    if not APPLY_LATE:
        break
    d = BG[s]
    date = pd.to_datetime(d.game_id.map(pd.read_parquet(R + f"schedules/schedule_{s.replace('-', '_')}.parquet").set_index("game_id").game_date))
    late = date > date.quantile(0.8)
    d = d.assign(late=late.to_numpy())
    team_games = d.groupby(["team_tricode", "late"]).game_id.nunique()
    part = d.groupby(["player_id", "late"]).agg(gp=("game_id", "nunique"), m=("m", "sum"), team=("team_tricode", lambda x: x.mode().iloc[0]),
                                                **{st: (st, "sum") for st in STATS}).reset_index()
    part["per_team_game"] = part.m / [team_games.get((t, l), np.nan) for t, l in zip(part.team, part.late)]
    w = part.pivot(index="player_id", columns="late")
    early_mpt = w["per_team_game"].get(False, pd.Series(dtype=float)).reindex(w.index).fillna(0)
    late_mpt = w["per_team_game"].get(True, pd.Series(dtype=float)).reindex(w.index).fillna(0)
    early_gp = w["gp"].get(False, pd.Series(dtype=float)).reindex(w.index).fillna(0)
    early_mpg = (w["m"].get(False, pd.Series(dtype=float)).reindex(w.index).fillna(0) / early_gp.replace(0, np.nan)).fillna(0)
    ps = SEAS[SEAS.index(s) - 1] if SEAS.index(s) > 0 else None
    prior_mpg = A[ps].MIN.reindex(w.index).fillna(0) if ps else pd.Series(0.0, index=w.index)
    benched = ((early_gp >= 5) & (early_mpg < JUMP_EARLY_MAX)) | ((early_gp < 5) & (prior_mpg < 20))  # benched/absent-but-not-established, not hurt
    jump = w.index[benched & (late_mpt >= JUMP_LATE_MIN)]
    LATE_JUMPS[s] = {}
    for pid in jump:
        e = part[(part.player_id == pid) & ~part.late]
        l = part[(part.player_id == pid) & part.late]
        ge, me = (e.gp.sum(), e.m.sum()) if len(e) else (0, 0.0)
        gl, ml = l.gp.sum(), l.m.sum()
        gp_adj, m_adj = ge + LATE_W * gl, me + LATE_W * ml
        LATE_JUMPS[s][pid] = (round(float(early_mpt[pid]), 1), round(float(late_mpt[pid]), 1), int(ge), int(gl))
        if pid in A[s].index and gp_adj > 0:
            ratio = m_adj / (me + ml)
            A[s].loc[pid, ["POSS", "MIN", "GP"]] = [float(A[s].loc[pid, "POSS"] * ratio), m_adj / gp_adj, float(gp_adj)]
        BT[s].loc[pid, STATS] = [float((e[st].sum() if len(e) else 0) + LATE_W * l[st].sum()) for st in STATS]
with contextlib.redirect_stdout(io.StringIO()):
    Z = runpy.run_path(S + "zone_projection.py", run_name="lib")
    U = runpy.run_path(S + "usage_resplit.py", run_name="lib")
ZS = {s: Z["load"](s).pivot_table(index="pid", columns="zone", values=["fga", "fgm"], fill_value=0) for s in SEAS}
HT = {}
for _s in ["2019-20"] + SEAS:
    HT.update(tab("bios", _s).PLAYER_HEIGHT_INCHES.dropna().to_dict())
# ≤6'2", 6'3–6'5, 6'6–6'8, 6'9–6'10, 6'11+ (unknown height → 6'6–6'8): rarely-fouled players' FT% by height
# (77.4 / 75.8 / 73.3 / 70.0 / 66.9) minus 7.5 pts, since a player with no FT history at all is an unknown
NOFT_BY_HT = [0.699, 0.683, 0.658, 0.625, 0.594]
AST2 = {s: tab("player_scoring", s).PCT_AST_2PM for s in SEAS}
RIM_PRIOR = (0.657, 0.0090, 0.069)  # rim FG% at 6'6" and 60% assisted; +0.9 pt per inch; +0.69 pt per 10 pts of assisted share
K_RIM = 70  # attempts where his own rim rate gets half the weight (spread between players net of luck, '21–'25)
MID_FLOOR, MID_UP, MID_CAP, MID_DOWN = 0.38, 0.65, 0.45, 0.5

# ---- career MPG model (healthy transitions ending before the target) ----
USE_OVER = False
USE_USG_ADJ = True
THREE_FLOOR, THREE_UP, THREE_CAP, THREE_DOWN = 0.34, 0.7, 0.38, 0.5
USG_COEF = json.load(open(S + 'usage_coef.json'))
BASE_NEEDS = (50, 20, 1)
CRED_K, CRED_MPG, CRED_FULL = 15, 16.0, 60


def ptdiff(season):
    sc = pd.read_parquet(R + f"schedules/schedule_{season.replace('-', '_')}.parquet")
    sc = sc[(sc.game_id.astype(str).str[2] == "2") & (sc.game_status == 3)]
    rr = [(x.home_team_tricode, x.home_score - x.away_score) for x in sc.itertuples()] + \
         [(x.away_team_tricode, x.away_score - x.home_score) for x in sc.itertuples()]
    return pd.DataFrame(rr, columns=["t", "d"]).groupby("t").d.mean()


PTD = {s: ptdiff(s) for s in SEAS}
PIE_MED = {s: A[s][A[s].GP >= 10].PIE.median() for s in SEAS}
USE_TEAM = True


def over_of(a):
    """minutes rank minus impact (PIE) rank within the season, among players with 10+ GP: + = playing more than his impact"""
    q = a[a.GP >= 10]
    return q.MIN.rank(pct=True) - q.PIE.rank(pct=True)

csrc = open(S + "career.py").read().split("# points/G for the 210")[0].split("train = pd.concat")[0]
C = {"over_of": over_of, "PTD": PTD, "PIE_MED": PIE_MED}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(csrc.replace('j = j[(j.GP >= 20) & (j.GP_1 >= 20)].copy()',
                              'j = j[(j.GP >= 20) & (j.GP_1 >= 20)].copy()\n    j["GP_prev"] = ap.GP.reindex(j.index)\n'
                              '    j["healthy"] = (j.GP >= 50) & (j.GP_1 >= 50) & (j.GP_prev.fillna(0) >= 50)\n'
                              '    j["over"] = over_of(a0).reindex(j.index)\n'
                              '    j["tdiff"] = a0.TEAM_ABBREVIATION.reindex(j.index).map(PTD[s0])\n'
                              '    j["moved"] = (a0.TEAM_ABBREVIATION.reindex(j.index) != a1.TEAM_ABBREVIATION.reindex(j.index)).astype(float)\n'
                              '    j["badlow"] = ((j.tdiff <= -4) & (a0.PIE.reindex(j.index) < PIE_MED[s0])).astype(float)'), "career", "exec"), C)
_models = {}


def career_model(target):
    if target in _models:
        return _models[target]
    ti = SEAS.index(target) if target in SEAS else len(SEAS)
    trs = [(SEAS[i - 1], SEAS[i], SEAS[i + 1]) for i in range(1, len(SEAS) - 1) if i + 1 < ti]
    train = pd.concat(C["rows"](*t) for t in trs)
    train = train[train.healthy]
    C["train"] = train
    cuts = list(np.quantile(train["prod"], [0.2, 0.4, 0.6, 0.8]))
    C["BANDS"] = {
        **({"over": ([-9, -0.3, -0.1, 0.1, 0.3, 9], ["under 0.3+", "under 0.1–0.3", "even", "over 0.1–0.3", "over 0.3+"])} if USE_OVER else {}),
        **({"tdiff": ([-99, -8, -4, 0, 4, 99], ["tank", "-8–-4", "-4–0", "0–+4", "+4+"]),
            "moved": ([-1, 0.5, 2], ["stayed", "moved"]), "badlow": ([-1, 0.5, 2], ["no", "bad team+low PIE"])} if USE_TEAM else {}),
        "age": ([0, 23, 26, 29, 32, 35, 99], ["≤22", "23–25", "26–28", "29–31", "32–34", "35+"]),
        "yrs": ([-99, 2, 4, 7, 11, 99], ["0–1", "2–3", "4–6", "7–10", "11+"]),
        "prod": ([-1] + cuts + [99], ["P1 low", "P2", "P3", "P4", "P5 top"]),
        "trend": ([-99, -4, -1, 1, 4, 99], ["fell 4+", "fell 1–4", "flat", "rose 1–4", "rose 4+"]),
    }
    src_ = {"age": "AGE", "yrs": "yrs", "prod": "prod", "trend": "trend", "over": "over", "tdiff": "tdiff", "moved": "moved", "badlow": "badlow"}

    def design(df):
        out = []
        for f, (cut, labs) in C["BANDS"].items():
            b = pd.cut(df[src_[f]], cut, labels=False, right=False)
            for i, lab in enumerate(labs):
                out.append(((b == i) & b.notna()).astype(float).rename(f"{f}:{lab}"))
            out.append(b.isna().astype(float).rename(f"{f}:unknown"))
        return pd.concat(out, axis=1)

    C["design"] = design
    Xtr = C["design"](train)
    Xtr = Xtr.loc[:, Xtr.sum() > 0]
    X = np.column_stack([np.ones(len(Xtr)), Xtr.to_numpy()])
    pen = 5.0 * np.eye(X.shape[1])
    pen[0, 0] = 0
    beta = np.linalg.solve(X.T @ X + pen, X.T @ (train.MIN_1 - train.MIN).to_numpy())
    _models[target] = (Xtr.columns, beta)
    return _models[target]


_rosters, _usg = {}, {}


def roster(target):
    if target not in _rosters:
        if target == "2026-27":
            r = pd.read_csv(f"{R}rosters/2026-27.csv")
            _rosters[target] = r.groupby("TEAM").PLAYER_ID.apply(set).to_dict(), r.set_index("PLAYER_ID").TEAM
        else:
            f = FIRST[target]
            _rosters[target] = f.groupby(f).apply(lambda x: set(x.index)).to_dict(), f
    return _rosters[target]


def base_info(pid, ins):
    """most recent input season with 50+ GP (healthy), else 20+, else any"""
    for need in BASE_NEEDS:
        for s in reversed(ins):
            if A[s].GP.get(pid, 0) >= need:
                return s
    return None


def usage_for(target):
    """resplit using each roster player's base-season usage + MPG (not just the prior season)"""
    if target in _usg:
        return _usg[target]
    ti = SEAS.index(target) if target in SEAS else len(SEAS)
    ins = SEAS[max(0, ti - 3):ti]
    teams, _ = roster(target)
    prior = pd.DataFrame(index=sorted({p for s in teams.values() for p in s}))
    u, m = [], []
    for p in prior.index:
        b = base_info(p, ins)
        u.append(A[b].USG_PCT[p] if b else np.nan)
        m.append(A[b].MIN[p] if b else np.nan)
    prior["USG_PCT"], prior["MIN"] = u, m
    _usg[target] = U["project"](prior.dropna(), teams)
    return _usg[target]


# ---- EPM flag ('27 only; temporary hand-entered '26 EPM — see PROJECTIONS.md) ----
import re as _re
import unicodedata as _ud


def name_key(n):
    n = _ud.normalize("NFKD", str(n)).encode("ascii", "ignore").decode().lower()
    return _re.sub(r"[^a-z]", "", _re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", n))


EPM = pd.read_csv(R + "epm_manual_2025_26.csv", comment="#")
EPM_BAD = {name_key(n): e for n, e in zip(EPM.name, EPM.epm) if e <= -2.5}
EPM_PENALTY_FP = 2.5


# ---- defensive rebounding is shared (dreb_teammates.py): −0.62 DREB% per +1 of teammates' minutes-weighted DREB%
USE_DREB_TM, DREB_BETA = True, -0.62


def _dreb_strength(prior, ids, me):
    a = A[prior]
    low = a[a.MIN < 15].DREB_PCT.median()
    ids = [p for p in ids if p != me]
    if not ids:
        return np.nan
    d = np.array([a.DREB_PCT.get(p, low) for p in ids], float)
    w = np.array([a.MIN.get(p, 15.0) * min(a.GP.get(p, 30), 82) for p in ids], float)
    return float((d * w).sum() / w.sum())


def dreb_shift(pid, target):
    """change in his DREB% from the change in teammates' rebounding, prior-season team → target roster"""
    ti = SEAS.index(target) if target in SEAS else len(SEAS)
    prior = SEAS[ti - 1]
    if prior not in BG or pid not in A[prior].index:
        return 0.0
    bp = BG[prior]
    mine = bp[bp.player_id == pid]
    if mine.empty:
        return 0.0
    old_team = mine.team_tricode.mode().iloc[0]
    old_ids = set(bp[bp.team_tricode == old_team].player_id)
    teams, team_of = roster(target)
    new_ids = teams.get(team_of.get(pid), set())
    old, new = _dreb_strength(prior, old_ids, pid), _dreb_strength(prior, new_ids, pid)
    return 0.0 if np.isnan(old) or np.isnan(new) else DREB_BETA * (new - old)


# ---- own shots blocked (blkd.py): zone block rates × player factor; BLKA from season game logs
USE_BLKD = True
BLK_RATE = np.array([0.104, 0.062, 0.003, 0.037, 0.026])  # RA, paint, mid, corner 3, other 3 (fit '22–'25)


def _blka(s):
    try:
        rs = json.load(open(f"{R}game_logs/{s}.json"))["resultSets"][0]
    except FileNotFoundError:
        return pd.Series(dtype=float)
    d = pd.DataFrame(rs["rowSet"], columns=rs["headers"])
    return d.groupby("PLAYER_ID").BLKA.sum()


BLKA = {s: _blka(s) for s in SEAS}


def project(pid, target):
    ti = SEAS.index(target) if target in SEAS else len(SEAS)
    ins3, ins5 = SEAS[max(0, ti - 3):ti], SEAS[max(0, ti - 5):ti]
    base = base_info(pid, ins3)
    if base is None:
        return None
    a = A[base]
    gap = (ti - SEAS.index(base)) - 1
    # MPG
    cols, beta = career_model(target)
    prev = SEAS[SEAS.index(base) - 1] if SEAS.index(base) > 0 else None
    _, team_of_ = roster(target)
    base_team = a.TEAM_ABBREVIATION.get(pid)
    td = PTD[base].get(base_team, np.nan)
    row = pd.DataFrame([dict(AGE=a.AGE[pid] + gap, yrs=C["years"](pid, base) + gap, over=over_of(a).get(pid, np.nan),
                             tdiff=td, moved=float(team_of_.get(pid) is not None and team_of_.get(pid) != base_team),
                             badlow=float(td <= -4 and a.PIE[pid] < PIE_MED[base]),
                             prod=a.USG_PCT[pid] * a.MIN[pid],
                             trend=a.MIN[pid] - (A[prev].MIN.get(pid, np.nan) if prev else np.nan))])
    x = C["design"](row).reindex(columns=cols, fill_value=0).to_numpy()[0]
    g_tot = sum(A[s_].GP.get(pid, 0) for s_ in ins3)
    wc = min(1.0, g_tot / CRED_FULL) if CRED_K else 1.0  # under CRED_FULL career games → pulled toward bench minutes
    base_min = wc * a.MIN[pid] + (1 - wc) * min(CRED_MPG, a.MIN[pid])  # short history can lose minutes, never gain them
    mpg = base_min + beta[0] + x @ beta[1:]
    # per-season arrays
    gp = np.array([A[s].GP.get(pid, 0) for s in ins3], float)
    mn = np.array([A[s].MIN.get(pid, 0) for s in ins3], float)
    poss = np.array([A[s].POSS.get(pid, 0) for s in ins3], float)
    pace = np.array([A[s].PACE.get(pid, 0) for s in ins3], float)
    tot = {st: np.array([BT[s][st].get(pid, 0) if s in BT else 0 for s in ins3], float) for st in STATS}
    k = np.arange(len(ins3), dtype=float)
    w3 = 3.0 ** k * gp * mn
    pace_p = (pace * w3).sum() / w3.sum()
    poss_g = mpg * pace_p / 48

    def rate(st, r):
        w = float(r) ** k
        return 75 * (tot[st] * w).sum() / (poss * w).sum()

    # usage (stayers only)
    teams, team_of = roster(target)
    t_new = team_of.get(pid)
    stayed = t_new is not None and t_new == a.TEAM_ABBREVIATION.get(pid) if hasattr(a.TEAM_ABBREVIATION, "get") else False
    u_base = usage_for(target).get(pid, a.USG_PCT[pid]) if stayed else a.USG_PCT[pid]  # re-split (stayed) or own (moved)
    # age / usage level / moved adjustment (usage2.py): older and high-usage players lose share, more so after a move
    if USE_USG_ADJ:
        cf = USG_COEF["to_2026-27" if target == "2026-27" else "to_2025-26"]
        age_now = a.AGE[pid] + gap
        ab = int(np.searchsorted([24, 28, 31, 34], age_now, side="right"))
        lvl, mv = a.USG_PCT[pid] - 0.20, 0.0 if stayed else 1.0
        u_base += cf[0] + (cf[ab] if ab > 0 else 0.0) + cf[5] * lvl + cf[6] * mv + cf[7] * mv * lvl
    ur = max(u_base, 0.05) / a.USG_PCT[pid]
    r75 = {"fga": rate("fga", 2) * ur ** 0.5, "fta": rate("fta", 2) * ur ** 0.5, "ast": rate("ast", 5),
           "stl": rate("stl", 1), "blk": rate("blk", 5), "tov": rate("tov", 2) * ur, "oreb": rate("oreb", 2),
           "dreb": rate("dreb", 2)}
    g_dshift = 0.0
    if USE_DREB_TM:
        d0 = A[SEAS[ti - 1]].DREB_PCT.get(pid, a.DREB_PCT[pid]) if SEAS[ti - 1] in A else a.DREB_PCT[pid]
        g_dshift = dreb_shift(pid, target)
        if d0 and d0 > 0:
            r75["dreb"] *= max(0.3, (d0 + g_dshift) / d0)
    # zones
    A5 = np.array([[ZS[s]["fga"][z].get(pid, 0) if z in ZS[s]["fga"] else 0 for z in ZONES] for s in ins5], float)
    M5 = np.array([[ZS[s]["fgm"][z].get(pid, 0) if z in ZS[s]["fgm"] else 0 for z in ZONES] for s in ins5], float)
    zt = A5.sum(1)
    wz = np.where(zt >= 100, zt, np.where(zt > 0, zt * 0.25, 0)) * 5.0 ** np.arange(len(ins5))
    share = (A5 / np.where(zt > 0, zt, 1)[:, None] * wz[:, None]).sum(0) / wz.sum()
    allA = np.stack([ZS[s]["fga"][ZONES].sum() for s in ins3]).sum(0)
    allM = np.stack([ZS[s]["fgm"][ZONES].sum() for s in ins3]).sum(0)
    a3, m3 = A5[-3:].sum(0), M5[-3:].sum(0)
    # paint: his own makes / attempts over 3 seasons (3 beat 1)
    pct = np.where(a3 > 0, m3 / np.where(a3 > 0, a3, 1), allM / allA - 0.075)  # never shot there: below the league rate (share ≈ 0)
    # rim: his own rate, weighted against what players his height and assisted share finish at
    # (half weight at 70 attempts, so a high-volume finisher is almost all his own number)
    ast2 = np.nanmean([AST2[s].get(pid, np.nan) for s in ins3])
    ht = HT.get(pid)
    if ht is not None and not np.isnan(ast2):
        rim_ht = RIM_PRIOR[0] + RIM_PRIOR[1] * (ht - 78) + RIM_PRIOR[2] * (ast2 - 0.6)
        pct[0] = (m3[0] + K_RIM * rim_ht) / (a3[0] + K_RIM)
    # mid-range: few players take many, so the evidence is a 5-season average, with a bracket on top like 3s —
    #   38–45% his own number; below 38% pulled up toward 38% only as far as volume earns it (none at ≤100 mid
    #   attempts over the 5 seasons — a guy who rarely takes it and misses is a real non-shooter — 65% of the gap at 300+);
    #   above 45% pulled toward 45% only on thin evidence (halfway at ≤100, none at 300+)
    a5m, m5m = A5[:, 2].sum(), M5[:, 2].sum()
    if a5m > 0:
        pct[2] = m5m / a5m
        earned = min(max((a5m - 100) / 200, 0), 1)
        if pct[2] < MID_FLOOR:
            pct[2] += MID_UP * earned * (MID_FLOOR - pct[2])
        elif pct[2] > MID_CAP:
            pct[2] -= MID_DOWN * (1 - earned) * (pct[2] - MID_CAP)
    # 3-point %, on his combined 3s over 3 seasons (the corner / above-break split is kept):
    #   below 34%: pulled up toward 34% only as far as volume earns it (none under 50 att/season, 70% of the gap at 250+)
    #   above 38%: pulled back toward 38% only when the volume is thin (halfway at 50 att/season, none at 250+)
    #   34–38%: his own number
    A3t, M3t = a3[3] + a3[4], m3[3] + m3[4]
    seasons3 = max(1, int(sum(1 for i in range(1, 4) if A5[-i][3] + A5[-i][4] > 0)))
    if A3t > 0 and share[3] + share[4] > 0:
        r3, ayr = M3t / A3t, A3t / seasons3
        if r3 < THREE_FLOOR:
            t3 = r3 + THREE_UP * min(max((ayr - 50) / 200, 0), 1) * (THREE_FLOOR - r3)
        elif r3 > THREE_CAP:
            # volume is the evidence: halfway back to 38% at 50 att/yr, nothing at 250+
            t3 = r3 - THREE_DOWN * (1 - min(max((ayr - 50) / 200, 0), 1)) * (r3 - THREE_CAP)
        else:
            t3 = r3
        blended = (pct[3] * share[3] + pct[4] * share[4]) / (share[3] + share[4])
        if blended > 0:
            pct[3:] = pct[3:] * (t3 / blended)
    fta3, ftm3 = tot["fta"].sum(), tot["ftm"].sum()
    # FT%: his own makes / attempts over 3 seasons, no pull (3 beat 1, 2, 4 and 5)
    # never been to the line in 3 seasons → what rarely-fouled players his height shoot ('21–'25, under 30 FTA in a season)
    ftp = ftm3 / fta3 if fta3 > 0 else NOFT_BY_HT[int(np.searchsorted([75, 78, 81, 83], HT.get(pid, 79), side="right"))]
    # per game
    g = {k_: poss_g / 75 * v for k_, v in r75.items()}
    att = g["fga"] * share
    mk = att * pct
    g["fgm"], g["fg3m"], g["fg3a"] = mk.sum(), mk[3:].sum(), att[3:].sum()
    g["ftm"] = g["fta"] * ftp
    g["pts"] = (mk * VAL).sum() + g["ftm"]
    g["mpg"], g["pace"], g["poss"] = mpg, pace_p, poss_g
    blk_exp = sum(float(np.array([ZS[s_]["fga"][z].get(pid, 0) if z in ZS[s_]["fga"] else 0 for z in ZONES]) @ BLK_RATE) for s_ in ins3)
    blk_act = sum(float(BLKA[s_].get(pid, 0)) for s_ in ins3)
    g["blkd_factor"] = (blk_act + 15) / (blk_exp + 15)
    g["blkd"] = float(att @ BLK_RATE * g["blkd_factor"]) if USE_BLKD else 0.0
    g["dreb_shift"] = g_dshift
    g["fp"] = (g["pts"] * SCORING["pts"] + (g["fga"] - g["fgm"]) * SCORING["fgx"] + g["fg3m"] * SCORING["fg3m"]
               + (g["fta"] - g["ftm"]) * SCORING["ftx"] + g["oreb"] * SCORING["oreb"] + g["dreb"] * SCORING["dreb"]
               + g["ast"] * SCORING["ast"] + g["stl"] * SCORING["stl"] + g["blk"] * SCORING["blk"] + g["tov"] * SCORING["tov"]
               + g["blkd"] * SCORING["blkd"])
    g["base"], g["gap"], g["stayed"], g["team"], g["age"] = base, gap, stayed, t_new, a.AGE[pid] + gap + 1
    g["share"], g["zone_pct"], g["zone_att"] = list(share), list(pct), list(att)
    g["usg"] = float(a.USG_PCT[pid] * ur)
    g["epm_flag"] = None
    if target == "2026-27":
        k = name_key(a.PLAYER_NAME[pid])
        if k in EPM_BAD and g["fp"] > 0:
            # bad player → teams trying to win cut his minutes: take ~EPM_PENALTY_FP off, through minutes (all counting stats scale)
            sc = max(0.0, g["fp"] - EPM_PENALTY_FP) / g["fp"]
            for kk in ["fga", "fta", "ast", "stl", "blk", "tov", "oreb", "dreb", "fgm", "fg3m", "fg3a", "ftm", "pts", "fp", "mpg", "poss", "blkd"]:
                g[kk] *= sc
            g["epm_flag"] = EPM_BAD[k]
    return g


def actual(pid, season):
    """per-game line in a season (box score; own shots blocked from season game logs), with fantasy points"""
    if season not in BG:
        return None
    d = BG[season][BG[season].player_id == pid]
    if d.empty:
        return None
    n = d.game_id.nunique()
    g = {st: d[st].sum() / n for st in STATS}
    g["mpg"], g["gp"] = d.m.sum() / n, n
    g["blkd"] = float(BLKA.get(season, pd.Series(dtype=float)).get(pid, 0)) / n if USE_BLKD else 0.0
    g["fp"] = (g["blkd"] * SCORING["blkd"] + g["pts"] + (g["fga"] - g["fgm"]) * SCORING["fgx"] + g["fg3m"] * SCORING["fg3m"] + (g["fta"] - g["ftm"]) * SCORING["ftx"]
               + g["oreb"] * SCORING["oreb"] + g["dreb"] * SCORING["dreb"] + g["ast"] + g["stl"] * SCORING["stl"]
               + g["blk"] * SCORING["blk"] + g["tov"] * SCORING["tov"])
    return g


def pid_of(name):
    for s in reversed(SEAS):
        m = A[s].index[A[s].PLAYER_NAME == name]
        if len(m):
            return int(m[0])
    raise KeyError(name)


def line(g):
    return (f"MPG {g['mpg']:4.1f}  PTS {g['pts']:4.1f}  REB {g['oreb'] + g['dreb']:4.1f}  AST {g['ast']:4.1f}  "
            f"STL {g['stl']:.1f}  BLK {g['blk']:.1f}  TOV {g['tov']:.1f}  3PM {g['fg3m']:.1f}  FP {g['fp']:5.1f}")


if __name__ == "__main__":
    print("=== Validation: projecting '26 (inputs '23–'25) ===")
    for n in ["Brandon Miller", "Brandon Ingram"]:
        p = pid_of(n)
        g = project(p, "2025-26")
        print(f"\n{n}  (base season {g['base']}, '25 GP {A['2024-25'].GP.get(p, 0)}, team '26 {g['team']}, stayed {g['stayed']})")
        for s in ["2022-23", "2023-24", "2024-25"]:
            a = actual(p, s)
            if a:
                print(f"   actual '{s[-2:]} ({a['gp']:>2} GP)  {line(a)}")
        print(f"   PROJECTED '26        {line(g)}")
        a = actual(p, "2025-26")
        print(f"   actual '26 ({a['gp']:>2} GP)  {line(a)}")

    print("\n\n=== 2026-27 for the top-50 superset players who missed '26 ===")
    t = pd.read_csv(f"{R}top50_superset_23_26.csv")
    miss = t[t["rk'26"].isna()]
    for n in miss.name:
        try:
            p = pid_of(n)
        except KeyError:
            continue
        gp26 = A["2025-26"].GP.get(p, 0)
        g = project(p, "2026-27")
        a25 = actual(p, "2024-25")
        if g is None:
            print(f"  {n:<24} no input seasons")
            continue
        print(f"  {n:<24} '26 GP {int(gp26):>2} | base {g['base'][-5:]} age {g['age']:.0f} {g['team']}\n"
              f"      '25 actual {line(a25) if a25 else '—'}\n      '27 proj   {line(g)}")
