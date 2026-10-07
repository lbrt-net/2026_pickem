# Sections 13–16, exec'd inside build_report4.py after sections912.py.
D13 = json.load(open(S + "sec1316.json"))


def xy(rows, xk, yk, xlo, xhi, ylo, yhi, xlab, ylab, labels, groups, title, w=520, h=420, tick=1.0):
    l, r, t, b = 46, 14, 26, 44
    X = lambda v: l + (v - xlo) / (xhi - xlo) * (w - l - r)  # noqa: E731
    Y = lambda v: t + (yhi - v) / (yhi - ylo) * (h - t - b)  # noqa: E731
    o = [f'<text class="mt" x="{l}" y="14">{E(title)}</text>']
    v = xlo
    while v <= xhi + 1e-9:
        o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{t}" y2="{h - b}"/><text class="ax" x="{X(v):.1f}" y="{h - b + 15}" text-anchor="middle">{v:+g}</text>')
        v += tick
    v = ylo
    while v <= yhi + 1e-9:
        o.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v:+g}</text>')
        v += tick
    o.append(f'<text class="ax" x="{(l + w - r) / 2:.1f}" y="{h - 8}" text-anchor="middle">{E(xlab)}</text>'
             f'<text class="ax" x="12" y="{(t + h - b) / 2:.1f}" transform="rotate(-90 12 {(t + h - b) / 2:.1f})" text-anchor="middle">{E(ylab)}</text>')
    for p in rows:
        xv, yv = min(max(p[xk], xlo), xhi), min(max(p[yk], ylo), yhi)
        o.append(f'<circle class="pt {groups[p["grp"]]}" cx="{X(xv):.1f}" cy="{Y(yv):.1f}" r="{3 + min(p["val"], 45) / 15:.1f}"><title>{E(p["name"])} ({p["grp"]})</title></circle>')
    for p in rows:
        if p["name"] in labels:
            xv, yv = min(max(p[xk], xlo), xhi), min(max(p[yk], ylo), yhi)
            anchor = "end" if X(xv) > w * 0.7 else "start"
            o.append(f'<text class="pl" x="{X(xv) + (-8 if anchor == "end" else 8):.1f}" y="{Y(yv) + 4:.1f}" text-anchor="{anchor}">{E(p["name"].split()[-1] if p["name"].split()[-1] not in ("Jr.", "III") else p["name"].split()[-2])}</text>')
    return f'<svg class="sc" viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}">{"".join(o)}</svg>'


# ---------------- 13. positions
PG = {"G": "g1", "F": "g2", "C": "g3"}
pkey = '<div class="key"><span><i class="g1"></i>G</span><span><i class="g2"></i>F</span><span><i class="g3"></i>C</span><span>dot size = \'26 weekly best game</span></div>'
LAB13 = {"Nikola Jokić", "Luka Dončić", "Shai Gilgeous-Alexander", "Victor Wembanyama", "Giannis Antetokounmpo", "Anthony Edwards", "Stephen Curry",
         "Bam Adebayo", "Scottie Barnes", "Evan Mobley", "Jayson Tatum", "Cade Cunningham", "Desmond Bane", "Deni Avdija"}
sc13 = xy(D13["pts"], "create", "big", -2.5, 2.5, -2, 4, "creation score (AST%, share of shots from 3, shorter)", "size score (height, REB%, blocks)",
          LAB13, PG, "Every '26 player by role: size vs creation")
chk_tbl = table(["Player", "Box-score start position", "Role position", "Size", "Creation"],
                [[E(c["name"]), c["old"], f"<b>{c['new']}</b>", f"{c['big']:+.2f}", f"{c['create']:+.2f}"] for c in D13["chk"]])
b8 = D13["bal"]
bal_tbl = table(["Teams", "G", "F", "C", "FLX", "TEAM"],
                [[N, *[f"{b8[N]['new'][k]:.1f}" for k in ("G", "F", "C", "FLX", "TEAM")]] for N in ("8", "10", "12")])
moved_tbl = table(["Top-60 player", "Box-score position", "Role position", "Why"], [
    ["Desmond Bane", "G", "<b>F</b>", "a shooter, not the creator"], ["Amen Thompson", "G", "<b>F</b>", "rebounds and finishes, rarely shoots 3s"],
    ["Brandon Miller", "G", "<b>F</b>", "6'9\" wing"], ["Dyson Daniels", "G", "<b>F</b>", "defender, not a creator"],
    ["Deni Avdija", "F", "<b>G</b>", "runs the offense"], ["Kon Knueppel", "F", "<b>G</b>", "shooter who creates"]])
