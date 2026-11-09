s = open('body.html').read()
a = s.index('// Awards:'); b = s.rindex('}') + 1
s = s[:a] + open('aw.js').read() + s[b:]
open('body.html', 'w').write(s)
p = open('splice.py').read()
if '.ar{' not in p:
    p = p.replace(".pos.FLEX{", ".rows{display:flex;flex-direction:column}.ar{display:grid;grid-template-columns:22px 92px minmax(0,1fr);gap:12px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--surface-2)}.ar:last-child{border-bottom:0}.ar .rk{font-family:var(--font-display);font-weight:800;font-size:18px}.ar .big{font-size:36px}.ar.r1 .big,.ar.r2 .big{font-size:26px}.ar.r1 .who,.ar.r2 .who{font-size:16px}\\n.pos.FLEX{", 1)
    open('splice.py', 'w').write(p)
