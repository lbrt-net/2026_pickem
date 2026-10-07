"""Builds weekly_best_game.html: the PROJ MAX / dispersion write-up, same look as the per-game report."""
import html, json, re
import numpy as np

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = json.load(open(S + "disp_report.json"))
E = html.escape
style = re.search(r"<style>.*?</style>", open(S + "per_game_projections.html").read(), re.S).group(0)
a, b, KL = D["a"], D["b"], D["KL"]
f1 = lambda v: f"{v:.1f}"  # noqa: E731


def table(head, rows, cls="r"):
    return (f'<div class="tw"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


def frame(xlo, xhi, ylo, yhi, xt, yt, xlab, ylab, title, w=480, h=380):
    l, r, t, bb = 46, 14, 26, 44
    X = lambda v: l + (v - xlo) / (xhi - xlo) * (w - l - r)  # noqa: E731
    Y = lambda v: t + (yhi - v) / (yhi - ylo) * (h - t - bb)  # noqa: E731
    o = [f'<text class="mt" x="{l}" y="14">{E(title)}</text>']
    v = xlo
    while v <= xhi + 1e-9:
        o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{t}" y2="{h - bb}"/><text class="ax" x="{X(v):.1f}" y="{h - bb + 15}" text-anchor="middle">{v:g}</text>')
        v += xt
    v = ylo
    while v <= yhi + 1e-9:
        o.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
        v += yt
    o.append(f'<text class="ax" x="{(l + w - r) / 2:.1f}" y="{h - 8}" text-anchor="middle">{E(xlab)}</text>'
             f'<text class="ax" x="12" y="{(t + h - bb) / 2:.1f}" transform="rotate(-90 12 {(t + h - bb) / 2:.1f})" text-anchor="middle">{E(ylab)}</text>')
    return o, X, Y, w, h


def label(o, X, Y, x, y, name, w):
    anchor = "end" if X(x) > w * 0.7 else "start"
    last = name.split()[-1] if name.split()[-1] not in ("Jr.", "III", "II") else name.split()[-2]
    o.append(f'<text class="pl" x="{X(x) + (-7 if anchor == "end" else 7):.1f}" y="{Y(y) + 4:.1f}" text-anchor="{anchor}">{E(last)}</text>')


# chart 1: mean vs SD ('25)
o, X, Y, w, h = frame(0, 50, 0, 20, 10, 5, "average FP per game ('25)", "game-to-game spread (SD, FP)", "Spread grows with the average, slowly")
for p in D["pts"]:
    o.append(f'<circle class="pt g1" cx="{X(min(p["mean"], 50)):.1f}" cy="{Y(min(p["sd"], 20)):.1f}" r="3.2"><title>{E(p["name"])}: {p["mean"]:.1f} ± {p["sd"]:.1f}</title></circle>')
curve = " ".join(f"{X(m):.1f},{Y(a * m ** b):.1f}" for m in np.linspace(1, 50, 60))
o.append(f'<polyline points="{curve}" fill="none" stroke="var(--g2)" stroke-width="2.5"/>')
LAB1 = {"Nikola Jokić", "Shai Gilgeous-Alexander", "Stephen Curry", "Kevin Durant", "Rudy Gobert", "Devin Booker", "Luka Dončić"}
for p in D["pts"]:
    if p["name"] in LAB1:
        label(o, X, Y, min(p["mean"], 50), min(p["sd"], 20), p["name"], w)
ch1 = f'<svg class="sc" viewBox="0 0 {w} {h}" role="img" aria-label="mean vs spread">{"".join(o)}</svg>'

# chart 2: per-player check '26
o, X, Y, w, h = frame(10, 60, 10, 60, 10, 10, "projected best game, 3-game weeks (avg)", "actual best game, same weeks (avg)", "'26: projected vs actual weekly best, by player")
o.append(f'<polygon class="band" points="{X(10):.1f},{Y(13):.1f} {X(57):.1f},{Y(60):.1f} {X(60):.1f},{Y(60):.1f} {X(60):.1f},{Y(57):.1f} {X(13):.1f},{Y(10):.1f} {X(10):.1f},{Y(10):.1f}"/>')
o.append(f'<line class="diag" x1="{X(10):.1f}" y1="{Y(10):.1f}" x2="{X(60):.1f}" y2="{Y(60):.1f}"/>')
for p in D["pcheck"]:
    o.append(f'<circle class="pt g1" cx="{X(min(max(p["pred"], 10), 60)):.1f}" cy="{Y(min(max(p["act"], 10), 60)):.1f}" r="3.4"><title>{E(p["name"])}: {p["pred"]:.1f} → {p["act"]:.1f} ({p["k"]} weeks)</title></circle>')
LAB2 = {"Nikola Jokić", "Shai Gilgeous-Alexander", "Stephen Curry", "Kevin Durant", "Rudy Gobert", "Victor Wembanyama", "Josh Giddey", "Jalen Brunson"}
for p in D["pcheck"]:
    if p["name"] in LAB2:
        label(o, X, Y, min(max(p["pred"], 10), 60), min(max(p["act"], 10), 60), p["name"], w)
ch2 = f'<svg class="sc" viewBox="0 0 {w} {h}" role="img" aria-label="per-player check">{"".join(o)}</svg>'

# chart 3: bias by games in week, mean-only vs spread model ('24+'25 avg)
bm = [np.mean([D["bias"][t]["m_mean"][n] for t in ("2023-24", "2024-25")]) for n in range(4)]
bl = [np.mean([D["bias"][t]["m_league"][n] for t in ("2023-24", "2024-25")]) for n in range(4)]
bf = [np.mean([D["bias"][t]["full"][n] for t in ("2023-24", "2024-25")]) for n in range(4)]
o, X, Y, w, h = frame(0.5, 4.5, -10, 4, 1, 2, "games he played that week", "projected minus actual best game (FP)", "How far off, by games in the week ('24 + '25)")
o = [x for x in o if 'text-anchor="middle">0.5<' not in x]
for i, (vals, cls, dx) in enumerate([(bm, "g2", -0.22), (bl, "g1", 0.0), (bf, "g3", 0.22)]):
    for n, v in enumerate(vals, start=1):
        x0 = X(n + dx - 0.1)
        y0, y1 = sorted([Y(0), Y(v)])
        o.append(f'<rect class="{cls}" x="{x0:.1f}" y="{y0:.1f}" width="{X(n + 0.1) - X(n - 0.1) - 2:.1f}" height="{max(y1 - y0, 1.5):.1f}" rx="2"><title>{n} games: {v:+.2f}</title></rect>')
o.append(f'<line class="diag" x1="{X(0.5):.1f}" x2="{X(4.5):.1f}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" style="stroke-dasharray:none"/>')
ch3 = f'<svg class="sc" viewBox="0 0 {w} {h}" role="img" aria-label="bias by games">{"".join(o)}</svg>'
k3 = '<div class="key"><span><i class="g2"></i>Average only (no spread)</span><span><i class="g1"></i>Average + spread</span><span><i class="g3"></i>Average + spread, weeks he played every team game</span></div>'

# tables
ax_names = {"USG_PCT": "Usage", "mpg": "Minutes per game", "PIE": "Player quality (PIE)", "AGE": "Age", "pts_share": "Share of his FP from points (scorer)",
            "reb_share": "Share of his FP from rebounds (rebounder)"}
ax_tbls = "".join(f"<div><p><b>{ax_names[k]}</b></p>" + table(["Group", "Player-seasons", "Spread vs expected"], [[E(g), str(n), f"<b>{(r - 1) * 100:+.0f}%</b>"] for g, n, r, m in v]) + "</div>"
                  for k, v in D["axes"].items())
pers_tbl = table(["Seasons", "Does his extra spread repeat? (correlation)"], [[k, f"{v:.2f}"] for k, v in D["pers"].items()])
sv = table(["Steadiest (20+ FP/G, 3+ seasons)", "Spread vs expected", "FP/G"], [[E(x["name"]), f"{(x['ratio'] - 1) * 100:+.0f}%", f1(x["mean"])] for x in D["steady"]])
vv = table(["Most volatile", "Spread vs expected", "FP/G"], [[E(x["name"]), f"{(x['ratio'] - 1) * 100:+.0f}%", f1(x["mean"])] for x in D["volat"]])
MN = {"m_mean": "Average only", "m_norm": "Average + spread, normal curve", "m_league": "<b>Average + spread, league's real shape</b>", "m_own": "Average + spread, his own past games"}
bias_tbl = table(["Model (projected − actual best game)", "1 game", "2 games", "3 games", "4 games"],
                 [[MN[m]] + [f"{np.mean([D['bias'][t][m][n] for t in ('2023-24', '2024-25')]):+.1f}" for n in range(4)] for m in MN]
                 + [["Player-weeks ('24 + '25)"] + [str(sum(D["bias"][t]["count"][n] for t in ("2023-24", "2024-25"))) for n in range(4)]])
avail_tbl = table(["Average + spread, projected − actual", "Season", "1 game", "2 games", "3 games"],
                  [[lab, f"'{t[-2:]}" + (" (check)" if t == "2025-26" else "")] + [f"{D['bias'][t][k][n]:+.1f}" for n in range(3)]
                   for t in ("2023-24", "2024-25", "2025-26") for lab, k in (("Played every team game", "full"), ("Missed a team game", "miss"))])
mult = table(["Games that week", "1", "2", "3", "4", "5"], [["Best game = average + this many spreads"] + [f"{k:.2f}" for k in KL]])
ex = table(["Average FP/G", "Spread (SD)", "Best of 2", "Best of 3", "Best of 4"],
           [[f"{m}", f1(a * m ** b)] + [f1(m + a * m ** b * KL[n - 1]) for n in (2, 3, 4)] for m in (10, 15, 20, 25, 30, 35, 40)])
bd = table(["#", "Player", "Team", "Pos", "PROJ AVG", "Spread", "PROJ MAX, 2 games", "3 games", "4 games"],
           [[str(x["rank"]), E(x["name"]), x["team"], x["pos"], f1(x["fp"]), f"±{x['sd']:.1f}", f"<b>{f1(x['m2'])}</b>", f"<b>{f1(x['m3'])}</b>", f"<b>{f1(x['m4'])}</b>"]
            for x in D["board"]])

page = f"""<title>Weekly Best Game</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..100,500..800&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
{style}
<div class="wrap">
<div class="eyebrow">Fantasy 2026-27 · Dispersion · PROJ MAX</div>
<h1>Weekly best game</h1>
<p class="dim">A player's weekly score is his best single game that week. This is how far above his average that best game lands, and what changes it. Seasons are named by the year they end ('26 = 2025-26). Everything was worked out on '22–'25; '26 is the check.</p>

<section id="what"><div class="n">1</div><div><h2>What PROJ MAX is</h2>
<p class="claim">PROJ MAX = PROJ AVG + his game-to-game spread × how far the best of that many games sits above the average.</p>
<p>The more games he plays in a week, the more chances at a big one: a 2-game week's best is about half a spread above his average, a 4-game week's about one full spread. The spread itself comes from his average (section 2), and the multiplier from how real NBA games are distributed:</p>
{mult}
{ex}
</div></section>

<section id="spread"><div class="n">2</div><div><h2>Spread grows with the average, slowly</h2>
<p class="claim">A 10 FP/G player's games swing about ±7; a 40 FP/G player's about ±12. Stars are steadier relative to their average.</p>
<div class="pair">{ch1}<div><p>Every dot is a player-season with 40+ games in '25. The line is the fit across {D['ndev']} player-seasons '22–'25: spread = {a:.2f} × average<sup>{b:.2f}</sup>. Doubling a player's average adds only about a quarter to his spread.</p>
<p>Rebounds, assists, steals and blocks behave like pure counting noise. Points come in 2s and 3s and swing more. Short games are noisier per possession. That's the earlier homoscedasticity work, logged in DISPERSION.md.</p></div></div>
</div></section>

<section id="axes"><div class="n">3</div><div><h2>Usage, minutes, good or bad player</h2>
<p class="claim">Once you know his average, usage, minutes, quality and age barely move a player's spread. Scorers swing a little more and rebounders a little less, within about ±6%.</p>
<p>Each table compares a player's real spread to what his average predicts (0% = exactly as expected), with the median per group across '22–'25:</p>
<div class="pair three">{ax_tbls}</div>
<p>All of these together explain about {D['r2'] * 100:.0f}% of the differences between players. A player's own extra spread repeats only weakly from one season to the next:</p>
<div class="pair">{pers_tbl}<div><p>A correlation around 0.2 means about four-fifths of a player's extra spread in one season is luck. The steady and volatile players do make basketball sense, though: three-point-heavy scorers swing more, bigs and mid-range scorers less.</p></div></div>
<div class="pair">{sv}{vv}</div>
<p class="cap">Curry's games swing about 13% more than his average predicts, Durant's about 15% less. In a 3-game week, that difference moves the projected best game by about one FP.</p>
</div></section>

<section id="weeks"><div class="n">4</div><div><h2>Tested on real weekly best games</h2>
<p class="claim">Using the average alone misses the weekly best by 3 to 9 FP. Adding the spread gets it right. How the spread is modeled hardly matters.</p>
<p>Every player-week (Monday to Sunday) in '24 and '25. Each model gets the player's real season average, so only the spread is tested:</p>
{k3}
<div class="pair">{ch3}<div>{bias_tbl}</div></div>
<p>A normal curve, the league's real (slightly skewed) shape and the player's own past games all land within about a point of each other. PROJ MAX uses the league shape: it comes from real games, and it's the closest in 4-game weeks. A player's own games don't add anything: a season isn't enough games to pin down his shape better than the league's.</p>
<p>The one real miss is 1- and 2-game weeks, where every version projects too high. The next section explains it.</p>
</div></section>

<section id="avail"><div class="n">5</div><div><h2>Weeks he missed a game are different</h2>
<p class="claim">When a player plays every one of his team's games, the projection is right. When he misses one, his other games that week are 1.5 to 2.5 FP worse: he's hurt, leaving early, or coming back on a minutes limit.</p>
{avail_tbl}
<p>So this isn't a spread problem. It belongs to the availability model: a player who is questionable, or just back from injury, should get a lower expected game as well as fewer games.</p>
</div></section>

<section id="check"><div class="n">6</div><div><h2>Player by player, '26</h2>
<div class="pair">{ch2}<div><p>Each dot is a player's average projected best game against his real average best game, over the 3-game weeks of '26 where he played every game (6+ such weeks). {D['within']} of {D['npc']} land within 3 FP.</p>
<p>The misses are role and form changes inside the season (the average moved), not the spread.</p></div></div>
</div></section>

<section id="board"><div class="n">7</div><div><h2>2026-27: PROJ MAX</h2>
<p class="claim">The top 25 and the random eight, by games that week.</p>
{bd}
<p class="cap">From PROJ AVG with the league shape. No player-specific spread, opponent, home/away or availability yet.</p>
</div></section>

<section id="next"><div class="n">8</div><div><h2>Next</h2>
<ul><li><b>Availability:</b> the chance he plays each game, plus a lower expected game when he's questionable or just back (section 5).</li>
<li><b>Opponent and home/away:</b> pace, fantasy points allowed, matchup by height and weight. These move the average for that game, and PROJ MAX follows.</li>
<li><b>Player spread factor:</b> keep about a fifth of his own extra spread from last season (scorers up, rebounders down). It's worth about a point at most, so it's last.</li>
<li><b>Win probability for a fantasy team:</b> simulate weeks by drawing real games from past players with a similar average and spread.</li></ul>
</div></section>
</div>
"""
open(S + "weekly_best_game.html", "w").write(page)
print("ok", len(page))
