"""Writes TEAM_SCORING.md (plain language) from team_draft1.json, team_show.json, team_eval.csv."""
import json
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D1 = json.load(open(S + "team_draft1.json"))
SH = json.load(open(S + "team_show.json"))
EV = pd.read_csv(S + "team_eval.csv").set_index("cand")
T = pd.DataFrame(D1["teams"]).set_index("TEAM_ABBREVIATION")
TS = pd.DataFrame(SH["teams"]).set_index("TEAM_ABBREVIATION")
L = []
w = L.append
w("# TEAM scoring\n")
w("Every fantasy roster has one **TEAM** spot: you draft a whole NBA team, like a defense in fantasy football. "
  "This file is how a TEAM scores, why, and what it looks like on last season (2025-26). Seasons are named by the "
  "year they end ('26 = 2025-26). Running log at the bottom.\n")
w("## The idea\n")
w("Players already score for what they do: points, rebounds, assists, steals, blocks. **TEAM is where a team's "
  "defense shows up.** The old TEAM scoring was point margin (how much a team won by). That's out: it rewards good "
  "offense as much as defense, and it made TEAM worth about twice a top center.\n")
w("It also has to be **easy to root for** while you watch, even when the math is complicated: \"please hold them "
  "under 105\", \"please force another turnover\", \"please get another shot clock violation\".\n")
w("## How a TEAM scores (draft 1)\n")
w("Per game:")
w("- **Points allowed: +5 for every line the opponent finishes under: 120, 115, 110, 105, 100, 95, 90.** Hold "
  "them to 98 and that's five lines, +25. Hold them to 112, two lines, +10. Allow 121, nothing.")
w("- **Turnovers forced: +1 each.** Every opponent turnover: steals, travels, offensive fouls, everything.")
w("- **Violations forced: +2 each.** Shot clock, 8-second and 5-second violations: the defense made the offense run out "
  "of time. (Being pulled now; included in the numbers below only for the dates already pulled.)\n")
w("Weekly score = **the team's best game of the week**, the same as players.\n")
w("How big this makes TEAM is decided later. Right now a team's best game of the week averages "
  f"**{D1['league_week']:.1f}**, about what a star player's best game is worth.\n")
w("## Why these three\n")
w("- **Points allowed is what good defense looks like.** The teams that give up the fewest points are the teams "
  "with the best defenses: across '22–'25 it lines up with defensive rating (points allowed per 100 possessions) "
  "almost perfectly (0.89 out of 1). It's also what you can watch: the score is on the screen.")
w("- **Lines every 5 points** so there's always something to root for late in a game, and so a great defensive "
  "night (under 95) is worth a lot more than an average one.")
w("- **Turnovers forced** is how a defense makes plays. It's a style more than a sign of a great defense, but "
  "teams that force a lot of turnovers keep doing it the next season, so you can draft for it.")
w("- **Violations forced** are the most purely defensive turnovers there are: nobody on offense made a mistake on "
  "their own, the defense took the clock away.\n")
w("## What it looks like on 2025-26\n")
w("Every team's average weekly score (best game of the week), its average game, and how often it held opponents "
  "under 100 / 105 / 110. Sorted by weekly score. Defensive rating (points allowed per 100 possessions, lower is "
  "better) for comparison: the order matches it closely.\n")
w("| # | Team | Weekly score | Average game | Points allowed | Held under 100 | Under 105 | Under 110 | Turnovers forced | Defensive rating |")
w("|---|---|---|---|---|---|---|---|---|---|")
for i, (k, r) in enumerate(T.iterrows()):
    w(f"| {i + 1} | {k} | **{r.week_best:.1f}** | {r.game:.1f} | {r.opp_pts:.1f} | {100 * r.u100:.0f}% | {100 * r.u105:.0f}% | {100 * r.u110:.0f}% | {r.tov:.1f} | {r.dr:.1f} |")
w("")
top = list(T.index[:5])
w(f"Best five: {', '.join(top)}. OKC held opponents under 105 in {100 * T.loc['OKC', 'u105']:.0f}% of its games; Utah in "
  f"{100 * T.loc['UTA', 'u105']:.0f}%. The gap between the best and the worst TEAM is about {T.week_best.max() - T.week_best.min():.0f} points a "
  "week.\n")
w("## What else we looked at\n")
w("Each stat: last season's best team, league average and worst team (per game), whether it goes with good defense "
  "(how closely teams' averages line up with defensive rating, 0 to 1), and whether teams repeat it the next season "
  "(0 to 1).\n")
