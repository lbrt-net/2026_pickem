import json, statistics as st
J=lambda f: json.load(open(f))
R=J('f3/results.json'); rows=J('f3/luck_rows.json'); WEEKS=[1,2,3]
ST=('BENCH','IR')
teams={t['id']:t for t in J('f3/teams.json')}
# --- luck: losses that would have been wins if every starter (both sides) had his usual (median) week
def luckrow(r):
    return {'week':r['week'],'opp':r['opp'],'margin':r['margin'],'usual_margin':r['usual_margin'],'me_pct':r['me']['pct'],'op_pct':r['op']['pct']}
unl={};lk={}
for r in rows:
    if r['lost'] and r['usual_margin']>0: unl.setdefault(r['id'],[]).append(luckrow(r))
    if r['won'] and r['usual_margin']<0: lk.setdefault(r['id'],[]).append(luckrow(r))
cost=lambda xs: round(sum(x['usual_margin']-x['margin'] for x in xs),1)
unlucky=sorted(({'id':t,'n':len(xs),'swing':cost(xs),'games':xs} for t,xs in unl.items()),key=lambda x:(-x['n'],-x['swing']))
lucky=sorted(({'id':t,'n':len(xs),'swing':-cost(xs),'games':xs} for t,xs in lk.items()),key=lambda x:(-x['n'],-x['swing']))
# --- balance: each week, the top starter's share of that week's starters' points; averaged over the weeks
bal={}
for w in R['weeks'][:3]:
    for m in w['matchups']:
        for side in ('home','away'):
            t=m[side]; ss=[s for s in t['slots'] if s['slot'] not in ST and s.get('score') is not None]
            tot=sum(s['score'] for s in ss); top=max(ss,key=lambda s:s['score'])
            bal.setdefault(t['team']['id'],[]).append({'week':w['week'],'name':top['name'],'share':round(100*top['score']/tot)})
balance=sorted(({'id':t,'pct':round(st.mean(x['share'] for x in xs)),'weeks':xs} for t,xs in bal.items()),key=lambda x:x['pct'])
# --- variance: standard deviation of weekly bests (top 60 by total who played all 3 weeks)
best={}
for w in WEEKS:
    for pid,g in J(f'f3/ws{w}.json').items():
        v=[x for x in g.values() if x is not None]
        if v: best.setdefault(pid,{})[w]=max(v)
P={p['id']:p for p in J('players_scenario_live.json')}
owner={x['id']:tid for tid,t in teams.items() for x in t['roster']}
cand=sorted([p for p in best if len(best[p])==3 and p in P],key=lambda p:-sum(best[p].values()))[:60]
cons=sorted(({'name':P[p]['name'],'team':owner.get(p),'weeks':[best[p][w] for w in WEEKS],'sd':round(st.stdev(best[p].values()),1)} for p in cand),key=lambda c:c['sd'])
# --- for fun: players a team added who never started for it (adds made this week and still on the roster wait)
started={}  # (team, player) -> True
for w in R['weeks'][:3]:
    for m in w['matchups']:
        for side in ('home','away'):
            for s in m[side]['slots']:
                if s['slot'] not in ST: started[(m[side]['team']['id'],s['id'])]=True
wa4=J('f3/wa4.json')
for tid,t in wa4.items():
    for e in t['entries']:
        if e['slot'] not in ST and e.get('on_roster'): started[(tid,e['id'])]=True
cur_week=4
fun={}
for x in J('f3/tx.json')['items']:
    for a in x['adds']:
        if started.get((x['team_id'],a['id'])): continue
        if (x['week'] or 0)>=cur_week and owner.get(a['id'])==x['team_id']: continue
        if any(f['id']==a['id'] for f in fun.get(x['team_id'],[])): continue
        fun.setdefault(x['team_id'],[]).append({'id':a['id'],'name':a['name'],'week':x['week'],'still':owner.get(a['id'])==x['team_id']})
forfun=sorted(({'id':t,'n':len(xs),'players':xs} for t,xs in fun.items()),key=lambda x:-x['n'])
rep=J('report.json')
rep.update({'unlucky':unlucky,'lucky':lucky,'balance':balance,'cons':{'steady':cons[:5],'swing':cons[::-1][:5]},'forfun':forfun})
json.dump(rep,open('report.json','w'))
nm=lambda t: teams[t]['name'] if t in teams else t
for k,v in (('unlucky',unlucky),('lucky',lucky)):
    print(k,[(nm(x['id']),x['n'],x['swing']) for x in v])
print('bal',[(nm(x['id']),x['pct']) for x in balance])
print('steady',[(c['name'],c['sd'],c['weeks']) for c in cons[:3]]); print('swing',[(c['name'],c['sd'],c['weeks']) for c in cons[::-1][:3]])
print('fun',[(nm(x['id']),x['n'],[p['name'] for p in x['players']]) for x in forfun])
