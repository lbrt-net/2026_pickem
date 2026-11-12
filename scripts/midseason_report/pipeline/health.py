import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json, urllib.request, os
from concurrent.futures import ThreadPoolExecutor
teams={t['id']:t['name'] for t in json.load(open('teams_scenario_live.json'))}
rep=json.load(open('report.json'))
wk={w:json.load(open(f'week_all_scenario_live_week_{w}.json')) for w in tuple(WEEKS)}
ids={e['id'] for w in wk.values() for t in w.values() for e in t['entries'] if e['kind']=='player'}
os.makedirs('logs2',exist_ok=True)
def get(i):
    p=f'logs2/{i}.json'
    if not os.path.exists(p):
        open(p,'w').write(urllib.request.urlopen(f'{BASE}/fantasy/2026_27/entity/{i}/games?scenario=live',timeout=60).read().decode())
    return i,json.load(open(p))
logs=dict(ThreadPoolExecutor(8).map(get,ids))
P={p['id']:p for p in json.load(open('players_scenario_live.json'))}
nbas={P[i]['nba_team'] for i in ids if i in P}
tl=dict(ThreadPoolExecutor(8).map(get,nbas))
def tgames(ab,w): return {g['date'] for g in tl[ab]['games'] if g.get('week')==w and g['status']=='final'}
out={}
for w,d in wk.items():
    for tid,t in d.items():
        a=out.setdefault(tid,{'played':0,'games':0,'miss':{}})
        pm=lambda e: P.get(e['id'],{}).get('proj_max') or 0
        starters=[x for x in t['entries'] if x['slot'] in ('G','F','C','FLEX')]
        for e in t['entries']:
            if e['kind']!='player': continue
            if e['slot']=='IR':
                ok=[x for x in starters if x['slot'] in (e['position'],'FLEX')]
                if not ok or pm(e)<=min(pm(x) for x in ok): continue   # IR only counts if he'd have started
            dates=tgames(e['nba_team'],w)
            pl={g['date'] for g in logs[e['id']]['games'] if g.get('week')==w and (g.get('minutes') or 0)>0}
            a['games']+=len(dates); a['played']+=len(dates&pl)
            m=len(dates-pl)
            if m: a['miss'][e['name']]=a['miss'].get(e['name'],0)+m
h=sorted([dict(id=k,**v) for k,v in out.items()],key=lambda x:-(x['games']-x['played']))
rep['health']=h; json.dump(rep,open('report.json','w'))
for x in h: print(teams[x['id']][:16],x['games']-x['played'],x['games'],sorted(x['miss'].items(),key=lambda y:-y[1])[:4])
