import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json
from collections import defaultdict
rep=json.load(open('report.json'))
best=lambda e: max([g['points'] for g in e.get('games') or [] if g.get('played') and g.get('points') is not None] or [0])
share=defaultdict(lambda: defaultdict(float)); tot=defaultdict(float)
for w in tuple(WEEKS):
    for tid,t in json.load(open(f'week_all_scenario_live_week_{w}.json')).items():
        for e in t['entries']:
            if e['slot'] in ('BENCH','IR'): continue
            p=best(e); share[tid][e['name']]+=p; tot[tid]+=p
bal=[]
for tid in tot:
    top=sorted(share[tid].items(),key=lambda kv:-kv[1])
    bal.append({'id':tid,'top':top[0][0],'pct':round(100*top[0][1]/tot[tid]),'top2':[(n,round(100*v/tot[tid])) for n,v in top[:3]]})
bal.sort(key=lambda b:b['pct']); rep['balance']=bal
# biggest single week
P={p['id']:p['name'] for p in json.load(open('players_scenario_live.json'))}
owner={x['id']:t['id'] for t in json.load(open('teams_scenario_live.json')) for x in t['roster']}
pops=[]
for w in tuple(WEEKS):
    for pid,g in json.load(open(f'ws{w}.json')).items():
        for dte,v in g.items():
            if v is not None: pops.append((v,pid,dte,w))
pops.sort(reverse=True); v,pid,dte,w=pops[0]
rep['pop']={'pts':v,'name':P.get(pid,pid),'team':owner.get(pid),'date':dte,'week':w}
json.dump(rep,open('report.json','w'))
for b in bal: print(b)
print(pops[:3])
rep=json.load(open('report.json'))
rep['pops']=[{'pts':v,'name':P.get(pid,pid),'team':owner.get(pid),'date':dte,'week':w} for v,pid,dte,w in pops[:3]]
json.dump(rep,open('report.json','w'))
