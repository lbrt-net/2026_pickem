import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json, os, re, statistics as st, urllib.request, concurrent.futures as cf
J = lambda f: json.load(open(f))

rep = J('report.json')
teams = {t['id']: t for t in J('teams_scenario_live.json')}
owner = {x['id']: tid for tid, t in teams.items() for x in t['roster']}
P = {p['id']: p for p in J('players_scenario_live.json')}

# team glyphs (frontend/src/components/fantasy/glyphs.js) for teams without a picture
g = open(_os.environ['MS_GLYPHS']).read()
rep['glyphs'] = dict(re.findall(r'^\s+(\w+): "([^"]+)"', g, re.M))
for tid, t in teams.items():
    if tid in rep['teams']: rep['teams'][tid]['glyph'] = t.get('glyph')

# weekly best game per player (rostered that week), with its scoring breakdown; bench points by team
GROUPS = {"Scoring": ("pts", "fg3m", "clutch_pts", "fgx", "ftx", "blkd"), "Playmaking": ("ast", "tov"),
          "Boards": ("oreb", "dreb"), "Stocks": ("stl", "blk"),
          "Clutch": ("clutch_pts",)}  # 2026-11-14: Clutch player of the year (also counted inside Scoring)
wk = {}      # pid -> {week: breakdown}
bench = {}   # (team, pid) -> {week: score}
started = {} # (team, pid) -> points while starting (Sixth man rule)
for w in WEEKS:
    for tid, t in J(f'f3/wa{w}.json').items():
        for e in t['entries']:
            if e['kind'] != 'player' or not e.get('games_done'): continue
            if e.get('breakdown') and e.get('week_score') is not None:
                wk.setdefault(e['id'], {})[w] = (e['week_score'], e['breakdown'])
            if e['slot'] == 'BENCH' and e.get('week_score'):
                bench.setdefault((tid, e['id']), {})[w] = e['week_score']
            elif e['slot'] != 'IR' and e.get('week_score'):
                started[(tid, e['id'])] = started.get((tid, e['id']), 0) + e['week_score']
def clutch_top(rows):
    """Clutch ties (2026-11-14): clutch points in every game of the report's weeks, then clutch points a game.
    Only players tied with a top-3 total need the player page's game log."""
    rows = sorted(rows, key=lambda r: -r['tot'])
    if len(rows) < 3: return rows
    cut = rows[2]['tot']; pool = [r for r in rows if r['tot'] >= cut]
    for r in pool:
        f = f"page_{r['id']}.json"
        if not os.path.exists(f):
            open(f, 'w').write(urllib.request.urlopen(f"{BASE}/fantasy/2026_27/players/{r['id']}/page?actual=true&scenario=live", timeout=120).read().decode())
        gs = [g for g in J(f)['glog'].get('2026-27', []) if g.get('week') in WEEKS and g.get('min')]
        r['clutch_all'] = sum((g.get('raw') or {}).get('clutch_pts', 0) for g in gs)
        r['clutch_gp'] = round(r['clutch_all'] / len(gs), 2) if gs else 0
    return sorted(pool, key=lambda r: (-r['tot'], -r['clutch_all'], -r['clutch_gp']))[:3]
mvp = {}
for grp, ks in GROUPS.items():
    rows = []
    for pid, ws in wk.items():
        per = {w: round(sum(b.get(k, 0) for k in ks), 1) for w, (_, b) in ws.items()}
        rows.append({'id': pid, 'name': P[pid]['name'] if pid in P else pid, 'team': owner.get(pid), 'tot': round(sum(per.values()), 1), 'weeks': [per.get(w) for w in WEEKS]})
    mvp[grp] = sorted(rows, key=lambda r: -r['tot'])[:3] if grp != 'Clutch' else clutch_top(rows)
rep['mvp'] = mvp
rep['sixth'] = sorted(({'id': pid, 'name': P[pid]['name'] if pid in P else pid, 'team': tid, 'tot': round(sum(ws.values()), 1),
                         'weeks': ws} for (tid, pid), ws in bench.items()
                        if sum(ws.values()) > started.get((tid, pid), 0)),  # 2026-11-14: more points on that bench than as its starter
                       key=lambda r: -r['tot'])[:3]

# this season's weekly bests (every player), for MIP and Rookie
best = {}
for w in WEEKS:
    for pid, gg in J(f'f3/ws{w}.json').items():
        v = [x for x in gg.values() if x is not None]
        if v: best.setdefault(pid, {})[w] = max(v)
cand = sorted((p for p in best if p in P and len(best[p]) >= 2), key=lambda p: -sum(best[p].values()))[:200]
def hist(i):
    p = f'f3/hist/{i}.json'
    if not os.path.exists(p):
        open(p, 'w').write(urllib.request.urlopen(f'{BASE}/fantasy/2026_27/players/{i}/history?scenario=live', timeout=60).read().decode())
    return J(p)
with cf.ThreadPoolExecutor(6) as ex: H = dict(zip(cand, ex.map(hist, cand)))
mip, rook = [], []
for p in cand:
    ss = {s.get('season'): s for s in H[p]['seasons']}
    now = st.mean(best[p].values())
    if not ss:
        rook.append({'id': p, 'name': P[p]['name'], 'team': owner.get(p), 'tot': round(sum(best[p].values()), 1), 'avg': round(now, 1)})
    last = ss.get('2025-26')
    lw = [x for x in (last or {}).get('weeks', []) if x.get('max') is not None and x.get('week') in WEEKS]
    need = max(1, (7 * len(WEEKS) + 8) // 9)  # 2026-11-17: played 7 of every 9 weeks in BOTH seasons (same week numbers)
    if len(lw) >= need and len(best[p]) >= need:  # total through the same weeks, this season vs last
        a, b = sum(best[p].values()), sum(x['max'] for x in lw)
        mip.append({'id': p, 'name': P[p]['name'], 'team': owner.get(p), 'now': round(a, 1), 'then': round(b, 1), 'gain': round(a - b, 1)})
rep['mip'] = sorted(mip, key=lambda r: -r['gain'])[:3]
rep['rookie'] = sorted(rook, key=lambda r: -r['tot'])[:3]
rep['extra_ids'] = sorted({r['id'] for v in mvp.values() for r in v} | {r['id'] for k in ('sixth', 'mip', 'rookie') for r in rep[k]} | {p['id'] for t in rep['af'] for p in t})
json.dump(rep, open('report.json', 'w'))
for k, v in mvp.items(): print(k, [(r['name'], r['tot']) for r in v])
print('sixth', [(r['name'], r['tot'], teams[r['team']]['name']) for r in rep['sixth']])
print('mip', [(r['name'], r['then'], r['now'], r['gain']) for r in rep['mip']])
print('rookie', [(r['name'], r['tot']) for r in rep['rookie']])
