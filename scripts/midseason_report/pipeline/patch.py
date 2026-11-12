import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json, statistics as st, urllib.request
J=lambda f: json.load(open(f))
rep=J('report.json')
teams={t['id']:t for t in J('teams_scenario_live.json')}
owner={x['id']:tid for tid,t in teams.items() for x in t['roster']}
P={p['id']:p for p in J('players_scenario_live.json')}
act=J('players_actual_scenario_live_window_season.json')['players']
draft=[p for r in J('draft_scenario_live.json')['rounds'] for p in (r['picks'] if isinstance(r,dict) else r)] if False else None
d=J('draft_scenario_live.json'); s=json.dumps(d)
picks=[]
def walk(o):
    if isinstance(o,dict):
        if 'pick' in o and 'team_id' in o and 'id' in o: picks.append(o)
        else: [walk(v) for v in o.values()]
    elif isinstance(o,list): [walk(v) for v in o]
walk(d)
drafted={p['id']:(p['team_id'],p['price']) for p in picks}
tx=J('transactions_scenario_live.json')['items']

wk={w:J(f'week_all_scenario_live_week_{w}.json') for w in WEEKS}
# weekly best per entity from week_all entries (rostered) + ws (all players)
best={}
for w in WEEKS:
    for pid,g in J(f'ws{w}.json').items():
        v=[x for x in g.values() if x is not None]
        if v: best.setdefault(pid,{})[w]=max(v)
def team_games(ab):
    g=json.load(urllib.request.urlopen(f'{BASE}/fantasy/2026_27/entity/{ab}/games?scenario=live',timeout=60))['games']
    out={}
    for x in g:
        if x['status']=='final' and x['week'] in WEEKS and x['fantasy_points'] is not None:
            out[x['week']]=max(out.get(x['week'],-99),x['fantasy_points'])
    return out
nba=[k for k in act if not k.isdigit()]
import os
if os.path.exists("tg.json"): best.update({k:{int(w):v for w,v in d.items()} for k,d in J("tg.json").items()})
else:
    for ab in nba: best[ab]=team_games(ab)
    json.dump({ab:best[ab] for ab in nba},open("tg.json","w"))
def how(pid):
    t=owner.get(pid)
    if not t: return 'free agent'
    if pid in drafted and drafted[pid][0]==t: return f'drafted ${drafted[pid][1]}'
    for x in sorted(tx,key=lambda x:x['at'],reverse=True):
        if x['team_id']==t and any(a['id']==pid for a in x['adds']):
            return ('claimed ' if x.get('via')=='waivers' else 'added ')+(x['week_label'] or ('Week %s'%x['week'] if x.get('week') else 'before Week 1'))
    return 'traded for'
def row(pid,pos):
    b=best.get(pid,{})
    name=P[pid]['name'] if pid in P else teams_name.get(pid,pid)
    return {'id':pid,'name':name,'pos':pos,'nba':P[pid]['nba_team'] if pid in P else pid,
            'weeks':[b.get(w) for w in WEEKS],'tot':sum(v for v in b.values()),'team':owner.get(pid),'how':how(pid)}
teams_name={}
for t in teams.values():
    for x in t['roster']:
        if x['kind']!='player': teams_name[x['id']]=x['name']
NAMES=dict(ATL='Atlanta Hawks',BOS='Boston Celtics',BKN='Brooklyn Nets',CHA='Charlotte Hornets',CHI='Chicago Bulls',CLE='Cleveland Cavaliers',DAL='Dallas Mavericks',DEN='Denver Nuggets',DET='Detroit Pistons',GSW='Golden State Warriors',HOU='Houston Rockets',IND='Indiana Pacers',LAC='LA Clippers',LAL='Los Angeles Lakers',MEM='Memphis Grizzlies',MIA='Miami Heat',MIL='Milwaukee Bucks',MIN='Minnesota Timberwolves',NOP='New Orleans Pelicans',NYK='New York Knicks',OKC='Oklahoma City Thunder',ORL='Orlando Magic',PHI='Philadelphia 76ers',PHX='Phoenix Suns',POR='Portland Trail Blazers',SAC='Sacramento Kings',SAS='San Antonio Spurs',TOR='Toronto Raptors',UTA='Utah Jazz',WAS='Washington Wizards')
for ab in nba:
    teams_name[ab]=NAMES.get(ab,ab)
tot=lambda pid: sum(best.get(pid,{}).values())
pl=[p for p in best if p in P]
used=set(); af=[]
for tier in range(3):
    line=[]
    for pos in 'GFC':
        c=max((p for p in pl if P[p]['position']==pos and p not in used),key=tot); used.add(c); line.append(row(c,pos))
    c=max((p for p in pl if p not in used),key=tot); used.add(c); line.append(row(c,'FLEX'))
    c=max((p for p in nba if p not in used),key=tot); used.add(c); line.append(row(c,'TM'))
    af.append(line)
rep['af']=af
# results: margins + opponent vs their average week
R=J('results_scenario_live.json')
scores={}; games=[]
for w in R['weeks'][:len(WEEKS)]:
    for m in w['matchups']:
        a,b=m['home'],m['away']
        for x,y in ((a,b),(b,a)):
            scores.setdefault(x['team']['id'],{})[w['week']]=x['score']
            games.append((w['week'],x['team']['id'],x['score'],y['team']['id'],y['score'],w['status']=='final'))