NAMES = {"OPP_PTS": ("Opponent points", "Opponent points (fewer)"), "U100": ("Held under 100", "Held under 100 (+10)"),
         "U105": ("Held under 105", None), "U110": ("Held under 110", "Held under 110 (+5)"),
         "STL": ("Steals", "Team steals"), "BLK": ("Blocks", "Team blocks"), "OPP_TOV": ("Turnovers forced", "Opponent turnovers forced"),
         "OPP_PTS_PAINT": ("Opponent paint points", "Opponent paint points (fewer)"), "OPP_PTS_FB": ("Opponent fast-break points", "Opponent fast-break points (fewer)"),
         "OPP_PTS_2ND_CHANCE": ("Opponent second-chance points", "Opponent second-chance points (fewer)"), "OPP_EFG_PCT": ("Opponent shooting (eFG%)", "Opponent eFG% (lower)"),
         "OPP_FG3_PCT": ("Opponent 3P%", "Opponent 3P% (lower)"), "DREB_PCT": ("Defensive rebound %", "Defensive rebound %")}
w("| Stat | Best team '26 | League | Worst team '26 | Goes with good defense | Repeats next season | Verdict |")
w("|---|---|---|---|---|---|---|")
VERDICT = {"OPP_PTS": "in (the base)", "U100": "in (a line)", "U105": "in (a line)", "U110": "in (a line)", "OPP_TOV": "in",
           "STL": "out — players already score steals", "BLK": "out — players already score blocks", "OPP_PTS_PAINT": "maybe",
           "OPP_PTS_FB": "maybe", "OPP_PTS_2ND_CHANCE": "out — doesn't repeat", "OPP_EFG_PCT": "covered by points allowed",
           "OPP_FG3_PCT": "out — mostly luck (doesn't repeat)", "DREB_PCT": "out — weak"}
for _, c, s in SH["cats"]:
    if c not in NAMES or c not in TS:
        continue
    lab, ev = NAMES[c]
    col = TS[c]
    best = col.idxmin() if s == "lower" else col.idxmax()
    worst = col.idxmax() if s == "lower" else col.idxmin()
    pct = c.startswith("U") or c.endswith("PCT")
    fmt = (lambda v: f"{100 * v:.0f}%") if pct else (lambda v: f"{v:.1f}")
    rep = f"{EV.loc[ev, 'yoy']:.2f}" if ev and ev in EV.index else "—"
    w(f"| {lab} | {best} {fmt(col[best])} | {fmt(col.mean())} | {worst} {fmt(col[worst])} | {SH['corr'][c]:.2f} | {rep} | {VERDICT.get(c, '')} |")
w("")
w("Also tested and out: \"no opponent scores 30\" (it's about the other team's star, not your defense), opponent "
  "points off turnovers (it's really offense), opponent 3-point attempts and free-throw rate (not defense).\n")
w("## Coming next\n")
w("- **Violations forced** for every game ('26 → '23): being pulled now, one request per game day.")
w("- **Hustle stats** (deflections, charges drawn, contested shots, loose balls, box outs): same pull. Then test them "
  "the same way and decide what's in.")
w("- **Weighting**: how big TEAM is next to the player spots (DRAFT_GUIDE.md has what a player spot is worth).\n")
w("## Log\n")
w("- 2026-10-07: rework started. Point margin out. Defense like fantasy football's D/ST.")
w("- 2026-10-07 (commissioner): weekly score = best game of the week; raw points allowed (simple), not per 100 "
  "possessions; TEAM must feel impactful and be easy to root for — lines to hold the opponent under, turnovers and "
  "violations to cheer for one at a time; weighting later; pull hustle stats.")
w("- 2026-10-07: shot clock violations aren't in NBA.com's box scores; they're on the team Violations stats page "
  "(MeasureType=Violations, same endpoint as the team stats pages), pulled day by day and matched to that day's "
  "opponent. In '25 play-by-play, 1,982 shot clock violations, about 0.8 per team per game.")
w("- 2026-10-07: draft 1 written (above). On '26 it orders teams almost exactly like defensive rating (0.87).")
w("- Scripts: `scripts/projection_study/team_draft1.py` (draft 1 on '26), `team_eval.py` / `team_show.py` (stats "
  "tested), `scripts/pull_team_daily.py` (violations + hustle by day), `scripts/pull_league_seasons.py` (team game logs).")
open("/Users/allan/PycharmProjects/2026_pickem/TEAM_SCORING.md", "w").write("\n".join(L) + "\n")
print("ok")
