import json, sys, re
S = sys.argv[1]; W2 = f'{S}/work3'; GROUP = sys.argv[2] if len(sys.argv) > 2 else 'Scoring'
src = open(f'{S}/m_ballot.html').read()
r = json.load(open(f'{W2}/report.json')); T = r['teams']
WEEKS = tuple(__import__('json').loads(__import__('os').environ.get('MS_WEEKS', '[1, 2, 3, 4]')))
MIP = GROUP == "Most improved"; ROOK = GROUP == "Top rookie"; SIX = GROUP == "Sixth man"
GRP = {"Scoring": ("pts","fg3m","clutch_pts","fgx","ftx","blkd"), "Playmaking": ("ast","tov"), "Boards": ("oreb","dreb"), "Stocks": ("stl","blk")}
CATS = {"Most improved": [], "Top rookie": [(k, k, 1.0) for ks in GRP.values() for k in ks], "Sixth man": [(k, k, 1.0) for ks in GRP.values() for k in ks], "Scoring": [("pts","PTS",1.0),("fg3m","3PM",0.5),("clutch_pts","Clutch pts",2.0),("fgx","Missed FG",-0.5),("ftx","Missed FT",-1.0),("blkd","Got blocked",-0.5)],
        "Playmaking": [("ast","AST",1.0),("tov","Turnovers",-2.0)],
        "Boards": [("oreb","Off reb",1.5),("dreb","Def reb",0.5)],
        "Stocks": [("stl","STL",2.0),("blk","BLK",1.5)]}[GROUP]
agg = {}
for w in WEEKS:
    for t in json.load(open(f'{W2}/f3/wa{w}.json')).values():
        for e in t['entries']:
            if e['kind']=='player' and e.get('games_done') and e.get('breakdown') and e.get('week_score') is not None:
                a = agg.setdefault(e['id'], {})
                for k, _, _ in CATS: a[k] = a.get(k, 0) + e['breakdown'].get(k, 0)
win = r['sixth'][0] if GROUP == 'Sixth man' else r['rookie'][0] if ROOK else r['mip'][0] if MIP else r['mvp'][GROUP][0]; me = agg.get(win['id'], {}); tc = T.get(win['team'] or '', {}).get('color', '#30363d')
def rank(k):  # by raw count, most first
    v = sorted((a.get(k,0) for a in agg.values()), reverse=True); return v.index(me.get(k,0)) + 1
ordn = lambda n: f"{n}{'th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"
cells = [(lab, round(me.get(k,0)/pt), me.get(k,0), rank(k)) for k, lab, pt in CATS]
fmt = lambda v: ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):g}"
# V1 box-score table
V1 = ('<table class="bx"><tr><th></th>' + ''.join(f'<th>{c[0]}</th>' for c in cells) + '</tr>'
      '<tr class="raw"><td></td>' + ''.join(f'<td>{c[1]}</td>' for c in cells) + '</tr>'
      '<tr><td class="rl">Fantasy</td>' + ''.join(f'<td class="{"g" if c[2]>0 else "b"}">{fmt(c[2])}</td>' for c in cells) + '</tr>'
      '<tr><td class="rl">League</td>' + ''.join(f'<td>{ordn(c[3])}</td>' for c in cells) + '</tr></table>')
# V2 rank-led: each category a column, rank big
N = len(agg)
sup = lambda n: f"{n}<sup>{ordn(n)[len(str(n)):]}</sup>"
def PG(pid, season="'27"):  # the player page's season row: actual-only, percentiles vs 20+ games / 20+ MPG / 500+ min (scaled)
    return next(s for s in json.load(open(f'{W2}/page_{pid}.json'))['seasons'] if s['season'] == season)
def pct(k):
    return PG(win['id'])['pct'][k]
def _old_pct(k):
    me_v = me.get(k,0); vals = [a.get(k,0) for a in agg.values()]
    lo = sum(v < me_v for v in vals); eq = sum(v == me_v for v in vals) - 1
    return min(99, int(100 * (lo + eq / 2) / (N - 1)))
cells = [c + (pct(k),) for c, (k, _, _) in zip(cells, CATS)]
if False and GROUP == "Playmaking":
    cnt = lambda a, k, p: a.get(k, 0) / p
    pool = [cnt(a,"ast",1)/max(1,cnt(a,"tov",-2)) for a in agg.values() if cnt(a,"ast",1) >= 20]
    mine = cnt(me,"ast",1)/max(1,cnt(me,"tov",-2))
    p = min(99, int(100*sum(v < mine for v in pool)/max(1,len(pool)-1)))
    cells.append(("AST : TO", f"{mine:.1f}", 1, 0, p))
