import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json
rep=json.load(open('report.json')); out=[]
best=lambda e: max([g['points'] for g in e.get('games') or [] if g.get('played') and g.get('points') is not None] or [0])
for w in tuple(WEEKS):
    for tid,t in json.load(open(f'week_all_scenario_live_week_{w}.json')).items():
        st=[e for e in t['entries'] if e['slot'] not in ('BENCH','IR')]
        for b in [e for e in t['entries'] if e['slot']=='BENCH']:
            ok=[s for s in st if (s['slot']=='TEAM')==(b['kind']!='player') and s['slot'] in (('TEAM',) if b['kind']!='player' else (b['position'],'FLEX'))]
            if not ok: continue
            s=min(ok,key=best)
            out.append({'week':w,'team':tid,'bench':b['name'],'bpts':best(b),'start':s['name'],'slot':s['slot'],'spts':best(s),'gain':best(b)-best(s)})
out.sort(key=lambda x:-x['gain'])
for x in out[:6]: print(x)
rep['bench']=out[:5]; json.dump(rep,open('report.json','w'))
# per team: best possible swap each week, summed (points left on the bench)
from collections import defaultdict
left=defaultdict(float); seen={}
for x in out:
    k=(x['team'],x['week'])
    if k not in seen and x['gain']>0: seen[k]=x; left[x['team']]+=x['gain']
lb=sorted(left.items(),key=lambda kv:-kv[1])
rep['bench_left']=[{'id':k,'pts':v,'weeks':[seen[(k,w)] for w in tuple(WEEKS) if (k,w) in seen]} for k,v in lb]
g={(x['id'],x['week']):x for x in rep['games']}
for b in rep['bench']: b['margin']=g[(b['team'],b['week'])]['pts']-g[(b['team'],b['week'])]['opp_pts']
json.dump(rep,open('report.json','w'))
print(lb[:3], rep['bench'][0]['margin'])
