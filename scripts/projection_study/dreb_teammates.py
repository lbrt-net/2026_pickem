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
        return (d * m).sum() / m.sum()

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
                        old=strength(roster0[t0], p), new=strength(new_roster[t1], p)))
    return pd.DataFrame(out)


SE = list(BOX)
train = pd.concat(rows(a, b) for a, b in zip(SE[:3], SE[1:4])).reset_index(drop=True)
test = rows(SE[3], SE[4])
mean = train.d0.mean()


def X(df):
    return np.column_stack([np.ones(len(df)), df.new - df.old, df.d0 - mean])


beta, *_ = np.linalg.lstsq(X(train), (train.d1 - train.d0).to_numpy(), rcond=None)
beta_r, *_ = np.linalg.lstsq(X(train)[:, [0, 2]], (train.d1 - train.d0).to_numpy(), rcond=None)
print(f"Train {len(train)} ({train.moved.sum()} movers), test '25→'26 {len(test)} ({test.moved.sum()} movers)")
print(f"  fit: change = {beta[0]:+.4f} + {beta[1]:.2f} x (teammate strength change) {beta[2]:+.2f} x (own DREB% - {mean:.3f})")
print(f"  teammate strength change: movers typical ±{100 * (train[train.moved].new - train[train.moved].old).abs().median():.1f} pts, "
      f"stayers ±{100 * (train[~train.moved].new - train[~train.moved].old).abs().median():.1f}\n")

pooled = pd.concat([train, test])
for lab, df, b, cols in [("test '25→'26", test, None, None)]:
    pass
print(f"DREB% error, % points (mean abs)       {'all':>6}{'stayed':>9}{'moved':>8}")
for lab, pred in [("same as last year", test.d0),
                  ("regression to mean only", test.d0 + X(test)[:, [0, 2]] @ beta_r),
                  ("+ teammate strength", test.d0 + X(test) @ beta)]:
    e = (pred - test.d1).abs() * 100
    print(f"  {lab:<37}{e.mean():6.2f}{e[~test.moved].mean():9.2f}{e[test.moved].mean():8.2f}")

# leave-one-transition-out over all four, for a bigger mover sample
allr = pd.concat([train, test]).reset_index(drop=True)
errs = {k: [] for k in ["same", "reg", "team"]}
mv = []
for tr in allr.tr.unique():
    tr_, te = allr[allr.tr != tr], allr[allr.tr == tr]
    m_ = tr_.d0.mean()
    Xa = lambda df: np.column_stack([np.ones(len(df)), df.new - df.old, df.d0 - m_])  # noqa: E731
    b, *_ = np.linalg.lstsq(Xa(tr_), (tr_.d1 - tr_.d0).to_numpy(), rcond=None)
    br, *_ = np.linalg.lstsq(Xa(tr_)[:, [0, 2]], (tr_.d1 - tr_.d0).to_numpy(), rcond=None)
    errs["same"].append((te.d0 - te.d1).abs())
    errs["reg"].append((te.d0 + Xa(te)[:, [0, 2]] @ br - te.d1).abs())
    errs["team"].append((te.d0 + Xa(te) @ b - te.d1).abs())
    mv.append(te.moved)
mv = pd.concat(mv).to_numpy()
print(f"\nLeave-one-season-out, all 4 transitions ({len(mv)} players, {mv.sum()} movers):")
for k, lab in [("same", "same as last year"), ("reg", "regression to mean only"), ("team", "+ teammate strength")]:
    e = pd.concat(errs[k]).to_numpy() * 100
    print(f"  {lab:<37}{e.mean():6.2f}{e[~mv].mean():9.2f}{e[mv].mean():8.2f}")

print("\nMovers (DREB% prior → model → actual; teammate strength old → new):")
allr["pred"] = allr.d0 + np.column_stack([np.ones(len(allr)), allr.new - allr.old, allr.d0 - mean]) @ beta
for _, x in allr[allr.moved].assign(dd=lambda d: (d.d1 - d.d0).abs()).sort_values("dd", ascending=False).head(12).iterrows():
    print(f"  {x.tr} {x['name']:<24} {x.t0}→{x.t1}  {100 * x.d0:5.1f} → {100 * x.pred:5.1f} → {100 * x.d1:5.1f}   "
          f"teammates {100 * x.old:4.1f} → {100 * x.new:4.1f}")