TP = D13["top_pos"]
pos_tbls = "".join(f"<div><p><b>{s}</b></p>" + table(["#", "Player", "PROJ AVG"], [[str(x["rank"]), E(x["name"]), f"<b>{x['fp']:.1f}</b>"] for x in TP[s]]) + "</div>"
                   for s in ("G", "F", "C"))
_pos27 = {c["name"]: c["pos"] for c in D13["cards"]}
_chk = {p["name"]: p for p in D13["pts"]}
e13 = table(["#", "Player", "2026-27 position", "Size", "Creation"],
            [[str(i + 1), E(c["name"]), f"<b>{c['pos']}</b>", f"{_chk[c['name']]['big']:+.2f}" if c["name"] in _chk else "—",
              f"{_chk[c['name']]['create']:+.2f}" if c["name"] in _chk else "—"] for i, c in enumerate(D13["cards"])])


# ---------------- 14. player cards
def yoy(v, ref, d=1):
    if v is None:
        return "—"
    s = f"{v:.{d}f}"
    if ref:
        s += f' <span class="yoy">{(v / ref - 1) * 100:+.0f}%</span>'
    return s


CARD_ST = [("mpg", "MIN"), ("pts", "PTS"), ("reb", "REB"), ("ast", "AST"), ("stl", "STL"), ("blk", "BLK"), ("tov", "TOV"), ("fg3m", "3PM"), ("fp", "FP/G")]


def card(c):
    s26 = c["seasons"]["2025-26"]
    rows = []
    for s in ("2023-24", "2024-25", "2025-26"):
        x = c["seasons"][s]
        if not x:
            rows.append([f"'{s[-2:]}", "0", "—"] + ["—"] * len(CARD_ST))
            continue
        rows.append([f"'{s[-2:]}", str(x["gp"]), pc(c["usg"][s])] + [f1(x[k]) if k not in ("stl", "blk", "tov") else f"{x[k]:.2f}" for k, _ in CARD_ST])
    p = c["proj"]
    rows.append(["<b>'27 proj</b>", "", f"<b>{pc(p['usg'])}</b>"] + [f"<b>{yoy(p[k], s26[k] if s26 else None, 2 if k in ('stl', 'blk', 'tov') else 1)}</b>" for k, _ in CARD_ST])
    note = ", ".join(x for x in [f"age {c['age']:.0f}", "new team" if not c["stayed"] else "", f"base '{c['base'][-2:]}" if c["base"] != "2025-26" else "", c["flags"]] if x)
    return (f'<div class="card"><h3>{E(c["name"])} <span class="tag">{c["team"]} · {c["pos"]} · #{c["rank"]}</span></h3><p class="cap">{E(note)}</p>'
            + table(["Season", "GP", "USG"] + [h for _, h in CARD_ST], rows) + "</div>")


cards_html = "".join(card(c) for c in D13["cards"])


# ---------------- 15. board
def bcell(v, ref, d=1):
    return yoy(v, ref, d)


BD = D13["board"]
board_tbl = table(["#", "Player", "Team", "Pos", "Age", "'26 FP/G (GP)", "PROJ AVG", "MIN", "PTS", "REB", "AST", "Flags"],
                  [[str(x["rank"]), E(x["name"]), x["team"], x["pos"], f"{x['age']:.0f}" if x["age"] else "—",
                    f"{x['a26']['fp']:.1f} ({x['a26']['gp']})" if x["a26"] else ("rookie" if x["kind"] != "vet" else "— (0)"),
                    f"<b>{bcell(x['fp'], x['a26']['fp'] if x['a26'] else None)}</b>",
                    bcell(x["mpg"], x["a26"]["mpg"] if x["a26"] else None), bcell(x["pts"], x["a26"]["pts"] if x["a26"] else None),
                    bcell(x["reb"], x["a26"]["reb"] if x["a26"] else None), bcell(x["ast"], x["a26"]["ast"] if x["a26"] else None), E(x["flags"])]
                   for x in BD])

