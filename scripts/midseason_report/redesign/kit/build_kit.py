"""Team asset kit: colors (field = the color a panel floods with, then secondary/tertiary/dark), the NBA primary logo,
and a tonal mark (the logo redrawn in two shades of the field) for giant cropped backgrounds."""
import re, json, urllib.parse
C = {  # field, secondary, tertiary, dark  (official palettes)
 "ATL":["#C8102E","#FDB927","#C1D32F","#26282A"], "BOS":["#007A33","#BA9653","#FFFFFF","#0B2E1A"],
 "BKN":["#2B2B2B","#FFFFFF","#707271","#000000"], "CHA":["#00788C","#1D1160","#A1A1A4","#0E0A2E"],
 "CHI":["#CE1141","#000000","#FFFFFF","#3A0613"], "CLE":["#860038","#FDBB30","#041E42","#2E0013"],
 "DAL":["#00538C","#002B5E","#B8C4CA","#001833"], "DEN":["#0E2240","#FEC524","#8B2131","#06101F"],
 "DET":["#C8102E","#1D42BA","#BEC0C2","#002D62"], "GSW":["#1D428A","#FFC72C","#26282A","#0D1F42"],
 "HOU":["#CE1141","#C4CED4","#000000","#3D0514"], "IND":["#002D62","#FDBB30","#BEC0C2","#001530"],
 "LAC":["#C8102E","#1D428A","#BEC0C2","#0C2340"], "LAL":["#552583","#FDB927","#000000","#1E0B38"],
 "MEM":["#5D76A9","#12173F","#F5B112","#0A0D24"], "MIA":["#98002E","#F9A01B","#000000","#2E000E"],
 "MIL":["#00471B","#EEE1C6","#0077C0","#00230D"], "MIN":["#236192","#78BE20","#0C2340","#0A1C2E"],
 "NOP":["#0C2340","#C8102E","#85714D","#050F1C"], "NYK":["#006BB6","#F58426","#BEC0C2","#00335A"],
 "OKC":["#007AC1","#EF3B24","#002D62","#003A5C"], "ORL":["#0077C0","#C4CED4","#000000","#003A5E"],
 "PHI":["#006BB6","#ED174C","#002B5C","#00335A"], "PHX":["#1D1160","#E56020","#F9AD1B","#0B0626"],
 "POR":["#E03A3E","#000000","#FFFFFF","#4A0F11"], "SAC":["#5A2D81","#63727A","#000000","#22102F"],
 "SAS":["#8A8D8F","#000000","#C4CED4","#1F1F1F"], "TOR":["#CE1141","#000000","#A1A1A4","#3D0514"],
 "UTA":["#3E2680","#000000","#FFFFFF","#170E30"], "WAS":["#002B5C","#E31837","#C4CED4","#00152E"],
}
def hx(c): c=c.lstrip('#'); c=''.join(x*2 for x in c) if len(c)==3 else c; return [int(c[i:i+2],16) for i in (0,2,4)]
def mix(a,b,t): return '#'+''.join(f'{round(x*(1-t)+y*t):02x}' for x,y in zip(hx(a),hx(b)))
def lum(c): r,g,b=hx(c); return .2126*r+.7152*g+.0722*b
def mark(svg, field, deep=.55, light=.22):
    dark, lite = mix(field,'#000000',deep), mix(field,'#000000',light)
    def sub(m):
        c=m.group(2); return m.group(1)+ (mix(dark,lite,min(1,lum(c)/255)))
    svg=re.sub(r'((?:fill|stroke)\s*[:=]\s*"?)(#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b)',sub,svg)
    svg=re.sub(r'((?:fill|stroke)\s*[:=]\s*"?)(white|black)\b',lambda m:m.group(1)+mix(dark,lite,1 if m.group(2)=='white' else 0),svg)
    svg=re.sub(r'<svg\b[^>]*>',lambda m:re.sub(r'\sfill="[^"]*"','',m.group(0)).replace('<svg',f'<svg fill="{dark}"',1),svg,count=1)
    return svg
kit={}
for t,(f,s,ter,d) in C.items():
    raw=open(f'logo/{t}.svg').read()
    raw=re.sub(r'<\?xml.*?\?>|<!--.*?-->','',raw,flags=re.S).strip()
    m=mark(raw,f); open(f'logo/{t}_mark.svg','w').write(m)
    kit[t]={"field":f,"secondary":s,"tertiary":ter,"dark":d,"logo":f"logo/{t}.svg","mark":f"logo/{t}_mark.svg"}
json.dump(kit,open('kit.json','w'),indent=1)
# contact sheet
url=lambda p:"url('data:image/svg+xml,"+urllib.parse.quote(open(p).read())+"')"
cells=''
for t,k in kit.items():
    cells+=(f'<div class="p" style="--f:{k["field"]};--s:{k["secondary"]};--t:{k["tertiary"]};--d:{k["dark"]}">'
            f'<i class="mk" style="background-image:{url(k["mark"])}"></i>'
            f'<img class="lg" src="{k["logo"]}"><b>{t}</b><span class="sw"><i></i><i></i><i></i><i></i></span></div>')
html=f'''<style>body{{margin:0;background:#0b0c0f;font-family:system-ui}}.g{{display:grid;grid-template-columns:repeat(6,200px);gap:6px;padding:16px}}
.p{{position:relative;height:150px;overflow:hidden;background:var(--f)}}
.mk{{position:absolute;width:300px;height:300px;left:30px;top:-60px;background:no-repeat center/contain}}
.lg{{position:absolute;left:8px;bottom:22px;width:40px;height:40px;object-fit:contain}}
b{{position:absolute;left:8px;top:6px;color:#fff;font:800 18px system-ui;letter-spacing:.04em}}
.sw{{position:absolute;left:0;right:0;bottom:0;height:14px;display:flex}}.sw i{{flex:1}}
.sw i:nth-child(1){{background:var(--f)}}.sw i:nth-child(2){{background:var(--s)}}.sw i:nth-child(3){{background:var(--t)}}.sw i:nth-child(4){{background:var(--d)}}
</style><div class="g">{cells}</div>'''
open('sheet.html','w').write(html)
