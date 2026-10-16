// Standings from GET /results: only final weeks count. `through` = last week to include (null = all).
// Rows are sorted by win % (ties = half), then points for, then name (the server's playoff seeding uses the same order). `results` per row = "W"/"L"/"T" by week.
export function standingsFrom(res, teams, through = null) {
  const rows = new Map();
  const row = t => {
    if (!rows.has(t.id)) rows.set(t.id, { team: t, w: 0, l: 0, t: 0, pf: 0, pa: 0, results: [] });
    return rows.get(t.id);
  };
  (teams || []).forEach(row);
  for (const wk of res?.weeks || []) {
    if (wk.status !== "final" || (through != null && wk.week > through)) continue;
    for (const m of wk.matchups) {
      const a = row(m.home.team), b = row(m.away.team);
      const sa = m.home.score, sb = m.away.score;
      a.pf += sa; a.pa += sb; b.pf += sb; b.pa += sa;
      if (sa > sb) { a.w++; b.l++; a.results.push("W"); b.results.push("L"); }
      else if (sb > sa) { b.w++; a.l++; b.results.push("W"); a.results.push("L"); }
      else { a.t++; b.t++; a.results.push("T"); b.results.push("T"); }
    }
  }
  const pct = r => { const g = r.w + r.l + r.t; return g ? (r.w + r.t / 2) / g : 0; };
  const out = [...rows.values()].sort((x, y) => pct(y) - pct(x) || y.pf - x.pf || x.team.name.localeCompare(y.team.name, undefined, { sensitivity: "base" }));
  const lead = out[0];
  return out.map(r => ({
    ...r, pct: r.w + r.l + r.t ? pct(r).toFixed(3).replace(/^0/, "") : "—",
    gb: lead && r !== lead && (lead.w - r.w) + (r.l - lead.l) > 0 ? ((lead.w - r.w) + (r.l - lead.l)) / 2 : null,
  }));
}

export const finalWeeks = res => (res?.weeks || []).filter(w => w.status === "final").map(w => w.week);
export const recordText = r => `${r.w}-${r.l}${r.t ? `-${r.t}` : ""}`;

// A team color that shows up on the dark page: very dark colors (e.g. a navy close to the card) get lifted toward
// the text color so the stripe and the win-probability bar stay visible.
export function accent(hex) {
  const h = (hex || "").replace("#", "");
  if (h.length !== 6) return "var(--text)";
  const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b < 70 ? `color-mix(in srgb, ${hex} 35%, var(--text))` : hex;
}

// A week's matchups, biggest game first (commissioner, 2026-10-15): by standings — the two teams' ranks added up,
// lowest first; within a matchup the better-ranked team on top. Before any week is final (everyone 0-0): by the two
// teams' combined projected points instead. pairs = [[a, b|null], …] with a/b = { team, proj? }; a bye goes last.
export function bigGameFirst(pairs, rows) {
  const ranked = rows.some(r => r.w + r.l + r.t > 0);
  const rank = new Map(rows.map((r, i) => [r.team.id, i]));
  const rk = side => rank.get(side.team.id) ?? 99;
  const proj = side => side?.proj ?? 0;
  const better = (x, y) => (ranked ? rk(x) - rk(y) : proj(y) - proj(x));
  return pairs
    .map(([a, b]) => (b && better(b, a) < 0 ? [b, a] : [a, b]))
    .sort(([a1, b1], [a2, b2]) => {
      if (!b1 || !b2) return (b1 ? 0 : 1) - (b2 ? 0 : 1);
      return ranked ? (rk(a1) + rk(b1)) - (rk(a2) + rk(b2)) : (proj(a2) + proj(b2)) - (proj(a1) + proj(b1));
    });
}
