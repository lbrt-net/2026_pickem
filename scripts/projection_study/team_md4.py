"""Writes a clean TEAM_SCORING.md around the current scoring (draft 4). Data: team_draft4.json, team_timeline_*,
team_candidates.csv, violation_types.json, team_full.parquet, draft_guide.json."""
import json
import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
J = json.load(open(S + "team_draft4.json"))
r, hit = J["res"]["draft 4"], J["hit"]
DG = json.load(open(S + "draft_guide.json"))
TL = pd.read_parquet(S + "team_timeline_games.parquet")
TM = json.load(open(S + "team_timeline_meta.json"))
SPARK = open(S + "team_timeline.txt").read()
C = pd.read_csv(S + "team_candidates.csv")
VT = json.load(open(S + "violation_types.json"))
F = pd.read_parquet(S + "team_full.parquet")
F26 = F[F.season == "2025-26"]
dr = (F26.DEF_RATING * F26.POSS).groupby(F26.TEAM_ABBREVIATION).sum() / F26.POSS.groupby(F26.TEAM_ABBREVIATION).sum()
wb = TL.groupby(["TEAM_ABBREVIATION", "week"]).score.max()
T = pd.DataFrame({"week": wb.groupby(level=0).mean(), "big": wb.groupby(level=0).apply(lambda s: (s >= 30).mean()),
                  "zero": TL.groupby("TEAM_ABBREVIATION").score.apply(lambda s: (s <= 0).mean()), "best": TL.groupby("TEAM_ABBREVIATION").score.max(),
                  "u100": TL.groupby("TEAM_ABBREVIATION").OPP_PTS.apply(lambda s: (s < 100).mean()), "dr": dr}).sort_values("week", ascending=False)
L = []
w = L.append
w("# TEAM scoring\n")
w("Every fantasy roster has one **TEAM** spot: you draft a whole NBA team, like a defense in fantasy football. Players "
  "already score for what they do (points, rebounds, assists, steals, blocks). **TEAM is where a team's defense shows "
  "up.** Seasons are named by the year they end ('26 = 2025-26). Basic box-score stats only this year.\n")
w("## The scoring (current: draft 6)\n")
w("Per game:\n")
w("| What | Points | Games it happens in ('23–'26) |")
w("|---|---|---|")
rows = [("Every 5 points the opponent finishes under 125", "+2 each", hit["Points under 125 (+2 per 5)"]),
        ("Hold them under 100", "+10", hit["Under 100 (+10)"]),
        ("Every shot clock violation forced", "+2 each", hit["Shot clock violations forced (+2 each)"]),
        ("Hold them to single-digit fast-break points", "+5", hit["Single-digit fast-break pts (+5)"]),
        ("Hold them under 30 points in the paint", "+10", hit["Under 30 paint pts (+10)"]),
        ("Force 20+ turnovers", "+10", hit["20+ turnovers forced (+10)"]),
        ("Win the defensive glass by 10+ (our defensive rebounds minus theirs)", "+5", r["hit_glass"])]
for a, b, c in rows:
    w(f"| {a} | {b} | {100 * c:.0f}% |")
w("")
w("**Weekly score = the team's best game of the week**, the same as players.\n")
w("Example: hold a team to 96 with one shot clock violation and 7 fast-break points → 10 (29 under 125 = five steps of 5) "
  "+ 10 (under 100) + 2 (shot clock) + 5 (fast break) = **27**.\n")
w("The numbers are small on purpose — it's the gap between TEAMs that matters, and that gap is sized against the player "
  "spots (below).\n")
w("## Why this shape\n")
w("- **A bread and butter that pays most games**: +2 for every 5 points under 125. The score is on the screen, and points allowed is "
  "the clearest sign of a good defense — the teams that allow the fewest points are the teams with the best defensive "
  "ratings (0.87 out of 1, '23–'26).")
w("- **A line to root for late in a game**: under 100. Rare, and worth a lot.")
w("- **Moments to cheer one at a time**: every shot clock violation forced.")
w("- **Bonuses that don't come every week**, even for good defenses: fast break, paint, turnovers, glass.")
w(f"- **It follows real defense**: a team's average weekly score lines up with its defensive rating at {r['corr']:.2f} and "
  f"repeats next season at {r['yoy']:.2f}, so a TEAM can be drafted like a player.\n")
ZL = TL.groupby("TEAM_ABBREVIATION").score.apply(lambda s: (s <= 0).mean())
WZ = (TL.groupby(["TEAM_ABBREVIATION", "week"]).score.max() <= 0).mean()
w(f"Where a weekly score comes from: points under 125 {100 * r['share']['Points under 125 (+2 per 5)']:.0f}%, shot clock violations "
  f"{100 * r['share']['Shot clock violations forced (+2 each)']:.0f}%, under 100 "
  f"{100 * r['share']['Under 100 (+10)']:.0f}%, the four bonuses "
  f"{100 * (r['share']['Single-digit fast-break pts (+5)'] + r['share']['Under 30 paint pts (+10)'] + r['share']['20+ turnovers forced (+10)'] + r['share']['Glass']):.0f}%. "
  f"A weekly score averages **{r['week']:.0f}**, give or take {r['sd']:.0f}.\n")
