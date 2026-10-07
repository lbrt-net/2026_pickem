# Sections 9–14 of weekly_best_game.html: player-specific PROJ MAX. Exec'd at the end of disp_report.py (uses its helpers).
import pandas as pd
D7 = json.load(open(S + "disp7.json"))
D5 = json.load(open(S + "disp5.json"))
CP = pd.read_csv(S + "disp_components_players.csv")
SEL = ["Stephen Curry", "Kevin Durant", "Tyrese Haliburton", "Domantas Sabonis", "Nikola Jokić", "Luka Dončić", "Shai Gilgeous-Alexander", "Giannis Antetokounmpo"]
cp = CP.set_index("name")
same_tbl = table(["Player ('24–'26)", "FP/G", "Bad week (25th pct)", "Big week (90th pct)", "Spread vs his average"],
                 [[E(n), f1(cp.fp[n]), f"+{cp.p25[n]:.1f}", f"+{cp.p90[n]:.1f}", f"{(cp.ratio[n] - 1) * 100:+.0f}%"] for n in SEL if n in cp.index])
comp_tbl = table(["Scoring part", "Average FP/G", "Best of 3 games", "Best of 3 ÷ average", "Share of the best game's lift"],
                 [[E(c["part"]), f"{c['mean']:.2f}", f"{c['max3']:.2f}" if c["pos"] else f"{c['max3']:.2f} (least costly)", f"<b>{c['ratio']:.2f}</b>" if c["pos"] else "—",
                   f"{100 * D5['dec'][c['part']] / D5['dectot']:+.0f}%" if c["part"] in D5["dec"] else "100%"] for c in D5["comp"]])


def lead(col, n=8, fmt="{:.2f}", extra=None):
    t = CP.sort_values(col, ascending=False).head(n)
    return ", ".join(f"{E(r['name'])} {fmt.format(r[col])}" + (f" ({extra(r)})" if extra else "") for _, r in t.iterrows())


lead_tbl = table(["Volatile in…", "Who (per-game swing)"], [
    ["Shot volume (FGA swing ÷ FGA)", lead("fga_cv", extra=lambda r: f"{r['fga']:.0f} FGA")],
    ["Shot volume, steadiest", ", ".join(f"{E(r['name'])} {r['fga_cv']:.2f}" for _, r in CP.sort_values("fga_cv").head(8).iterrows())],
    ["Steals (SD of steal FP)", lead("sd_STL")], ["Turnovers (SD of turnover FP)", lead("sd_TOV")],
    ["Blocks (SD of block FP)", lead("sd_BLK")], ["Threes (SD of 3PM bonus FP)", lead("sd_3PM")]], cls="")
T3 = D5["three"]
always_hi = [x for x in T3 if min(x["r"]) > 1]
always_lo = [x for x in T3 if max(x["r"]) < 1]
trait_tbl = table(["Spread vs his average, every season '23 / '24 / '25", "Above all three", "Below all three"],
                  [[f"{D5['n3']} established players (20+ FP/G, 50+ GP each season)", ", ".join(E(x["name"]) for x in sorted(always_hi, key=lambda x: -x["avg"])),
                    ", ".join(E(x["name"]) for x in sorted(always_lo, key=lambda x: x["avg"]))]], cls="")
PR = D7["prior"]
arch_tbl = table(["Archetype", "Under 15 FP/G", "15–25", "25+"],
                 [[E(a)] + [f"{(PR.get(f'{a}|{b}', 1) - 1) * 100:+.0f}%" for b in ("<15", "15–25", "25+")]
                  for a in ("Big", "Self-creator, outside", "Self-creator, mid/paint", "Assisted")])
cal_tbl = table(["Season", "All: above ceiling (10%)", "All: below floor (25%)", "Volatile: above ceiling", "Steady: below floor", "Steady: above ceiling"], [
    ["'23", "10.6 → 10.5%", "25.3 → 23.4%", "11.2 → 10.3%", "25.6 → 19.9%", "12.8 → 13.7%"],
    ["'24", "11.2 → 11.2%", "28.3 → 25.2%", "13.4 → <b>9.6%</b>", "32.4 → <b>25.0%</b>", "8.2 → 9.8%"],
    ["'25", "10.7 → 10.9%", "26.1 → 22.5%", "13.5 → <b>10.1%</b>", "34.1 → <b>26.2%</b>", "8.7 → 12.7%"],
    ["'26 (check)", "9.2 → 9.2%", "26.1 → 24.0%", "9.5 → 8.6%", "32.2 → <b>27.0%</b>", "7.9 → 9.2%"]])
