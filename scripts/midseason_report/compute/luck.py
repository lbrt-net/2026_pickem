import json, statistics as st
J=lambda f: json.load(open(f))
R=J('f3/results.json'); WEEKS=[1,2,3]
ws={w:J(f'f3/ws{w}.json') for w in WEEKS}
this={}  # id -> {week: weekly best}
for w in WEEKS:
    for pid,g in ws[w].items():
        v=[x for x in g.values() if x is not None]
        if v: this.setdefault(pid,{})[w]=max(v)
ST=('BENCH','IR')
for w in R['weeks'][:3]:
    for m in w['matchups']:
        for side in ('home','away'):
            for s in m[side]['slots']:
                if s['kind']=='nba_team' and s.get('score') is not None: this.setdefault(s['id'],{})[w['week']]=s['score']
def hist(i):
    ss=sorted(J(f'f3/hist/{i}.json')['seasons'],key=lambda s:s.get('season',''))[-2:]
    return [x['max'] for s in ss for x in s['weeks'] if x.get('max') is not None]
H={}
def mine(i):
    if i not in H: H[i]=hist(i)+list(this.get(i,{}).values())
    return H[i]
def pct(i,v):
    m=mine(i); return round(100*(sum(x<v for x in m)+0.5*sum(x==v for x in m))/len(m))
rows=[]  # one per team-week
for w in R['weeks'][:3]:
    for m in w['matchups']:
        for a,b in (('home','away'),('away','home')):
            me,op=m[a],m[b]
            def side(t):
                st_=[s for s in t['slots'] if s['slot'] not in ST]
                played=[s for s in st_ if s.get('score') is not None]
                return {'score':t['score'],'usual':round(sum(st.median(mine(s['id'])) for s in played),1),
                        'pct':round(st.mean(pct(s['id'],s['score']) for s in played)) if played else None,
                        'players':[(s['name'],s['score'],pct(s['id'],s['score']),st.median(mine(s['id']))) for s in played],
                        'tot':round(sum(s['score'] for s in played),1)}
            x,y=side(me),side(op)
            rows.append({'week':w['week'],'id':me['team']['id'],'opp':op['team']['id'],'me':x,'op':y,
                         'won':me['score']>op['score'],'lost':me['score']<op['score'],
                         'margin':round(me['score']-op['score'],1),'usual_margin':round(x['usual']-y['usual'],1)})
# sanity: starters' points add up to the score
bad=[(r['week'],r['id'],r['me']['tot'],r['me']['score']) for r in rows if abs(r['me']['tot']-r['me']['score'])>0.05]
print('mismatch',bad[:5])
json.dump(rows,open('f3/luck_rows.json','w'))
for r in rows:
    if r['lost'] and r['usual_margin']>0: print('UNLUCKY',r['week'],r['id'][-6:],r['margin'],r['usual_margin'],r['me']['pct'],r['op']['pct'])
    if r['won'] and r['usual_margin']<0: print('LUCKY',r['week'],r['id'][-6:],r['margin'],r['usual_margin'],r['me']['pct'],r['op']['pct'])
