"""Builds team_slot_scoring.html from TEAM_SCORING.md's data: draft 1, all 30 teams on 2025-26, defensive rating vs
each category (scatter grid, every team labeled), and the stats table."""
import html, json, re
import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
E = html.escape
style = re.search(r"<style>.*?</style>", open(S + "per_game_projections.html").read(), re.S).group(0)
D1 = json.load(open(S + "team_draft1.json"))
SH = json.load(open(S + "team_show.json"))
T = pd.DataFrame(D1["teams"]).set_index("TEAM_ABBREVIATION")
TS = pd.DataFrame(SH["teams"]).set_index("TEAM_ABBREVIATION")
md = open("/Users/allan/PycharmProjects/2026_pickem/TEAM_SCORING.md").read()


def table(head, rows, cls="r"):
    return (f'<div class="tw"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


# bar chart: weekly score, all 30
rows = list(T.itertuples())
lw, rw, rh, t0, W = 60, 60, 20, 24, 560
H = t0 + rh * len(rows) + 26
hi = 50
Xb = lambda v: lw + v / hi * (W - lw - rw)  # noqa: E731
o = [f'<text class="mt" x="{lw}" y="15">Average weekly score (best game of the week), 2025-26</text>']
for v in range(0, hi + 1, 10):
    o.append(f'<line class="grid" x1="{Xb(v):.1f}" x2="{Xb(v):.1f}" y1="{t0}" y2="{t0 + rh * len(rows)}"/><text class="ax" x="{Xb(v):.1f}" y="{t0 + rh * len(rows) + 15}" text-anchor="middle">{v}</text>')
for i, r in enumerate(rows):
    y = t0 + i * rh + 3
    o.append(f'<text class="pl" x="{lw - 8}" y="{y + 11}" text-anchor="end">{r.Index}</text><rect class="g1" x="{Xb(0):.1f}" y="{y}" width="{Xb(r.week_best) - Xb(0):.1f}" height="14" rx="3">'
             f'<title>{r.Index}: weekly {r.week_best:.1f}, game {r.game:.1f}, held under 105 in {100 * r.u105:.0f}%</title></rect>'
             f'<text class="ax" x="{Xb(r.week_best) + 5:.1f}" y="{y + 11}">{r.week_best:.1f}</text>')
bars = f'<svg class="sc" viewBox="0 0 {W} {H}" role="img" aria-label="weekly score by team">{"".join(o)}</svg>'

ttbl = table(["#", "Team", "Weekly score", "Average game", "Points allowed", "Held under 100", "Under 105", "Under 110", "Turnovers forced", "Defensive rating"],
             [[str(i + 1), r.Index, f"<b>{r.week_best:.1f}</b>", f"{r.game:.1f}", f"{r.opp_pts:.1f}", f"{100 * r.u100:.0f}%", f"{100 * r.u105:.0f}%", f"{100 * r.u110:.0f}%",
               f"{r.tov:.1f}", f"{r.dr:.1f}"] for i, r in enumerate(rows)])


# scatter grid: defensive rating (x, better to the right) vs each category, every team labeled
def mini(col, lab, better, corr):
    x = -TS.dr
    y = TS[col]
    pct = col.startswith("U") or col.endswith("PCT")
    w, h, l, r, t, b = 300, 230, 40, 10, 34, 30
    xl, xh = x.min() - 0.5, x.max() + 0.5
    pad = (y.max() - y.min()) * 0.08
    yl, yh = y.min() - pad, y.max() + pad
    X = lambda v: l + (v - xl) / (xh - xl) * (w - l - r)  # noqa: E731
    Y = lambda v: t + (yh - v) / (yh - yl) * (h - t - b)  # noqa: E731
    o = [f'<text class="mt" x="{l}" y="14">{E(lab)}</text><text class="ax" x="{l}" y="27">goes with good defense: {corr:.2f} · {"lower" if better == "lower" else "higher"} is better</text>']
    for v in np.linspace(yl, yh, 4):
        o.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{l - 4}" y="{Y(v) + 3:.1f}" text-anchor="end">{(f"{100 * v:.0f}%" if pct else f"{v:.0f}" if abs(v) >= 10 else f"{v:.1f}")}</text>')
    o.append(f'<text class="ax" x="{(l + w - r) / 2:.1f}" y="{h - 6}" text-anchor="middle">better defense →</text>')
    for k in TS.index:
        cls = "g3" if k in list(T.index[:5]) else "g1"
        o.append(f'<circle class="pt {cls}" cx="{X(x[k]):.1f}" cy="{Y(y[k]):.1f}" r="3"/><text class="ax" x="{X(x[k]) + 4:.1f}" y="{Y(y[k]) - 3:.1f}" style="font-size:8.5px">{k}</text>')
    return f'<svg class="sc" viewBox="0 0 {w} {h}" role="img" aria-label="{E(lab)}">{"".join(o)}</svg>'


LAB = {"OPP_PTS": "Opponent points per game", "U100": "Held under 100 (share of games)", "U105": "Held under 105", "U110": "Held under 110",
       "STL": "Steals per game", "BLK": "Blocks per game", "OPP_TOV": "Turnovers forced per game", "OPP_PTS_PAINT": "Opponent paint points",
       "OPP_PTS_FB": "Opponent fast-break points", "OPP_PTS_2ND_CHANCE": "Opponent second-chance points", "OPP_EFG_PCT": "Opponent shooting (eFG%)",
       "OPP_FG3_PCT": "Opponent 3P%", "DREB_PCT": "Defensive rebound %"}
grid = "".join(mini(c, LAB[c], s, SH["corr"][c]) for _, c, s in SH["cats"] if c in LAB and c in TS)


def md_section(title):
    m = re.search(rf"## {re.escape(title)}\n(.*?)(?=\n## |\Z)", md, re.S)
    return m.group(1).strip() if m else ""


def md_to_html(txt):
    out = []
    for block in txt.split("\n\n"):
        if block.startswith("|"):
            lines = [l for l in block.splitlines() if not set(l.replace("|", "").strip()) <= set("-")]
            head = [c.strip() for c in lines[0].strip("|").split("|")]
            body = [[re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", c.strip()) for c in l.strip("|").split("|")] for l in lines[1:]]
            out.append(table(head, body))
        elif block.lstrip().startswith("- "):
            items = [re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", re.sub(r"`(.+?)`", r"\1", E(i[2:]).replace("&quot;", '"'))) for i in re.split(r"\n(?=- )", block.strip())]
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        elif block.strip():
            out.append("<p>" + re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", E(block.strip()).replace("&quot;", '"').replace("&#x27;", "'")) + "</p>")
    return "".join(out)


page = f"""<title>TEAM Slot Scoring</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..100,500..800&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
{style.replace("</style>", ".pair.three {{ grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }}</style>".replace("{{", "{").replace("}}", "}"))}
<div class="wrap">
<div class="eyebrow">Fantasy 2026-27 · TEAM slot</div>
<h1>TEAM slot scoring</h1>
<p class="dim">Every roster has one TEAM spot: you draft a whole NBA team, like a defense in fantasy football. Seasons are named by the year they end ('26 = 2025-26).</p>
<section><div class="n">1</div><div><h2>The idea</h2>{md_to_html(md_section("The idea"))}</div></section>
<section><div class="n">2</div><div><h2>How a TEAM scores (draft 2)</h2>{md_to_html(md_section("How a TEAM scores (draft 2, current)"))}</div></section>
<section><div class="n">3</div><div><h2>Why these</h2>{md_to_html(md_section("Why these"))}</div></section>
<section><div class="n">4</div><div><h2>Every team on 2025-26</h2>
<p class="claim">The best defenses score the most and have the most big weeks: OKC, Detroit and Boston on top; Chicago, Memphis and Utah at the bottom.</p>
<div class="pair">{bars}<div><p>Average weekly score = each team's best game of the week, averaged over the season. OKC had a big week (30+) in two of every three weeks; the bottom teams in one week in ten or twenty.</p></div></div>
{md_to_html(md_section("What it looks like on 2025-26"))}</div></section>
<section><div class="n">5</div><div><h2>Defensive rating vs each stat</h2>
<p class="claim">Each chart: the 30 teams, better defense to the right (defensive rating = points allowed per 100 possessions). If the dots run in a line, the stat follows good defense. Green = the top five TEAMs under draft 2.</p>
<div class="pair three">{grid}</div></div></section>
<section><div class="n">6</div><div><h2>What else we looked at</h2>{md_to_html(md_section("What else we looked at"))}</div></section>
<section><div class="n">7</div><div><h2>Coming next</h2>{md_to_html(md_section("Coming next"))}</div></section>
</div>
"""
open(S + "team_slot_scoring.html", "w").write(page)
print("ok", len(page))