# range chart, 2026-27
BD7 = sorted(D7["board"], key=lambda r: -r["e3"])
avg_rank = {r["name"]: i + 1 for i, r in enumerate(sorted(D7["board"], key=lambda r: -r["fp"]))}
lw, rw, rh, t0 = 168, 20, 22, 26
W = 640
H = t0 + rh * len(BD7) + 34
lo_, hi_ = 20, 62
Xr = lambda v: lw + (v - lo_) / (hi_ - lo_) * (W - lw - rw)  # noqa: E731
o = [f'<text class="mt" x="{lw}" y="14">2026-27, a 3-game week: bad week · typical · big week</text>']
for v in range(lo_, hi_ + 1, 5):
    o.append(f'<line class="grid" x1="{Xr(v):.1f}" x2="{Xr(v):.1f}" y1="{t0}" y2="{t0 + rh * len(BD7)}"/><text class="ax" x="{Xr(v):.1f}" y="{t0 + rh * len(BD7) + 15}" text-anchor="middle">{v}</text>')
for i, r in enumerate(BD7):
    y = t0 + i * rh + rh / 2
    cls = "g2" if r["f"] >= 1.03 else ("g3" if r["f"] <= 0.97 else "g1")
    o.append(f'<text class="pl" x="{lw - 8}" y="{y + 4:.1f}" text-anchor="end" style="font-weight:400">{E(r["name"])}</text>'
             f'<line x1="{Xr(r["p25_3"]):.1f}" x2="{Xr(r["p90_3"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="rng {cls}"/>'
             f'<rect class="{cls}" x="{Xr(r["p50_3"]) - 1.5:.1f}" y="{y - 7:.1f}" width="3" height="14" rx="1"/>'
             f'<circle cx="{Xr(r["fp"]):.1f}" cy="{y:.1f}" r="3" class="avgdot"/>'
             f'<title>{E(r["name"])}: bad week {r["p25_3"]:.1f}, typical {r["p50_3"]:.1f}, big week {r["p90_3"]:.1f}, PROJ AVG {r["fp"]:.1f}</title>')
o.append(f'<text class="ax" x="{(lw + W - rw) / 2:.1f}" y="{H - 4}" text-anchor="middle">fantasy points, best game of the week</text>')
range_ch = f'<svg class="sc" viewBox="0 0 {W} {H}" role="img" aria-label="weekly range">{"".join(o)}</svg>'
rkey = '<div class="key"><span><i class="g2"></i>Volatile (spread ×1.03+)</span><span><i class="g1"></i>Average</span><span><i class="g3"></i>Steady (×0.97 or less)</span><span><i class="avgdot-k"></i>PROJ AVG</span></div>'
board7 = table(["Player", "PROJ AVG (rank)", "Spread, volume only", "Spread, player", "Archetype", "Bad week", "Typical", "Big week", "PROJ MAX 2 / 3 / 4 games", "Rank at 3 games"],
               [[E(r["name"]), f"{r['fp']:.1f} ({avg_rank[r['name']]})", f"±{r['sd0']:.1f}", f"<b>±{r['sd']:.1f}</b>", E(r["arch"]), f1(r["p25_3"]), f1(r["p50_3"]), f1(r["p90_3"]),
                 f"{r['e2']:.1f} / <b>{r['e3']:.1f}</b> / {r['e4']:.1f}", str(i + 1)] for i, r in enumerate(BD7)])