# ---------------- 16. open problems
open_html = """<ul>
<li><b>Role changes are the biggest miss.</b> Rollins, Tyson and Sheppard up; Sochan, Mogbo, Tyus Jones and Cam Thomas down. Next to try: roster competition, meaning his depth rank at his position on the target roster.</li>
<li><b>Injury type.</b> An Achilles (Haliburton, Tatum, Lillard) or a chronic knee (Embiid, '26: 32.1 projected, 28.0 actual) takes something off a player even after he's back. Nothing in the projection knows that.</li>
<li><b>Availability.</b> Games played and the chance he plays this week belong to their own model: an injury report feed, plus how long each injury type keeps players out.</li>
<li><b>PROJ MAX and dispersion.</b> The weekly best game needs the spread of his games, the number of games that week, opponent and home/away. Running log in <code>DISPERSION.md</code>.</li>
<li><b>EPM flag is temporary.</b> It comes from a hand-entered partial '26 table and can't be tested on '26. Replace it with a pulled advanced stat.</li>
<li><b>Rookies at the ends.</b> Top-4 picks who play 33+ minutes (Flagg, Edgecombe, Knueppel) and tall rookies who sit (Yang, Maluach). No fix beat the current model on past classes.</li>
<li><b>Forward is the flat slot.</b> With one position each, the 8th-best F is only 1.3 better than the best F left over (G 5.9, C 5.3). Balance goes through the league guides.</li>
<li><b>TEAM slot</b> (weekly margin total) is worth 9.8–11.8 over replacement, more than any player slot. It needs its own scaling.</li>
<li><b>Usage for players who change teams</b> regresses to the middle and isn't modeled. So is shot-mix development (bigs moving out to 3 faster than their trend).</li>
<li><b>No projection</b> for about 60 undrafted rookies, two-ways and a few returners. They stay in the draft list with a blank.</li>
<li><b>Draft page wiring</b> (PROJ AVG column, the pool, the glossary) is written but not tested or committed.</li>
<li>Later: win probability for a fantasy team (simulated draws from similar past players), auction values.</li>
</ul>"""

sec1316_html = f"""
<section id="positions"><div class="n">13</div><div><h2>Positions</h2>
<p class="claim">Every player gets one position, G, F or C, from how he plays, not how he's listed.</p>
<p>Two scores from '26 stats. Size: height, rebounding share and blocks. Creation: assist share, share of shots from 3, and being shorter. The top 20% by size are C. Of the rest, the top 40% by creation are G. Everyone else is F. Overrides win: Giannis, Barnes and Mobley are F. Rookies and players with no '26 stats get the first letter of their roster position.</p>
{pkey}
<div class="pair">{sc13}<div>{chk_tbl}</div></div>
<h3>What changed from box-score positions</h3>
<p>The app's old rule used each player's most frequent box-score starting position. Most players land in the same place either way. Six of the top 60 moved:</p>
{moved_tbl}
<h3>Slot balance</h3>
<p>Value of a slot = the average starter at that slot minus the best player left over for it, using '26 weekly best games, with the top players filling G, F and C first, then FLX. TEAM is an NBA team's weekly margin total.</p>
{bal_tbl}
<p class="cap">Forward is flat: so many good players are forwards that the one left over is nearly as good as the starters. Guard and center are worth about the same. TEAM is worth more than any player slot. Both are for the league guides to settle.</p>
<h3>2026-27: the top 12 at each position</h3>
<div class="pair three">{pos_tbls}</div>
<h3>2026-27: the random eight</h3>{e13}
</div></section>

<section id="cards"><div class="n">14</div><div><h2>Player cards</h2>
<p class="claim">The random eight, season by season: what he did, and what he's projected to do. The percentage is the change from '26.</p>
{cards_html}
</div></section>

<section id="board"><div class="n">15</div><div><h2>2026-27 board</h2>
<p class="claim">The top 50 by PROJ AVG. Each projection shows its change from what he did in '26.</p>
{board_tbl}
<p class="cap">Per game, in games he plays. A player who missed all of '26 has no percentage. Flags: injured in '26, new team, EPM ≤ −2.5 (minutes cut), late jump in '26.</p>
</div></section>

<section id="open"><div class="n">16</div><div><h2>Open problems</h2>
{open_html}
</div></section>
"""