w("## Last season (2025-26)\n")
w("| # | Team | Weekly score | Weeks of 30+ | Games at 0 | Best game | Held under 100 | Defensive rating |")
w("|---|---|---|---|---|---|---|---|")
for i, (k, x) in enumerate(T.iterrows()):
    w(f"| {i + 1} | {k} | **{x.week:.1f}** | {100 * x.big:.0f}% | {100 * x.zero:.0f}% | {x.best:.0f} | {100 * x.u100:.0f}% | {x.dr:.1f} |")
w("")
w("Defensive rating = points allowed per 100 possessions (lower is better), for comparison.\n")
w("### Every game, every team\n")
w("One line per team, every game October → March. `|` starts a new fantasy week (21; the All-Star week and the final "
  "are 2-week periods). Each character is one game: `·` = **0**, `▁▂▃▄▅▆▇█` = higher (each step 5 points; `█` = "
  f"35+). Before the line: average weekly score, share of games at 0. {100 * (TL.score <= 0).mean():.0f}% of games score 0, but only {100 * WZ:.1f}% of weeks do.\n")
w("```")
w(SPARK)
w("```\n")
w("## 2026-27 projections\n")
w("Each team's projected weekly score under its real 2026-27 schedule: start from its '26 games, pull its average back "
  "toward the league by the part that doesn't carry over (about 4 in 10 of the gap, measured '23→'24 and '24→'25), and "
  "take the best game for each week's real game count (NBA Cup games filled in, the same as players).\n")
w("| # | Team | Projected weekly | '26 weekly |")
w("|---|---|---|---|")
for i, p in enumerate(r["proj"]):
    w(f"| {i + 1} | {p['team']} | **{p['proj_max']:.1f}** | {p['week26']:.1f} |")
w("")
w("**How valuable a TEAM is**: the average starting TEAM and the best TEAM over the best one left undrafted, next to the "
  "player spots (1 G / 1 F / 1 C; DRAFT_GUIDE.md):\n")
w("| Teams in the league | TEAM avg starter / best | G | F | C | Best C (Jokić) |")
w("|---|---|---|---|---|---|")
for N in ("4", "8", "12"):
    v, pl = r["vor"][N], DG[f"gfc|{N}"]["by_slot"]
    w(f"| {N} | +{v['avg']:.1f} / +{v['best']:.1f} | +{pl['G']['avg_vor']:.1f} | +{pl['F']['avg_vor']:.1f} | +{pl['C']['avg_vor']:.1f} | +{pl['C']['best_vor']:.1f} |")
w("")
w("About as valuable as a guard spot, closer to a center spot in bigger leagues. No rescaling needed.\n")
V = json.load(open(S + "team_value.json"))
w("## What a TEAM is worth in the draft\n")
w(f"One draft board with every player and every NBA team, ranked by value over replacement (projected weekly score minus "
  f"the best one left undrafted at that spot), for the default lineup G / F / C / TEAM. **Players are discounted to the "
  f"{100 * V['avail']:.0f}% of weeks they actually play** ('24–'26, top 100: when a player sits, you start a replacement); "
  f"TEAMs never miss a week. One point a week over replacement is worth about **{100 * V['4']['per_pt']:.1f}% of a weekly win**.\n")
w("| League size | Avg starting TEAM | Avg starting G / F / C | Best TEAM | Jokić | Where the TEAMs go (overall pick, + a week) |")
w("|---|---|---|---|---|---|")
for N in ("4", "8", "12"):
    x = V[N]
    w(f"| {N} teams | +{x['team_avg']:.1f} | +{x['g']:.1f} / +{x['f']:.1f} / +{x['c']:.1f} | +{x['team_best']:.1f} | +{x['jokic']:.1f} | "
      + ", ".join(f"{y['name']} #{y['pick']} (+{y['vor']:.1f})" for y in x["teams"][:6]) + (" …" if len(x["teams"]) > 6 else "") + " |")
w("")
w("- **A TEAM is worth about a forward-to-guard spot**: the average starting TEAM sits just under the average player spot, "
  "and the best TEAM is about a good guard — not half a Jokić.")
w("- **The top four defenses still go early-ish, then TEAMs flatten**: take a top TEAM when it's the best value on the "
  "board, otherwise wait.\n")
w("## How we got here\n")
w("- **Point margin** (the old TEAM scoring): out. It rewards offense as much as defense and made TEAM worth twice a center.")
w("- **Draft 1**: +5 for every line under 120 / 115 / 110 / 105 / 100 / 95 / 90, +1 per turnover forced. Followed defense "
  "well, but too smooth — it paid something every game, nothing to sweat.")