avg={t:st.mean(v.values()) for t,v in scores.items()}
rep['games']=[{'week':w,'id':t,'pts':s,'opp':o,'opp_pts':os_,'opp_vs_avg':round(os_-avg[o],1),'final':f} for w,t,s,o,os_,f in games]
rep['team_avg']=avg
# roster continuity: different starters used
cont=[]
for tid in teams:
    st_by=[]
    for w in WEEKS:
        st_by.append({e['id'] for e in wk[w][tid]['entries'] if e['slot'] not in ('BENCH','IR')})
    allw=set.intersection(*st_by); anyw=set.union(*st_by)
    nm=lambda i: P[i]['name'] if i in P else teams_name.get(i,i)
    cont.append({'id':tid,'n':len(anyw),'every':[nm(i) for i in allw],'once':[nm(i) for i in anyw-allw],
                 'used':[{'id':i,'name':nm(i)} for i in sorted(anyw,key=lambda i:(-sum(i in x for x in st_by),nm(i)))]})
rep['cont']=sorted(cont,key=lambda c:c['n'])
# player consistency: top 60 by total, played all 3 weeks; gap best-worst weekly best
cand=sorted([p for p in pl if len(best[p])==len(WEEKS)],key=tot,reverse=True)[:60]
cons=[{'name':P[p]['name'],'team':owner.get(p),'weeks':[best[p][w] for w in WEEKS],'gap':max(best[p].values())-min(best[p].values())} for p in cand]
cons.sort(key=lambda c:c['gap'])
rep['cons']={'steady':cons[:5],'swing':cons[-5:][::-1]}
json.dump(rep,open('report.json','w'))
for t in af: print([(r['pos'],r['name'],r['tot'],r['how']) for r in t])
print(rep['cont'][:2],rep['cont'][-2:]); print(rep['cons'])
# value over replacement: avg weekly best minus the 3rd-best free agent at the position
def lvl(p): return act.get(p,{}).get('max')
repl={}
for pos in ('G','F','C'):
    fa=sorted([lvl(p) for p in act if p in P and P[p]['position']==pos and p not in owner and lvl(p) is not None],reverse=True)
    repl[pos]=fa[2]
fa_t=sorted([lvl(p) for p in nba if p not in owner],reverse=True); repl['TM']=fa_t[2]
posof=lambda p: P[p]['position'] if p in P else 'TM'
vor=lambda p: (lvl(p) or 0)-repl[posof(p)]
dp=[p for p in drafted if drafted[p][1]]
rate=sum(vor(p) for p in dp)/sum(drafted[p][1] for p in dp)   # points over replacement per draft dollar, league-wide
def vrow(p):
    t=drafted.get(p,(None,0))
    nm=P[p]['name'] if p in P else teams_name.get(p,p)
    return {'name':nm,'pos':posof(p),'price':t[1],'by':t[0],'team':owner.get(p),'lvl':lvl(p),'repl':repl[posof(p)],'vor':round(vor(p),1),'exp':round(t[1]*rate,1),'surplus':round(vor(p)-t[1]*rate,1),'how':how(p)}
vals=sorted([vrow(p) for p in dp],key=lambda r:r['surplus'])
rep['value']=vals[-5:][::-1]; rep['bust']=vals[:5]
pick=[p for p in owner if not (p in drafted and drafted[p][0]==owner[p]) and lvl(p) is not None]
rep['pickups']=sorted([vrow(p) for p in pick],key=lambda r:-r['vor'])[:5]
rep['repl']=repl; rep['rate']=round(rate,3)
json.dump(rep,open('report.json','w'))
print(repl, rate); print(json.dumps(rep['value'])); print(json.dumps(rep['bust'])); print(json.dumps(rep['pickups']))
# fit: what each price usually buys over replacement (straight line through drafted players who've played)
fit=[(drafted[p][1],vor(p)) for p in dp if lvl(p) is not None]
mx=st.mean(x for x,_ in fit); my=st.mean(y for _,y in fit)
b=sum((x-mx)*(y-my) for x,y in fit)/sum((x-mx)**2 for x,_ in fit); a=my-b*mx
def vrow2(p):
    r=vrow(p); r['exp']=round(a+b*r['price'],1); r['surplus']=round(r['vor']-r['exp'],1); return r
vals=sorted([vrow2(p) for p in dp],key=lambda r:r['surplus'])
rep['value']=vals[-5:][::-1]; rep['bust']=[r for r in vals if r['price']>=20][:5]
rep['fit']=[round(a,2),round(b,3)]
json.dump(rep,open('report.json','w'))
print('fit',a,b)
for r in rep['value']+rep['bust']: print(r['name'],r['price'],r['lvl'],r['vor'],r['exp'],r['surplus'],r['how'])
# standings fresh from results (week 3 live)
stand=[]
wkscores={w:{t:scores[t][w] for t in scores if w in scores[t]} for w in WEEKS}
for t in scores:
    my=[g for g in rep['games'] if g['id']==t]
    w_=sum(g['pts']>g['opp_pts'] for g in my); l_=sum(g['pts']<g['opp_pts'] for g in my)
    exp=sum(sum((s<scores[t][w])+0.5*(s==scores[t][w]) for o,s in wkscores[w].items() if o!=t)/11 for w in WEEKS)
    stand.append({'id':t,'w':w_,'l':l_,'pf':sum(scores[t].values()),'pa':sum(g['opp_pts'] for g in my),'luck':round(w_-exp,2),'scores':[scores[t][w] for w in WEEKS]})
stand.sort(key=lambda s:(-s['w'],-s['pf'])); rep['stand']=stand
# opponent vs their usual: their score minus the average of their OTHER weeks
for g in rep['games']:
    o=[v for w,v in scores[g['opp']].items() if w!=g['week']]
    g['opp_vs_usual']=round(g['opp_pts']-st.mean(o),1)
json.dump(rep,open('report.json','w'))
for s in stand: print(teams[s['id']]['name'][:14], s['w'],s['l'],s['luck'],[ (g['week'],round(g['pts']-g['opp_pts'],1),g['opp_vs_usual']) for g in rep['games'] if g['id']==s['id']])
