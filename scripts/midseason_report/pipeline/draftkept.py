import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json
J=lambda f: json.load(open(f))
picks=[]
def walk(o):
    if isinstance(o,dict):
        if 'pick' in o and 'team_id' in o and 'id' in o: picks.append(o)
        else: [walk(v) for v in o.values()]
    elif isinstance(o,list): [walk(v) for v in o]
walk(J('draft_scenario_live.json'))
teams={t['id']:t for t in J('teams_scenario_live.json')}
rost={tid:{x['id'] for x in t['roster']} for tid,t in teams.items()}
out=[]
for tid in teams:
    mine=[p for p in picks if p['team_id']==tid]
    out.append({'id':tid,'spent':sum(p['price'] or 0 for p in mine),'kept':sum(p['price'] or 0 for p in mine if p['id'] in rost[tid]),'still':sorted(([p['id'],p.get('name') or p['id'],p['price'] or 0] for p in mine if p['id'] in rost[tid]),key=lambda x:-x[2])})
rep=J('report.json'); print(rep.get('draft',[None])[:2]); rep['draft']=out; json.dump(rep,open('report.json','w'))
print(sorted((teams[x['id']]['name'],x['kept'],x['spent']) for x in out))
