"""Builds team_slot_scoring.html — the TEAM slot rework (TEAM_SCORING.md) as a page."""
import html, json, re
import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
E = html.escape
style = re.search(r"<style>.*?</style>", open(S + "per_game_projections.html").read(), re.S).group(0)
EV = pd.read_csv(S + "team_eval.csv")
CA = pd.read_csv(S + "team_calib.csv")
DG = json.load(open(S + "draft_guide.json"))


def table(head, rows, cls="r"):
    return (f'<div class="tw"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


KEEP = {"Opponent points (fewer)", "Held under 100 (+10)", "Held under 110 (+5)", "Both tiers (<100: +15, <110: +5)", "Defensive rating (pts/100 poss, lower)",
        "Opponent paint points (fewer)", "Opp paint under 40 (bonus)"}
STYLE = {"Opponent turnovers forced", "Opponent turnover % forced"}
REF = {"Point margin (reference — out)"}
SHORT = {"Opponent points (fewer)": "Opp points", "Held under 110 (+5)": "Under 110", "Held under 100 (+10)": "Under 100", "Defensive rating (pts/100 poss, lower)": "Def rating",
         "Opponent paint points (fewer)": "Opp paint", "Opponent turnovers forced": "TOV forced", "Opponent 3P% (lower)": "Opp 3P%", "No opponent scores 30 (bonus)": "No 30-pt scorer",
         "Steals + blocks": "Stl + blk", "Opponent points off turnovers (fewer)": "Opp pts off TOV", "Opponent second-chance points (fewer)": "2nd-chance",
         "Point margin (reference — out)": "Point margin", "Opponent 3PA (fewer)": "Opp 3PA", "Opponent eFG% (lower)": "Opp eFG%", "Defensive rebound %": "DREB%"}

# chart 1: tracks defense (x) vs carries over (y)
W, H, l, r, t, b = 560, 420, 50, 16, 28, 46
xlo, xhi, ylo, yhi = -0.4, 1.05, -0.2, 0.7
X = lambda v: l + (v - xlo) / (xhi - xlo) * (W - l - r)  # noqa: E731
Y = lambda v: t + (yhi - v) / (yhi - ylo) * (H - t - b)  # noqa: E731
o = ['<text class="mt" x="50" y="16">Each candidate: is it defense, and does it repeat?</text>']
for v in np.arange(-0.4, 1.01, 0.2):
    o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{t}" y2="{H - b}"/><text class="ax" x="{X(v):.1f}" y="{H - b + 15}" text-anchor="middle">{v:.1f}</text>')
for v in np.arange(-0.2, 0.71, 0.1):
    o.append(f'<line class="grid" x1="{l}" x2="{W - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v:.1f}</text>')
o.append(f'<text class="ax" x="{(l + W - r) / 2:.1f}" y="{H - 8}" text-anchor="middle">tracks team defense (correlation with defensive rating)</text>'
         f'<text class="ax" x="12" y="{(t + H - b) / 2:.1f}" transform="rotate(-90 12 {(t + H - b) / 2:.1f})" text-anchor="middle">carries over to next season</text>')
for x in EV.itertuples():
    cls = "g3" if x.cand in KEEP else ("g1" if x.cand in STYLE else ("g4" if x.cand in REF else "g2"))
    o.append(f'<circle class="pt {cls}" cx="{X(x.defense):.1f}" cy="{Y(x.yoy):.1f}" r="5"><title>{E(x.cand)}: defense {x.defense:+.2f}, offense {x.offense:+.2f}, carries over {x.yoy:.2f}</title></circle>')
    if x.cand in SHORT:
        anchor = "end" if X(x.defense) > W * 0.72 else "start"
        o.append(f'<text class="pl" x="{X(x.defense) + (-8 if anchor == "end" else 8):.1f}" y="{Y(x.yoy) + 4:.1f}" text-anchor="{anchor}">{E(SHORT[x.cand])}</text>')
ch1 = f'<svg class="sc" viewBox="0 0 {W} {H}" role="img" aria-label="candidates">{"".join(o)}</svg>'
k1 = '<div class="key"><span><i class="g3"></i>Defense signal (keep)</span><span><i class="g1"></i>Style trait</span><span><i class="g2"></i>Out</span><span><i class="g4"></i>Point margin (reference)</span></div>'

# chart 2: ratio (draft gap ÷ weekly swing) — player slots vs TEAM options
bs = DG["gfc|8"]["by_slot"]
pl = [(f"Player slot: {s}", bs[s]["avg_vor"] / (np.sqrt(3) * 0 + 9.5), "g1") for s in ("C", "G", "F")]
pl = [("Player slot: C", 0.66, "g1"), ("Player slot: G", 0.30, "g1"), ("Player slot: F", 0.18, "g1")]
pick = [("A: tiers only", "week total"), ("D: commissioner's (<100 +10, <110 +5)", "week total"), ("E: (125 − opp points) / 2", "week total"),
        ("E: (125 − opp points) / 2", "week avg ×3"), ("F: (125 − def rating) / 2", "week total"), ("G: E + 0.25 / turnover forced", "week total"),
        ("E: (125 − opp points) / 2", "best game")]
tm = []
for s, f in pick:
    r_ = CA[(CA.struct == s) & (CA.form == f)].iloc[0]
    tm.append((f"TEAM {s.split(':')[0]}, {f}", float(r_.ratio8), "g3" if f != "best game" else "g2"))
rows = pl + tm
lw, rw, rh, t0 = 250, 50, 26, 26
W2 = 620
H2 = t0 + rh * len(rows) + 30
Xs = lambda v: lw + v / 0.7 * (W2 - lw - rw)  # noqa: E731
o = [f'<text class="mt" x="{lw}" y="16">Draft gap per unit of weekly swing (8 teams)</text>']
for v in (0, 0.2, 0.4, 0.6):
    o.append(f'<line class="grid" x1="{Xs(v):.1f}" x2="{Xs(v):.1f}" y1="{t0}" y2="{t0 + rh * len(rows)}"/><text class="ax" x="{Xs(v):.1f}" y="{t0 + rh * len(rows) + 15}" text-anchor="middle">{v:.1f}</text>')
for i, (lab, v, cls) in enumerate(rows):
    y = t0 + i * rh + 5
    o.append(f'<text class="pl" x="{lw - 8}" y="{y + 12}" text-anchor="end" style="font-weight:400">{E(lab)}</text>'
             f'<rect class="{cls}" x="{Xs(0):.1f}" y="{y}" width="{max(Xs(v) - Xs(0), 1.5):.1f}" height="16" rx="3"/>'
             f'<text class="ax" x="{Xs(v) + 6:.1f}" y="{y + 12}">{v:.2f}</text>')
ch2 = f'<svg class="sc" viewBox="0 0 {W2} {H2}" role="img" aria-label="ratio">{"".join(o)}</svg>'

ev_tbl = table(["Candidate", "Real spread between teams", "One game's swing", "Tracks defense", "Tracks offense", "Tracks point margin", "Carries over"],
               [[E(x.cand), f"{x.true_sd:.2f}", f"{x.game_sd:.2f}", f"{x.defense:+.2f}", f"{x.offense:+.2f}", f"{x.margin:+.2f}", f"{x.yoy:.2f} / {x.yoy26:.2f}"] for x in EV.itertuples()])
ca_tbl = table(["Structure", "Weekly form", "Mean", "Weekly swing", "Avg starter over repl. 4 / 8 / 12", "Best over repl. 4 / 8 / 12", "Gap ÷ swing"],
               [[E(x.struct), E(x.form), f"{x.mean:.1f}", f"±{x.wk_sd:.1f}", f"+{x.avg4:.1f} / <b>+{x.avg8:.1f}</b> / +{x.avg12:.1f}",
                 f"+{x.best4:.1f} / <b>+{x.best8:.1f}</b> / +{x.best12:.1f}", f"{x.ratio8:.2f}"] for x in CA.itertuples()])
tgt = table(["Setup (8 teams)", "G avg starter over repl.", "F", "C", "FLX"],
            [[n, *[f"+{DG[k]['by_slot'][s]['avg_vor']:.1f}" if s in DG[k]["by_slot"] else "—" for s in ("G", "F", "C", "FLX")]]
             for n, k in (("1 G / 1 F / 1 C", "gfc|8"), ("1 G / 1 F / 1 C / 1 FLX", "gfcx|8"))])
ff = table(["Fantasy football D/ST", "Points"], [["Points allowed 0", "+10"], ["1–6", "+7"], ["7–13", "+4"], ["14–20", "+1"], ["21–27", "0"], ["28–34", "−1"],
                                                ["35+", "−4"], ["Interception / fumble recovery", "+2"], ["Sack", "+1"], ["Defensive or return TD", "+6"],
                                                ["Safety / blocked kick", "+2"]])

page = f"""<title>TEAM Slot Scoring</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..100,500..800&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
{style.replace("</style>", ".g4 {{ fill:var(--ink-2); }} .key i.g4 {{ background:var(--ink-2); }}</style>".replace("{{", "{").replace("}}", "}"))}
<div class="wrap">
<div class="eyebrow">Fantasy 2026-27 · TEAM slot rework</div>
<h1>TEAM slot scoring</h1>
<p class="dim">TEAM is being rebuilt as the slot where team defense shows, like D/ST in fantasy football. Point margin is out: it's offense plus defense, and it made TEAM worth twice a center. Data: every team-game '22–'26 (NBA.com team game logs). Seasons are named by the year they end.</p>

<section id="goal"><div class="n">1</div><div><h2>What TEAM should be worth</h2>
<p class="claim">About as much as a player slot: the average starting TEAM +3 to +5 over the best TEAM left, the best TEAM +6 to +10. Not Jokić-level.</p>
<p>From the draft guide: how much a typical starter at each player slot beats the best player left over (PROJ MAX, 8 teams). One point a week is worth about 2% of weekly win probability.</p>
{tgt}
<p class="cap">Point margin, the old scoring, gave the average starting TEAM +9.8 to +11.8 — about twice a center and three to six times a guard or forward.</p>
</div></section>

<section id="ff"><div class="n">2</div><div><h2>The fantasy football template</h2>
<p class="claim">D/ST scores a base from points allowed in tiers, plus takeaways and sacks, plus rare big-play bonuses.</p>
<div class="pair">{ff}<div><p>The NBA versions brainstormed: points allowed (raw, in tiers, or per 100 possessions); the commissioner's held-under-100 (+10) and held-under-110 (+5); turnovers forced, steals, blocks; holding the opponent down in the paint, in transition, on second chances, from 3; no opposing scorer reaching 30; and hustle stats (deflections, charges, contests), which aren't pulled yet.</p></div></div>
</div></section>

<section id="cand"><div class="n">3</div><div><h2>Which stats are defense</h2>
<p class="claim">Points allowed is the defense signal. Turnovers forced is a real trait but a style, not quality. Opponent 3P% is luck, and "no 30-point scorer" is about the opponent's stars.</p>
{k1}
<div class="pair">{ch1}<div><p>Right side = moves with a team's real defensive rating. Up = a team's season average repeats the next season, so a TEAM can be drafted on it.</p>
<p>Opponent points tracks defense at 0.89 and offense at only 0.14. The under-100 / under-110 bonuses (0.80 / 0.87) and opponent paint points (0.76) do too. Turnovers forced barely tracks defense (0.3) but repeats (0.58): disruptive defenses. Point margin tracks offense at 0.82, which is why it's out.</p></div></div>
{ev_tbl}
<p class="cap">Seasons '22–'25 for everything except the second carry-over number ('25 → '26). Real spread = how much team season averages differ once game-to-game luck is removed.</p>
</div></section>

<section id="size"><div class="n">4</div><div><h2>Sizing it</h2>
<p class="claim">Team defense is noisy game to game: however it's scored, its draft gap per unit of weekly swing lands between a forward slot and a guard slot. TEAM reaches the target importance by its scale, and swings a bit more than a player slot.</p>
{ch2}
<p>Scoring a team's <b>best defensive game of the week</b> washes it out: every team has a good night some time in a week, so the average starter is only +0.5 over replacement. The <b>weekly total</b> keeps team differences, and games played that week count, like a player's extra chances.</p>
<p><b>Leading option:</b> (125 − opponent points) / 2 per game, totaled over the week — the best gap-to-swing ratio and the simplest. At 8 teams the average starting TEAM is +2.9 over replacement and the best +6.4, with a weekly swing of ±13: already close to target. Turnovers forced and the paint bonus add more noise than signal. The commissioner's under-100 / under-110 bonuses work about as well as football-style tiers.</p>
{ca_tbl}
<p class="cap">Each NBA team projected from its prior season (keeping 60% of its gap from average — how much team margin repeats), then compared with the best team left over. Fantasy weeks under the league's rules, '23–'26. Tiers (A): under 95 +12, 95–104 +8, 105–114 +4, 115–124 0, 125+ −4.</p>
</div></section>

<section id="open"><div class="n">5</div><div><h2>Commissioner's calls</h2>
<ol><li>Weekly total or weekly average: does a 4-game week deserve more TEAM points?</li>
<li>Raw points allowed (simple, rewards slow teams) or per 100 possessions (pure defense, separates teams less)?</li>
<li>Turnovers forced at a small weight, for flavor?</li>
<li>Pull hustle stats (deflections, charges, contests) to test them — about 170 requests a season.</li></ol>
</div></section>
</div>
"""
open(S + "team_slot_scoring.html", "w").write(page)
print("ok", len(page))