def combo(label, parts):  # third cell for two-stat awards: the combined count, percentile among everyone
    tot = lambda a: sum(a.get(k, 0) / pt for k, pt in parts)
    pool = [tot(a) for a in agg.values()]; mine = tot(me)
    p = min(99, int(100*(sum(v < mine for v in pool) + (sum(v == mine for v in pool) - 1)/2)/max(1, len(pool)-1)))
    cells.append((label, f"{mine:g}", 1, 0, p))
pass  # if GROUP == "Boards": combo("Total reb", (("oreb", 1.5), ("dreb", .5)))
pass  # if GROUP == "Stocks": combo("STL + BLK", (("stl", 2.0), ("blk", 1.5)))
V2 = f'<div class="rk2" style="--n:{len(cells)}">' + ''.join(f'<div class="c {"g" if c[2]>0 else "b"}"><span class="l">{c[0]}</span><b>{sup(c[4])}</b><span class="m"><u style="width:{c[4]}%"></u><i style="left:{c[4]}%"></i></span><span class="v">{c[1]}{"" if c[0] in ("AST : TO","Total reb","STL + BLK") else f" <em>{fmt(c[2])}</em>"}</span></div>' for c in cells) + '</div>'
if ROOK:  # the four wheel groups: his points from each, percentile among every player with a weekly best
    gs = lambda a, ks: sum(a.get(k, 0) for k in ks)
    def pc(pool, x):
        lo = sum(v < x for v in pool); eq = sum(v == x for v in pool) - 1
        return min(99, int(100 * (lo + eq / 2) / (len(pool) - 1)))
    wh = {x['k']: x for x in json.load(open(f"{W2}/page_{win['id']}.json"))['header']['wheel']}  # the player page's wheel (one source)
    row = PG(win['id']); cells = [(n, row['pct']['wheel_' + n], round(wh[n]['v'], 1)) for n in GRP]
    V2 = '<div class="rk2" style="--n:4">' + ''.join(f'<div class="c {"g" if c[2] >= 0 else "b"}"><span class="l">{c[0]}</span><b>{sup(c[1])}</b><span class="m"><u style="width:{c[1]}%"></u><i style="left:{c[1]}%"></i></span><span class="v"><em>{fmt(c[2])}</em></span></div>' for c in cells) + '</div>'
    V1 = V2; print(cells)
if SIX:  # overall MAX (percentile, same pool as Most improved), MAX on the bench, the starter he could have replaced
    import statistics as st
    best = {}
    for w in WEEKS:
        for pid, gg in json.load(open(f'{W2}/ws{w}.json')).items():
            v = [x for x in gg.values() if x is not None]
            if v: best.setdefault(pid, {})[w] = max(v)
    nowp = [st.mean(b.values()) for b in best.values() if len(b) >= 2]
    def pc(pool, x):
        lo = sum(v < x for v in pool); eq = sum(v == x for v in pool) - 1
        return min(99, int(100 * (lo + eq / 2) / (len(pool) - 1)))
    pos = {p['id']: p.get('position') for p in json.load(open(f'{W2}/players_scenario_live.json'))}[win['id']]
    lows = []
    for w in win['weeks']:  # each week he sat: the lowest starter in his slot or FLEX on his team
        es = json.load(open(f'{W2}/f3/wa{w}.json'))[win['team']]['entries']
        v = [e['week_score'] for e in es if e['slot'] in (pos, 'FLEX') and e.get('week_score') is not None]
        if v: lows.append(min(v))
    mx = st.mean(best[win['id']].values()); bm = st.mean(win['weeks'].values()); lo = st.mean(lows)
    cell = lambda l, big, bar, v, c: f'<div class="c {c}"><span class="l">{l}</span><b>{big}</b>' + (f'<span class="m"><u style="width:{bar}%"></u><i style="left:{bar}%"></i></span>' if bar is not None else '<span class="m" style="visibility:hidden"></span>') + f'<span class="v">{v}</span></div>'
    p = PG(win['id'])['pct']['max']
    cell = lambda l, big, bar, v: (f'<div class="c g"><span class="l">{l}</span><b>{big}</b>'
        + (f'<span class="m"><u style="width:{bar}%"></u><i style="left:{bar}%"></i></span>' if bar is not None else '<span class="m nb"></span>')
        + f'<span class="v">{v}</span></div>')
    V2 = ('<div class="rk2 six" style="--n:3">'
          + cell("MAX", sup(p), p, f"{mx:.1f}") + '<div class="bench"><span class="bl">Bench weeks</span>' + cell("", f"{bm:.1f}", None, "MAX") + cell("", f"{lo:.1f}", None, f"Worst {pos} / FLEX starter") + '</div></div>')
    V1 = V2; print(mx, bm, lows, lo)
