import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json, statistics as st
J=lambda f: json.load(open(f))
N=12; ST=('BENCH','IR')
P={p['id']:p for p in J('players_scenario_live.json')}
tg={k:{int(w):v for w,v in d.items()} for k,d in J('f3/tg.json').items()}
best={}
for w in WEEKS:
    for pid,g in J(f'f3/ws{w}.json').items():
        v=[x for x in g.values() if x is not None]
        if v: best.setdefault(pid,{})[w]=max(v)
# replacement level per week (Draft Value rule): top 12 at G/F/C/TM start, next 12 best G/F/C fill the Flex,
# replacement = average of the next 12 left at the position
repl={}
for w in WEEKS:
    left={}
    for pos in 'GFC':
        xs=sorted((b[w] for p,b in best.items() if w in b and p in P and P[p]['position']==pos),reverse=True)
        left[pos]=[(v,pos) for v in xs[N:]]
    flex=sorted(left['G']+left['F']+left['C'],reverse=True)[:N]
    for pos in 'GFC':
        rest=list(left[pos])
        for f in flex:
            if f[1]==pos: rest.remove(f)
        repl.setdefault(pos,{})[w]=round(st.mean(v for v,_ in rest[:N]),1)
    ts=sorted((d[w] for d in tg.values() if w in d),reverse=True)
    repl.setdefault('TM',{})[w]=round(st.mean(ts[N:2*N]),1)
print(repl)
R=J('f3/results.json')
start={}  # (team, id) -> {week: (score, slot)}
for wk in R['weeks'][:len(WEEKS)]:
    for m in wk['matchups']:
        for side in ('home','away'):
            for s in m[side]['slots']:
                if s['slot'] not in ST: start.setdefault((m[side]['team']['id'],s['id']),{})[wk['week']]=s.get('score')
picks={}
for x in J('f3/tx.json')['items']:
    for a in x['adds']:
        k=(x['team_id'],a['id'])
        aw=x['week'] or 0
        wks={w:v for w,v in start.get(k,{}).items() if w>=aw and v is not None}  # started (and played) after the add
        if not wks or k in picks: continue
        pos='TM' if a['kind']=='nba_team' else (P[a['id']]['position'] if a['id'] in P else a['position'])
        vor={w:round(v-repl[pos][w],1) for w,v in wks.items()}
        picks[k]={'name':a['name'],'team':x['team_id'],'pos':pos,'weeks':wks,'vor':vor,'per':round(st.mean(vor.values()),1)}
pk=sorted(picks.values(),key=lambda p:-p['per'])
for p in pk[:8]: print(p['name'],p['pos'],p['per'],p['weeks'],p['vor'])
rep=J('report.json'); rep['pick2']=pk[:5]; rep['repl_wk']=repl; json.dump(rep,open('report.json','w'))