w("- **Draft 2**: big lines (under 100 / 95 / 90) and rare bonuses only. Exciting, but everything was swingy.")
w("- **Draft 3**: one steady category plus the swingy part; tested turnovers forced vs points under 125 as the steady one.")
w("- **Draft 4**: the commissioner's numbers — +1 per point under 125, +10 under 100, +15 more under 90, +5 per time "
  "violation (shot clock, 8-second, 5-second), and the four bonuses. Paint and glass cutoffs adjusted from the first ask "
  "(under 25 paint points happens in 0.5% of games; the glass is our defensive rebounds minus theirs, by 10).")
w("- **Draft 5**: +1 per point under 120, +10 under 100 (no under-90), +2 per shot clock violation (8- and 5-second out).")
w("- **Draft 6** (current, above): TEAMs never miss a game while players miss about 14% of weeks, so TEAM was nerfed: "
  "+2 for every 5 points under 125 (about 0.4 a point). Moving the line (120 → 115 → 110) didn't nerf anything — it "
  "lowers every team equally, so the gap between them stays; only a smaller value per point shrinks it. 20+ turnovers "
  "doubled to +10.\n")
w("## What else we looked at\n")
w("Per game ('23–'26), whether teams' averages follow good defense (0–1), and whether teams repeat it next season (0–1):\n")
w("| Stat | Per game | Follows defense | Repeats | Verdict |")
w("|---|---|---|---|---|")
VERD = {"Points allowed": "in (the base)", "Turnovers forced": "in (20+ bonus)", "Steals": "out — players score them", "Blocks": "out — players score them",
        "Violations forced": "in (each one) — but mostly luck", "Deflections": "out — not a basic stat", "Contested shots": "out — not a basic stat",
        "Charges drawn": "out — rare, not defense", "Loose balls recovered (def)": "out — not a basic stat", "Box outs (def)": "out — not a basic stat",
        "Offensive fouls forced": "option — the best of the other violations"}
for x in C.itertuples():
    w(f"| {x.cand} | {x.per_game:.1f} | {x.follows_defense:.2f} | {x.repeats:.2f} | {VERD.get(x.cand, '')} |")
w("")
w("- **Violations forced are mostly luck** (follow defense 0.04): fun to cheer, so shot clock violations stay at +2 each — a size that doesn't decide things.")
w("- Not in: shooting percentages (too abstract), rebounds on their own, opponent 3P% (luck: doesn't repeat), \"no "
  "opponent scores 30\" (it's about their star), opponent points off turnovers (it's offense).")
w(f"- Other violations as forced per game: offensive fouls {VT['OFF_FOUL']['pg']:.1f} (follows defense {VT['OFF_FOUL']['corr']:.2f}, repeats "
  f"{VT['OFF_FOUL']['yoy']:.2f}); travels {VT['TRAVEL']['pg']:.1f} (not defense); backcourt {VT['BACKCOURT']['pg']:.1f}; 8- and 5-second about 1 in 50 games each.\n")
w("## Data and scripts\n")
w("- Team game logs (NBA.com: base, advanced, misc, four factors, opponent) '22–'26 — `scripts/pull_league_seasons.py`.")
w("- Team violations and hustle by game day, '23–'26 — `scripts/pull_team_daily.py`. A team's violations forced = its "
  "opponent's own violations that day; checked against play-by-play on '25: all 2,460 team-games match.")
w("- Analysis: `scripts/projection_study/team_*.py` (`team_draft4.py` current scoring + projections, `team_timeline.py`, "
  "`team_md4.py` writes this file, `team_report.py` the page).")
w("- Write-up page: https://claude.ai/artifact/R6rsSPwshQQTizgPRxJzEr\n")
w("## Log\n")
for line in [
    "2026-10-07: rework started — point margin out; TEAM = defense, like fantasy football's D/ST.",
    "Commissioner: weekly score = best game of the week; raw points allowed (simple); TEAM must feel impactful and be easy to root for (lines, turnovers, violations to cheer); weighting later.",
    "Shot clock violations come from NBA.com's team violations table (MeasureType=Violations), by day, matched to the opponent.",
    "Draft 1 (smooth, too easy to tune out) → draft 2 (all swingy) → commissioner: one steady bread-and-butter category, the rest swingy → draft 3 (two steady options) → draft 4 (commissioner's numbers).",
    "Hustle stats pulled and tested; commissioner: basic stats only this year.",
    "Commissioner: draft 5 — +1 per point under 120, +10 under 100 (no under-90 bonus), +2 for each shot clock violation forced; bonuses unchanged.",
    "Commissioner: draft 6 — teams never miss games, so nerf: +2 per 5 points under 125; 20+ turnovers +10. Small numbers are fine (deceptive), it's about relative value. Keep the simple projection."]:
    w(f"- {line}")
open("/Users/allan/PycharmProjects/2026_pickem/TEAM_SCORING.md", "w").write("\n".join(L) + "\n")
print("ok", len(L))
