import sys, urllib.parse
S = sys.argv[1]
src = open(f'{S}/m_flair3.html').read()
def svg(s): return "url(\"data:image/svg+xml," + urllib.parse.quote(s) + "\")"
# half court seen from above the basket: lane, free-throw circle, 3pt arc, restricted arc, rim
court = svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 470" fill="none" stroke="white" stroke-width="3" stroke-opacity=".16">'
  '<rect x="170" y="0" width="160" height="190"/><circle cx="250" cy="190" r="60"/>'
  '<path d="M30 0v140a220 220 0 0 0 440 0V0"/><path d="M210 40a40 40 0 0 0 80 0"/><circle cx="250" cy="42" r="8"/><path d="M0 470h500"/><circle cx="250" cy="470" r="60"/></svg>')
grain = svg('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .09 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>')
FL = f'''
/* ---- winner slab: spotlight + court lines + halftone + grain, layered edge ---- */
.r.win{{background:var(--ink)!important;isolation:isolate}}
.r.win .slab{{position:absolute;left:0;top:0;bottom:0;width:262px;z-index:0;
  clip-path:polygon(0 0,100% 0,calc(100% - 34px) 100%,0 100%);
  background:
    {grain},
    radial-gradient(circle at 70% 115%,transparent 0 1.6px,transparent 1.7px) ,
    radial-gradient(60% 75% at 62% 18%,color-mix(in srgb,var(--nc) 55%,white) 0,transparent 70%),
    linear-gradient(160deg,color-mix(in srgb,var(--nc) 90%,white),var(--nc) 45%,color-mix(in srgb,var(--nc) 55%,black));}}
.r.win .slab:before{{content:"";position:absolute;inset:-10px -40px 0 0;background:{court} 60% 0/300px auto no-repeat;transform:rotate(180deg);opacity:1}}
.r.win .slab:after{{content:"";position:absolute;inset:0;
  background:radial-gradient(circle,color-mix(in srgb,var(--nc) 30%,black) 1.3px,transparent 1.6px) 0 0/7px 7px;
  -webkit-mask:linear-gradient(0deg,#000,transparent 55%);mask:linear-gradient(0deg,#000,transparent 55%)}}
.r.win .ab{{position:absolute;left:8px;top:-6px;z-index:0;font:900 120px/1 var(--display, "Barlow Condensed",sans-serif);letter-spacing:-.04em;color:color-mix(in srgb,var(--nc) 70%,white);opacity:.22}}
/* echo slivers past the slab */
.r.win .ech{{position:absolute;top:0;bottom:0;z-index:0;left:238px;width:56px;clip-path:polygon(34px 0,100% 0,22px 100%,0 100%);background:color-mix(in srgb,var(--nc) 50%,var(--ink))}}
.r.win .ech+.ech{{left:262px;width:52px;clip-path:polygon(40px 0,100% 0,12px 100%,0 100%);background:linear-gradient(180deg,color-mix(in srgb,var(--nc) 30%,var(--ink)),var(--ink))}}
.r.win > *:not(.slab):not(.ech):not(.ab){{position:relative;z-index:2}}
.r.win:after{{width:228px!important;z-index:3}}
.r.win .rk{{text-shadow:none}}
/* ---- runners-up: mini slab, same recipe ---- */
.r:not(.win) .ph{{background:
    radial-gradient(circle,color-mix(in srgb,var(--nc) 35%,black) 1.1px,transparent 1.4px) 0 0/6px 6px,
    radial-gradient(70% 80% at 55% 20%,color-mix(in srgb,var(--nc) 60%,white),transparent 70%),
    linear-gradient(160deg,color-mix(in srgb,var(--nc) 90%,white),color-mix(in srgb,var(--nc) 60%,black))!important;
  clip-path:polygon(0 0,100% 0,calc(100% - 16px) 100%,0 100%)}}
.r:not(.win) .rk{{background:linear-gradient(180deg,#fff,#d9dbe0)!important}}
'''
src = src.replace('</style>', FL + '</style>', 1)
# inject slab layers into the winner row
i = src.index('class="r win"'); j = src.index('>', i) + 1
src = src[:j] + '<i class="slab"></i><i class="ech"></i><i class="ech"></i>' + src[j:]
open(f'{S}/m_flair4.html','w').write(src)
