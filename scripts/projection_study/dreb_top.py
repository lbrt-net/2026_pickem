"""DREB%: does the rebounding strength of his teammates drive his share?

Teammate strength = minutes-weighted mean of teammates' prior-year DREB% (excluding him).
  old: his prior team (players with 1+ game for it in the prior season), prior-year DREB% and MPG.
  new: his target-season opening team (first-game team), teammates' prior-year DREB% and MPG
       (no prior data: league median of players under 15 MPG, 15 MPG).
Model: DREB%_1 - DREB%_0 = a + b*(new - old) + c*(DREB%_0 - mean).
Fit '22→'23 … '24→'25; test '25→'26.  Players: 60+ GP for their team both seasons.
"""
import contextlib
import io
import runpy

import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
with contextlib.redirect_stdout(io.StringIO()):
    RB = runpy.run_path(S + "reb_resplit.py", run_name="lib")
tab, box, BOX = RB["tab"], RB["box"], RB["BOX"]


def rows(s0, s1):
    a0, a1 = tab("player_advanced", s0).set_index("PLAYER_ID"), tab("player_advanced", s1).set_index("PLAYER_ID")
    b0, b1 = box(s0), box(s1)
    opening = b1.sort_values("game_id").groupby("player_id").team_tricode.first()
    gp0 = b0.groupby(["player_id", "team_tricode"]).game_id.nunique()
    gp1 = b1.groupby(["player_id", "team_tricode"]).game_id.nunique()
    main0 = gp0.reset_index().sort_values("game_id").groupby("player_id").last()
    roster0 = b0.groupby("team_tricode").player_id.apply(set)
    low = a0[a0.MIN < 15].DREB_PCT.median()

    def strength(team_players, me):
        ids = [p for p in team_players if p != me]
        d = np.array([a0.DREB_PCT.get(p, low) for p in ids], float)
        m = np.array([a0.MIN.get(p, 15.0) * min(a0.GP.get(p, 30), 82) for p in ids], float)
        rot = np.array([a0.MIN.get(p, 0.0) >= 15 for p in ids])
        top = np.sort(d[rot])[::-1] if rot.any() else np.array([low, low])
        if len(top) < 2:
            top = np.append(top, low)
        return {"avg": (d * m).sum() / m.sum(), "top1": top[0], "top2": top[:2].mean()}

    new_roster = opening.groupby(opening).apply(lambda s: set(s.index))
    out = []
    for p, t1 in opening.items():
        if p not in main0.index or p not in a0.index or p not in a1.index:
            continue
        t0, g0 = main0.loc[p, "team_tricode"], main0.loc[p, "game_id"]
        if g0 < 60 or gp1.get((p, t1), 0) < 60:
            continue
        out.append(dict(tr=f"'{s0[-2:]}→'{s1[-2:]}", name=a1.PLAYER_NAME[p], t0=t0, t1=t1, moved=t0 != t1,
                        d0=a0.DREB_PCT[p], d1=a1.DREB_PCT[p],
                        **{f"old_{k}": v for k, v in strength(roster0[t0], p).items()},
                        **{f"new_{k}": v for k, v in strength(new_roster[t1], p).items()}))
    return pd.DataFrame(out)



SE = list(BOX)
allr = pd.concat(rows(a, b) for a, b in zip(SE, SE[1:])).reset_index(drop=True)
print(f"{len(allr)} player-seasons, {allr.moved.sum()} movers. Leave-one-season-out, DREB% error (% points):")
print(f"  {'teammate measure':<34}{'all':>6}{'stayed':>9}{'moved':>8}   slope")
for meas in [None, "avg", "top1", "top2"]:
    errs, mv, slopes = [], [], []
    for tr in allr.tr.unique():
        a, t = allr[allr.tr != tr], allr[allr.tr == tr]
        m_ = a.d0.mean()
        def X(df):
            cols = [np.ones(len(df)), df.d0 - m_]
            if meas: cols.append(df[f"new_{meas}"] - df[f"old_{meas}"])
            return np.column_stack(cols)
        b, *_ = np.linalg.lstsq(X(a), (a.d1 - a.d0).to_numpy(), rcond=None)
        errs.append((t.d0 + X(t) @ b - t.d1).abs()); mv.append(t.moved)
        if meas: slopes.append(b[2])
    e = pd.concat(errs).to_numpy() * 100; mv_ = pd.concat(mv).to_numpy()
    lab = {None: "none (regression only)", "avg": "minutes-weighted average", "top1": "top teammate rebounder", "top2": "average of top 2"}[meas]
    print(f"  {lab:<34}{e.mean():6.2f}{e[~mv_].mean():9.2f}{e[mv_].mean():8.2f}   {np.mean(slopes) if slopes else float('nan'):+.2f}")
print(f"  {'same as last year':<34}{100*(allr.d0-allr.d1).abs().mean():6.2f}{100*(allr.d0-allr.d1)[~allr.moved].abs().mean():9.2f}{100*(allr.d0-allr.d1)[allr.moved].abs().mean():8.2f}")
m_ = allr.d0.mean()
Xf = np.column_stack([np.ones(len(allr)), allr.d0 - m_, allr.new_top1 - allr.old_top1])
b, *_ = np.linalg.lstsq(Xf, (allr.d1 - allr.d0).to_numpy(), rcond=None)
allr["pred"] = allr.d0 + Xf @ b
print("\nMovers, top-teammate version (DREB% prior → model → actual; top teammate old → new):")
for _, x in allr[allr.moved].assign(dd=lambda d: (d.d1 - d.d0).abs()).sort_values("dd", ascending=False).head(10).iterrows():
    print(f"  {x.tr} {x['name']:<24} {x.t0}→{x.t1}  {100*x.d0:5.1f} → {100*x.pred:5.1f} → {100*x.d1:5.1f}   top teammate {100*x.old_top1:4.1f} → {100*x.new_top1:4.1f}")
