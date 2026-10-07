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
D2 = json.load(open(S + "team_draft2.json"))
T2 = pd.DataFrame(D2["teams"]).set_index("TEAM_ABBREVIATION")
CU = pd.read_csv(S + "team_cutoffs.csv").set_index("cut")
w("## How a TEAM scores (draft 2, current)\n")
w("Built to be **exciting and swingy**: a few big lines to hold the opponent under, a play-by-play thing to cheer "
  "for, and bonuses that even great defenses don't get every week. Per game:\n")
w("- **Hold them under 100: +15. Under 95: +10 more. Under 90: +10 more.** A great night is worth +35; most nights, nothing here.")
w("- **Every violation forced: +5.** Shot clock, 8-second, 5-second: the defense made the offense run out of time. "
  f"About {D2['viol_league']:.1f} a game; two in a night is a highlight.")
w("- **+10 bonuses**, each one rare:")
w("  - **Force 20+ turnovers**")
w("  - **Hold them to 6 or fewer fast-break points**")
w("  - **Hold them to 32 or fewer points in the paint**")
w("  - **Win the defensive glass by 30+** (your defensive rebounds minus their offensive rebounds)\n")
w("Weekly score = **the team's best game of the week**, the same as players. How big TEAM is next to the player spots "
  "is decided later.\n")
w("What it looks like on 2025-26: a TEAM's best game of the week averages "
  f"**{D2['league_week2']:.0f}**, but it swings a lot (give or take about {D2['league_sd2']:.0f}): only "
  f"{100 * D2['zero']:.0f}% of weeks are a zero, and {100 * D2['big']:.0f}% of weeks are a big one (30+). It still follows "
  f"real defense closely: the order of teams matches defensive rating at {D2['corr2']:.2f} (out of 1).\n")
w("**Draft 1** (earlier, too smooth): +5 for every line under 120 / 115 / 110 / 105 / 100 / 95 / 90, +1 per "
  f"turnover forced, +2 per violation forced. Weekly score {D2['league_week1']:.0f} ± {D2['league_sd1']:.0f}: it paid out "
  "something every game, so there was little to sweat.\n")
w("## Why these\n")
w("- **Points allowed is what good defense looks like**: across '22–'25 the teams that allow the fewest points are "
  "the teams with the best defensive ratings (0.89 out of 1). The score is on the screen, so it's easy to root for.")
w("- **Few, harsh lines** because it lines up with defense so well: holding a team under 100 happens in about 1 game "
  "in 7, under 95 in 1 in 14, under 90 in 1 in 33. The best defenses do it about twice as often as the worst.")
w("- **Violations forced** are the most purely defensive turnovers: nobody on offense made a mistake on their own.")
w("- **The four bonuses** are the commissioner's: things a defense does that you can see, rare enough to be a big moment.")
w("- **Not in**: shooting percentages (too abstract next to a count), steals and blocks (players already score them), "
  "and plain rebounds (partly about the offense) — the rebounding bonus is a margin instead.\n")
w("How often each line and bonus happens ('22–'25), the chance a team gets it at least once in a 3-game week, and how "
  "much more often the best defenses get it ('26's best five vs worst five):\n")
w("| Line or bonus | Games it happens in | Weeks with at least one | Best 5 defenses, per game | Worst 5, per game | Goes with good defense (0–1) |")
w("|---|---|---|---|---|---|")
for k, lab in [("Opponent under 100", "Hold them under 100"), ("Opponent under 95", "Under 95"), ("Opponent under 90", "Under 90"),
               ("20+ turnovers forced", "Force 20+ turnovers"), ("Opp fast-break pts 6 or fewer", "6 or fewer fast-break points"),
               ("Opp paint pts 32 or fewer", "32 or fewer paint points"), ("Def. rebound margin 30+", "Defensive glass by 30+")]:
    r = CU.loc[k]
    w(f"| {lab} | {100 * r.league:.0f}% | {100 * r.week:.0f}% | {100 * r.best5:.0f}% | {100 * r.worst5:.0f}% | {r["corr"]:.2f} |")
w("")
w("## What it looks like on 2025-26\n")
w("Every team: average weekly score (best game of the week), how much it swings, how often a week was a big one "
  "(30+), its single best game, how often it held opponents under 100, violations forced per game, and how often it "
  "got each bonus. Defensive rating (points allowed per 100 possessions, lower is better) for comparison.\n")
w("| # | Team | Weekly score | Swing (±) | Big weeks (30+) | Best game | Under 100 | Violations forced | 20+ TOV | FB ≤ 6 | Paint ≤ 32 | Glass 30+ | Defensive rating |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, (k, r) in enumerate(T2.iterrows()):
    w(f"| {i + 1} | {k} | **{r.week2:.1f}** | {r.sd2:.0f} | {100 * r.big2:.0f}% | {r.top2:.0f} | {100 * r.u100:.0f}% | {r.viol:.2f} | "
      f"{100 * r['20+ turnovers forced']:.0f}% | {100 * r['Fast-break pts held to 6 or fewer']:.0f}% | {100 * r['Paint pts held to 32 or fewer']:.0f}% | "
      f"{100 * r['Rebounding: DREB − opp OREB 30+']:.0f}% | {r.dr:.1f} |")
w("")
w("Biggest single games of '26:")
for x in D2["examples"]:
    parts = x["MATCHUP"].split()
    who, opp = parts[0], parts[-1]
    nv = int(x["viol"])
    w(f"- **{who} held {opp} to {x['OPP_PTS']:.0f}** ({x['GAME_DATE']}): **{x['score2']:.0f}** — {nv} violation{'s' if nv != 1 else ''} forced, "
      f"{x['OPP_TOV']:.0f} turnovers forced, {opp} had {x['OPP_PTS_FB']:.0f} fast-break and {x['OPP_PTS_PAINT']:.0f} paint points, glass +{x['DREB_MARGIN']:.0f}")
w("")
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
w("- **Violations forced** for '25 → '23: being pulled now ('26 done), one request per game day.")
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
w("- 2026-10-07: draft 1 written: +5 per line every 5 points, +1 turnover, +2 violation. Orders teams like defense (0.88) but too smooth.")
w("- 2026-10-07 (commissioner): draft 1 is lame — a smooth scale is easy to tune out. TEAM should be exciting and swingy: fewer, harsher lines; "
  "high cutoffs that don't happen every week even for good defenses; no shooting % (abstract); rebounding only as a margin; fast-break, paint "
  "and turnovers as one bonus each. (Players: clutch-time scoring to be added back to the projection work.)")
w("- 2026-10-07: draft 2 (above). Weekly 19 ± 14, follows defense 0.80. Cutoffs measured in `team_cutoffs.py`.")
w("- 2026-10-07 (commissioner, for the next draft — nothing redone yet): **not every category should be swingy.** One **bread-and-butter** category that pays steadily most games, then the rest as the swingy lines and rare bonuses.")
w("- Scripts: `scripts/projection_study/team_draft1.py` (draft 1 on '26), `team_eval.py` / `team_show.py` (stats "
  "tested), `scripts/pull_team_daily.py` (violations + hustle by day), `scripts/pull_league_seasons.py` (team game logs).")
open("/Users/allan/PycharmProjects/2026_pickem/TEAM_SCORING.md", "w").write("\n".join(L) + "\n")
print("ok")
