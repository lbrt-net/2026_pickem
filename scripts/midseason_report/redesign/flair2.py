import sys, re
S = sys.argv[1]
src = open(f'{S}/m_scoring2.html').read()
g = src[src.index('<div class="grid">'):]
card = re.findall(r'(?<=</div>)<section class="aw">.*?</section>', g, re.S)[1]
FL = '''
.grid{grid-template-columns:minmax(0,640px)!important;padding-top:30px}
/* header: thin double rule, award name with a team-color underscore */
.aw h2{border-bottom:0!important;padding-bottom:10px!important}
.aw h2+.r{box-shadow:inset 0 2px 0 var(--text)}
/* winner row: headshot rises out of the row, standing on a team-color floor line */
.r.win{overflow:visible;margin-top:26px;background:radial-gradient(70% 140% at 22% 100%,color-mix(in srgb,var(--tc) 38%,transparent),transparent 60%),linear-gradient(90deg,var(--surface),var(--bg) 85%)!important}
.r.win .ph{height:150px!important;width:170px!important;margin-top:-38px;background:none!important;position:relative;z-index:2}
.r.win{grid-template-columns:52px 170px minmax(0,1fr) auto!important}
.r.win:after{content:"";position:absolute;left:52px;width:170px;bottom:0;height:3px;background:var(--tc);z-index:3}
.r.win .rk{font-size:80px!important;line-height:.8;align-self:end;padding-bottom:12px;letter-spacing:-.04em}
.r.win .fn{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:2px}
.r.win .ln{font-size:44px!important;line-height:.95}
.r.win .v b{font-size:54px!important;letter-spacing:-.01em}
.r.win .v span{display:inline-block;padding-top:6px;border-top:2px solid var(--tc);margin-top:4px}
/* corner notch on the winner row (solid fill, so the cut is allowed) */
.r.win{clip-path:polygon(0 -60px,100% -60px,100% calc(100% - 14px),calc(100% - 14px) 100%,0 100%)}
/* band: ordinal superscripts, a rank meter under each rank */
.ctx{padding:14px 18px 16px 22px!important}
.rk2 .c{border-left:0!important;padding:0 12px 0 0!important}
.rk2 b{font-size:34px!important;line-height:1!important;margin-top:4px}
.rk2 sup{font-size:.42em;vertical-align:top;position:relative;top:.18em;margin-left:1px;letter-spacing:.04em}
.rk2 .m{position:relative;display:block;width:100%;height:3px;margin:7px 0 6px;background:var(--surface-3)}
.rk2 .m i{position:absolute;top:-3px;width:3px;height:9px;transform:translateX(-50%)}
.rk2 .c.g .m i{background:#4ade80}.rk2 .c.b .m i{background:#f87171}
.rk2 .m{background:var(--surface-3)!important;height:5px!important}.rk2 .m u{position:absolute;left:0;top:0;bottom:0}
.rk2 .c.g .m u{background:linear-gradient(90deg,color-mix(in srgb,#22c55e 25%,var(--surface-3)),#22c55e)}
.rk2 .c.b .m u{background:linear-gradient(90deg,color-mix(in srgb,#ef4444 25%,var(--surface-3)),#ef4444)}
.rk2 .m i{top:-3px!important;height:11px!important}
.rk2 .v{font-size:12px;font-weight:700}.rk2 .v em{font-style:normal;margin-left:6px}
.rk2 .c.g .v em{color:#4ade80}.rk2 .c.b .v em{color:#f87171}
/* runners-up: rank numerals sit in a narrow team-color column */
.r:not(.win) .rk{align-self:stretch;display:flex;align-items:center;justify-content:center;padding:0!important}
.r:not(.win):before{width:44px!important;background:linear-gradient(90deg,color-mix(in srgb,var(--tc) 30%,transparent),transparent)!important;border-left:3px solid var(--tc)}
'''
out = src[:src.index('<div class="grid">')] + '<div class="grid"><div>' + card + '</div></div>'
open(f'{S}/m_flair2.html','w').write(out.replace('</style>', FL + '</style>', 1))
