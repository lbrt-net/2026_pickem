"""Back-test weekly win probability on the 2025-26 season — offline (nba-pipeline data), no site needed.

    python3 scripts/backtest_winprob.py [--leagues 6] [--runs 400]

Made-up 10-team leagues: 5 player starters (drafted from the real pool in random tiers, so many kinds of players get
tested) + 1 NBA team starter, scored with the current rules. Every Mon–Sun week of 2025-26; four moments a week (before
Monday, after Tuesday, after Thursday, after Saturday); each prediction uses only what was known then. Every version is
judged on the same leagues, matchups and moments:

  base       chance to play = his share of his team's last 20 games; every opponent the same
  injuries   perfect injury knowledge: we know which remaining games he plays
  +opp D×P   … and each remaining game scaled by the opponent's defense so far (defensive rating × pace)
  +opp FPA   … or by the fantasy points the opponent has allowed per game so far
  old        the old method: logistic on the projected-total gap

Prints Brier scores (lower = better; always saying 50% scores 0.25) and calibration; writes WINPROB.md.
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.fantasy_2026_27 import scoring  # noqa: E402
from backend.fantasy_2026_27.lineup import expected_best  # noqa: E402
from backend.fantasy_2026_27.winprob import win_prob  # noqa: E402

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
TEAM_FULL = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "derived" / "projections_2026_27" / "inputs" / "team_full.parquet"
PLAYERS, TEAMS = 5, 10
CHECKPOINTS = {"before Mon": 0, "after Tue": 2, "after Thu": 4, "after Sat": 6}
VERSIONS = ["base", "injuries", "+opp D×P", "+opp FPA"]
FORMS = [0.08, 0.12, 0.16, 0.20, 0.25]  # --form: week-form spreads tested on top of perfect injury knowledge
THIN = 10  # fewer games than this this season → top up with last season's


def logs(season):
    rs = json.load(open(RAW / "game_logs" / f"{season}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    g = pd.DataFrame(rs["rowSet"], columns=rs["headers"])
    g["date"] = pd.to_datetime(g.GAME_DATE).dt.date
    g["opp"] = g.MATCHUP.str.split().str[-1]
    g["fp"] = [scoring.score_game(scoring.DEFAULT["player"], scoring.player_line({
        "pts": r.PTS, "fgm": r.FGM, "fga": r.FGA, "fg3m": r.FG3M, "ftm": r.FTM, "fta": r.FTA, "oreb": r.OREB,
        "dreb": r.DREB, "ast": r.AST, "stl": r.STL, "blk": r.BLK, "tov": r.TOV}))["total"] for r in g.itertuples()]
    return g


def team_games():
    t = pd.read_parquet(TEAM_FULL)
    t["date"] = pd.to_datetime(t.GAME_DATE).dt.date
    t["opp"] = t.MATCHUP.str.split().str[-1]
    t["fp"] = [scoring.score_game(scoring.DEFAULT["team"], scoring.team_line(r.PTS, r.OPP_PTS, {
        k: v for k, v in {"fb_pts_allowed": r.OPP_PTS_FB, "paint_pts_allowed": r.OPP_PTS_PAINT, "tov_forced": r.OPP_TOV,
                          "dreb_margin": r.DREB_MARGIN, "shot_clock_forced": r.SC_FORCED}.items() if pd.notna(v)}))["total"]
               for r in t.itertuples()]
    t["dp"] = t.DEF_RATING * t.PACE
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leagues", type=int, default=6)
    ap.add_argument("--runs", type=int, default=400)
    ap.add_argument("--form", action="store_true", help="compare week-form spreads (on top of injury knowledge) instead")
    ap.add_argument("--dump", help="also write every prediction (version, moment, p, won, lead, projected gap, games left) to this JSON file")
    args = ap.parse_args()
    versions = (["injuries"] + [f"form {f}" for f in FORMS]) if args.form else VERSIONS

    cur, prev = logs("2025-26"), logs("2024-25")
    T = team_games()
    Tc, Tp = T[T.season == "2025-26"], T[T.season == "2024-25"]
    played = cur[cur.MIN > 0]
    prev_scores = prev[prev.MIN > 0].groupby("PLAYER_ID").fp.apply(list).to_dict()
    pgames = played.groupby("PLAYER_ID")[["date", "fp", "TEAM_ABBREVIATION", "GAME_ID"]].apply(
        lambda d: list(zip(d.date, d.fp, d.TEAM_ABBREVIATION, d.GAME_ID))).to_dict()
    team_sched = Tc.sort_values("date").groupby("TEAM_ABBREVIATION")[["date", "opp", "GAME_ID", "fp"]].apply(
        lambda d: list(zip(d.date, d.opp, d.GAME_ID, d.fp))).to_dict()
    prev_team_scores = Tp.groupby("TEAM_ABBREVIATION").fp.apply(list).to_dict()
    # fantasy points each team allowed per game (players' FP against it)
    fpa = played.groupby(["opp", "GAME_ID", "date"]).fp.sum().reset_index()
    fpa_prev = prev[prev.MIN > 0].groupby(["opp", "GAME_ID"]).fp.sum().groupby("opp").mean().to_dict()
    dp_prev = Tp.groupby("TEAM_ABBREVIATION").dp.mean().to_dict()

    @lru_cache(maxsize=None)
    def opp_factor(kind, team, cutoff):
        """How generous `team`'s defense has been through `cutoff`, vs the league (1 = average); thin → last season."""
        if kind == "D×P":
            rows = Tc[Tc.date <= cutoff]
            mine = rows[rows.TEAM_ABBREVIATION == team].dp
            league, prior, lg_prior = rows.dp.mean(), dp_prev.get(team), sum(dp_prev.values()) / len(dp_prev)
        else:
            rows = fpa[fpa.date <= cutoff]
            mine = rows[rows.opp == team].fp
            league, prior, lg_prior = rows.fp.mean(), fpa_prev.get(team), sum(fpa_prev.values()) / len(fpa_prev)
        n = len(mine)
        now = (mine.mean() / league) if n and league == league else 1.0
        before = (prior / lg_prior) if prior else 1.0
        w = min(n, 20) / 20  # lean on last season until ~20 games in
        return w * now + (1 - w) * before

    def player_state(pid, wk, upto, version):
        games = pgames.get(pid, [])
        end = wk + timedelta(days=6)
        cutoff = wk + timedelta(days=upto - 1) if upto else wk - timedelta(days=1)
        hist = [s for d, s, _, _ in games if d <= cutoff]
        if len(hist) < THIN:
            hist = hist + prev_scores.get(pid, [])
        mine = [s for d, s, _, _ in games if wk <= d <= cutoff]
        teams_wk = [t for d, _, t, _ in games if wk <= d <= end] or [t for d, _, t, _ in games if d <= cutoff][-1:]
        team = teams_wk[0] if teams_wk else None
        played_ids = {g for _, _, _, g in games}
        remaining = [(d, o, g) for d, o, g, _ in team_sched.get(team, []) if cutoff < d <= end]
        recent = [g for d, _, g, _ in team_sched.get(team, []) if d <= cutoff][-20:]
        p_recent = sum(1 for g in recent if g in played_ids) / len(recent) if len(recent) >= 5 else 0.85
        out = []
        for d, o, g in remaining:
            p = p_recent if version == "base" else (1.0 if g in played_ids else 0.0)
            f = opp_factor("D×P", o, cutoff) if version == "+opp D×P" else opp_factor("FPA", o, cutoff) if version == "+opp FPA" else 1.0
            out.append((p, f))
        return {"current": max(mine) if mine else None, "games": out, "scores": hist,
                "actual": max([s for d, s, _, _ in games if wk <= d <= end], default=0.0)}

    def team_state(team, wk, upto):
        sched = team_sched.get(team, [])
        end = wk + timedelta(days=6)
        cutoff = wk + timedelta(days=upto - 1) if upto else wk - timedelta(days=1)
        hist = [s for d, _, _, s in sched if d <= cutoff]
        if len(hist) < THIN:
            hist = hist + prev_team_scores.get(team, [])
        mine = [s for d, _, _, s in sched if wk <= d <= cutoff]
        return {"current": max(mine) if mine else None, "games": [(1.0, 1.0) for d, _, _, _ in sched if cutoff < d <= end],
                "scores": hist, "actual": max([s for d, _, _, s in sched if wk <= d <= end], default=0.0)}

    prior = {p: sum(v) / len(v) for p, v in prev_scores.items() if len(v) >= 20}
    pool = sorted(prior, key=lambda p: -prior[p])[:TEAMS * PLAYERS * 2]
    nba = sorted(team_sched)
    first = min(played.date)
    monday, weeks = first - timedelta(days=first.weekday()), []
    while monday + timedelta(days=6) <= max(played.date):
        weeks.append(monday)
        monday += timedelta(days=7)

    rnd = random.Random(7)
    preds = defaultdict(list)  # (version, checkpoint) -> [(p, won)]
    records = []  # for --dump
    for lg in range(args.leagues):
        order = []
        for i in range(0, len(pool), TEAMS):
            tier = pool[i:i + TEAMS]
            rnd.shuffle(tier)
            order += tier
        rosters = [order[i::TEAMS][:PLAYERS] for i in range(TEAMS)]
        teams_pick = rnd.sample(nba, TEAMS)
        for wk in weeks:
            pairs = list(range(TEAMS))
            rnd.shuffle(pairs)
            for a, b in zip(pairs[::2], pairs[1::2]):
                act = lambda i: sum(player_state(p, wk, 7, "base")["actual"] for p in rosters[i]) + team_state(teams_pick[i], wk, 7)["actual"]
                ta, tb = act(a), act(b)
                if ta == tb:
                    continue
                won = ta > tb
                for name, day in CHECKPOINTS.items():
                    seed = rnd.randrange(10 ** 9)
                    for v in versions:
                        base_v, form = ("injuries", float(v.split()[1])) if v.startswith("form") else (v, 0.0)
                        sa = [player_state(p, wk, day, base_v) for p in rosters[a]] + [team_state(teams_pick[a], wk, day)]
                        sb = [player_state(p, wk, day, base_v) for p in rosters[b]] + [team_state(teams_pick[b], wk, day)]
                        preds[(v, name)].append((win_prob(sa, sb, runs=args.runs, seed=seed, form_sd=form), won))
                    sa = [player_state(p, wk, day, "base") for p in rosters[a]] + [team_state(teams_pick[a], wk, day)]
                    sb = [player_state(p, wk, day, "base") for p in rosters[b]] + [team_state(teams_pick[b], wk, day)]
                    proj = lambda ss: sum((expected_best(s["scores"], round(sum(p for p, _ in s["games"])), s["current"]) or s["current"] or 0) for s in ss)
                    p_old = 1 / (1 + math.exp(-(proj(sa) - proj(sb)) / 20))
                    preds[("old", name)].append((p_old, won))
                    if args.dump:
                        lead = sum(s["current"] or 0 for s in sa) - sum(s["current"] or 0 for s in sb)
                        left = sum(len(s["games"]) for s in sa) - sum(len(s["games"]) for s in sb)
                        for v in versions + ["old"]:
                            records.append({"v": v, "moment": name, "p": round(preds[(v, name)][-1][0], 4), "won": won,
                                            "lead": round(lead, 1), "gap": round(proj(sa) - proj(sb), 1), "left_diff": left})
        print(f"league {lg + 1}/{args.leagues}", file=sys.stderr)

    brier = lambda rows: sum((p - w) ** 2 for p, w in rows) / len(rows)
    allv = versions + ["old"]
    lines = ["# Win probability back-test (2025-26)", "",
             f"{args.leagues} made-up {TEAMS}-team leagues × {len(weeks)} weeks; {PLAYERS} player starters + 1 NBA team each; "
             f"{args.runs} runs per prediction. Brier = average squared miss (lower is better; always 50% = 0.25).", "",
             "| moment | " + " | ".join(allv) + " |", "|---" * (len(allv) + 1) + "|"]
    for name in CHECKPOINTS:
        lines.append(f"| {name} | " + " | ".join(f"{brier(preds[(v, name)]):.4f}" for v in allv) + " |")
    lines.append("| **all** | " + " | ".join(f"**{brier([r for n in CHECKPOINTS for r in preds[(v, n)]]):.4f}**" for v in allv) + " |")
    lines += ["", "Calibration (all moments) — of the matchups given about X%, how many were won:", "",
              "| predicted | " + " | ".join(allv) + " |", "|---" * (len(allv) + 1) + "|"]
    for lo in range(0, 100, 10):
        cells = []
        for v in allv:
            rows = [r for n in CHECKPOINTS for r in preds[(v, n)] if lo <= r[0] * 100 < lo + 10 or (lo == 90 and r[0] == 1)]
            cells.append(f"{100 * sum(w for _, w in rows) / len(rows):.0f}% ({len(rows)})" if rows else "—")
        lines.append(f"| {lo}–{lo + 10}% | " + " | ".join(cells) + " |")
    if args.dump:
        Path(args.dump).write_text(json.dumps(records))
    out = "\n".join(lines)
    print(out)
    Path(__file__).resolve().parent.parent.joinpath("WINPROB.md").write_text(out + "\n")


if __name__ == "__main__":
    main()