if MIP:
    import statistics as st
    best = {}
    for w in WEEKS:
        for pid, gg in json.load(open(f'{W2}/ws{w}.json')).items():
            v = [x for x in gg.values() if x is not None]
            if v: best.setdefault(pid, {})[w] = max(v)
    top = max(st.mean(b.values()) for b in best.values() if len(b) >= 2)
    cells = [("Last season", PG(win['id'], "'26")['pct']['max'], f"{win['then']:.1f} a week", "n"),
             ("This season", PG(win['id'])['pct']['max'], f"{win['now']:.1f} a week", "g")]
    V2 = '<div class="rk2" style="--n:2">' + ''.join(f'<div class="c {c[3]}"><span class="l">{c[0]}</span><b>{sup(c[1])}</b><span class="m"><u style="width:{c[1]}%"></u><i style="left:{c[1]}%"></i></span><span class="v">{c[2]}</span></div>' for c in cells) + '</div>'
    print(cells)
    V1 = V2
    CSSX = '.aw .rk2 .c.n .m u{background:linear-gradient(90deg,color-mix(in srgb,#8b949e 25%,var(--surface-3)),#8b949e)!important}.aw .rk2 .c.n .m i{background:#c9d1d9!important}.aw .r.win .ln{font-size:38px!important}'
else: CSSX = ''
if SIX: CSSX = ('.six{grid-template-columns:1fr 2fr!important}'
    '.six .bench{display:grid;grid-template-columns:1fr 1fr;align-items:center;border-left:1px solid var(--surface-3)}'
    '.six .bench .bl{grid-column:1 / span 2;text-align:center;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;align-self:start}'
    '.six .bench .c .l{display:none}.six .bench .c{justify-content:flex-start}.six .bench .m.nb{display:none}'
    '.six .bench .c b{font-size:40px!important;margin:6px 0 4px!important}'
    '.six .bench .c .v{min-height:15px}')
if ROOK: CSSX = '.aw .rk2 .v em{font-style:normal;color:#4ade80}'
CSS = '''
.ctx .rk2 .c{align-items:center!important;text-align:center}.ctx .rk2 .m{width:88%!important}

.aw h2{font-size:26px!important;letter-spacing:.06em!important;padding-bottom:12px!important}.aw h2:before{width:14px!important;height:24px!important}
.ctx{position:relative;padding:12px 18px 14px 22px;background:color-mix(in srgb,var(--tc) 8%,var(--surface));border-bottom:1px solid var(--surface-3)}
.ctx:before{content:"";position:absolute;left:0;top:0;bottom:0;width:6px;background:var(--tc)}
.bx{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
.bx th{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;text-align:right;padding:0 0 6px 10px;border-bottom:1px solid var(--surface-3)}
.bx td{text-align:right;padding:5px 0 0 10px;font-size:14px;font-weight:600}
.bx tr.raw td{font-size:20px;font-weight:700;padding-top:8px}
.bx td.rl{text-align:left;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding-left:0}
.bx td.g{color:#4ade80}.bx td.b{color:#f87171}
.rk2{display:grid;grid-template-columns:repeat(var(--n,6),minmax(0,1fr))}
.rk2 .c{display:flex;flex-direction:column;align-items:flex-start;padding:2px 10px;border-left:3px solid #22c55e}.rk2 .c.b{border-left-color:#ef4444}.rk2 .c.n{border-left-color:#8b949e}
.rk2 .l{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}
.rk2 b{font:800 30px/1.05 var(--fd)}.rk2 .v{font-size:12px;font-weight:600;white-space:nowrap}
.grid{grid-template-columns:minmax(0,640px)!important}
.lbl{font:800 18px var(--fd);color:var(--accent);margin:26px 0 6px}
'''
sec = [x for x in re.findall(r'<section class="aw">.*?</section>', src, re.S) if f'<h2>{GROUP}</h2>' in x][0]; j = sec.index('<div class="r"')
cards = ''.join(f'<div class="lbl">{n}</div>' + sec[:j] + f'<div class="ctx" style="--tc:{tc}">{c}</div>' + sec[j:] for n, c in (("1 · box score: count, fantasy points, league rank", V1), ("2 · rank-led: his league rank in each scoring stat", V2)))
out = src[:src.index('<div class="grid">')] + '<div class="grid"><div>' + cards + '</div></div>'
open(f'{S}/m_scoring2.html','w').write(out.replace('</style>', CSS + CSSX + '</style>', 1))
print(cells)
