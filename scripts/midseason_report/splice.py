s = open('build.py').read()
a = s.index('<section><h2>Standings'); b = s.index('</script>')
css = '''.two>:last-child:nth-child(odd){grid-column:1/-1}\n.rows{display:flex;flex-direction:column}.ar{display:grid;grid-template-columns:22px 92px minmax(0,1fr);gap:12px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--surface-2)}.ar:last-child{border-bottom:0}.ar .rk{font-family:var(--font-display);font-weight:800;font-size:18px}.ar .big{font-size:36px}.ar.r1 .big,.ar.r2 .big{font-size:26px}.ar.r1 .who,.ar.r2 .who{font-size:16px}\n.ics{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}.ic{width:40px;height:30px;object-fit:contain;background:var(--surface-2);border-radius:4px}\n.pos.FLEX{background:var(--surface-2);border:1px solid var(--border)} .pos.TM{background:var(--text);color:var(--bg)}
.opp td{vertical-align:top}.opp .r{font-weight:800;font-size:16px}.opp .u{font-size:13px;font-weight:500}
.opp .W{color:var(--good)}.opp .L{color:var(--bad)}
.lst{display:flex;flex-direction:column}.lst .it{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;padding:10px 14px;border-bottom:1px solid var(--surface-2)}
.lst .it:last-child{border-bottom:0}.lst .n{font-weight:700}.lst .s{font-size:13px;font-weight:500;grid-column:1/3}.lst .v{font-weight:800;text-align:right}
'''
s = s[:a] + open('body.html').read() + s[b:]
s = s.replace('svg text{fill', css + open('aw.css').read() + 'svg text{fill', 1)
open('build.py', 'w').write(s)