extra = f"""
<section id="ps"><div class="n">9</div><div><h2>Same average, different weeks</h2>
<p class="claim">Sections 1–8 gave every player the same spread for his average. Real players differ. A volatile scorer's big week is much bigger; a steady player's bad week is better, and his big week smaller.</p>
{same_tbl}
<p class="cap">Best game of each 3-game week, above his average. Curry's big week is +23, Durant's +16; Durant's bad week is better. Haliburton is boom or bust; Sabonis has the lowest ceiling. Jokić keeps a full-size ceiling at the top of the league.</p>
</div></section>

<section id="parts"><div class="n">10</div><div><h2>Where the spread comes from</h2>
<p class="claim">Rare events are the spikiest. Blocks, steals and offensive rebounds run about twice their average in a player's best of three games. Points are the steadiest part, but they're so big that they carry most of a best game.</p>
{comp_tbl}
<p class="cap">Median over player-seasons '23–'25 with 10+ FP/G. The last column is the best game of each 3-game week minus his season average, split by part ({D5['nbest']} player-weeks). Missed shots barely move in a best game: more makes come with more misses. The parts don't add up to the total's best game, because a player's best night isn't his best night in every category. That's why the model works from whole games, not parts.</p>
{lead_tbl}
<p>Bigs who live on putbacks and lobs have the swingiest shot volume (Williams, Ayton, Allen, Gobert). Players fed the ball by design have the steadiest: Luka, Kawhi, Tatum, SGA. Ball-handlers swing in turnovers, each worth −2 (Cade, Durant, Jokić, LeBron, Trae). Curry is in a class of his own from three.</p>
</div></section>

<section id="trait"><div class="n">11</div><div><h2>A real trait for established players</h2>
<p class="claim">For bench players, spread is mostly noise. For established players it repeats: 0.40–0.45 season to season for 20+ FP/G players with 60+ games, against 0.2 for everyone.</p>
{trait_tbl}
<p class="cap">If it were luck, about {D5['n3'] // 8} would land above all three seasons and {D5['n3'] // 8} below. Instead it's {len(always_hi)} and {len(always_lo)}. The volatile ones are high-usage guards who live on threes and pull-ups; the steady ones are bigs and post or mid-range scorers.</p>
</div></section>

<section id="layers"><div class="n">12</div><div><h2>How the player's spread is built</h2>
<p class="claim">Volume first, then archetype, then his own record, then the asymmetry of a weekly best.</p>
<ol><li><b>Volume:</b> spread = 3.42 × average<sup>0.33</sup>. Lower-volume players get the bigger boost relative to their average.</li>
<li><b>Archetype:</b> bigs are 6'9"+ and take half their shots at the rim or in the paint, with few threes and little mid-range. Self-creators have 25%+ usage or make 45%+ of their shots unassisted. Of those, outside shooters take 40%+ of their shots from three; the rest are mid-range/paint maestros. Everyone else is assisted.</li>
<li><b>His own record:</b> his spread over the last three seasons, counting up to half at 200+ games.</li>
<li><b>Shape:</b> his weekly best simulated from his own games (full weight at 300+), otherwise from players at his level.</li>
<li><b>Asymmetry:</b> steady players' bad weeks are worse than their spread says, and their good weeks aren't. Only the bottom half of a steady player's range moves down.</li></ol>
{arch_tbl}
<p class="cap">Spread vs what volume predicts, by archetype and level ('21–'25). Low-volume self-creators swing most (+14% for outside shooters under 15 FP/G); bigs and high-volume assisted players least. A turnover-heavy player without the assists showed no dampening of his spread: his big-usage nights come with turnovers, but the totals even out.</p>
</div></section>

<section id="cal"><div class="n">13</div><div><h2>Tested: floors and ceilings</h2>
<p class="claim">About 10% of weeks should beat the ceiling and 25% should fall under the floor. With volume only, volatile players beat their ceiling too often and steady players fell under their floor too often. The player model fixes both.</p>
{cal_tbl}
<p class="cap">Volume only → player model. Players with 15+ FP/G and 8+ full 3-game weeks, each given his real season average so only the spread is tested. '23–'25 set the model; '26 is the check. Volatile = player factor ≥ 1.03, steady ≤ 0.97.</p>
</div></section>

<section id="board27"><div class="n">14</div><div><h2>2026-27: player-specific PROJ MAX</h2>
<p class="claim">PROJ MAX no longer follows PROJ AVG in lockstep. Luka passes SGA at 3 games; Haliburton passes Mitchell and Cade; Durant and Sabonis drop. Jokić stays on top.</p>
{rkey}
{range_ch}
{board7}
<p class="cap">Bad week = 25th percentile, typical = median, big week = 90th percentile of his best game in a 3-game week. PROJ MAX = expected best game. No opponent, home/away or availability yet.</p>
</div></section>
"""
page = page.replace('</div></section>\n</div>\n', '</div></section>\n' + extra + '</div>\n', 1) if False else page[: page.rstrip().rfind("</div>")] + extra + "</div>\n"
page = page.replace("</style>", ".rng {{ stroke-width:6; stroke-linecap:round; }} .rng.g1 {{ stroke:var(--g1); }} .rng.g2 {{ stroke:var(--g2); }} .rng.g3 {{ stroke:var(--g3); }}\n.avgdot {{ fill:var(--ink); }} .key i.avgdot-k {{ background:var(--ink); }}\n</style>".replace("{{", "{").replace("}}", "}"), 1)
