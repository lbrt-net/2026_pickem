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
// The schedule's sides and order for a week (results: each matchup's home / away, in schedule order), so a team never
// changes side and the list never reshuffles mid-week (2026-10-23).
export function scheduleOf(results, week) {
  const w = (results?.weeks || []).find(x => x.week === week);
  const side = new Map(), order = new Map();
  (w?.matchups || []).forEach((m, i) => {
    const h = m.home?.team?.id ?? m.home?.id, a = m.away?.team?.id ?? m.away?.id;
    if (h) { side.set(h, 0); order.set(h, i); }
    if (a) { side.set(a, 1); order.set(a, i); }
  });
  return { side, order };
}

// Biggest game first, held steady (2026-10-23): home on the left / top as the schedule has it; ordered by standings
// (they only change between weeks) — before anyone has a record, the schedule's order; a matchup with no games left on
// either side moves to the end, keeping its place among the finished ones. Sides carry `left` = games still to play.
export function bigGameFirst(pairs, rows, sched) {
  const ranked = rows.some(r => r.w + r.l + r.t > 0);
  const rank = new Map(rows.map((r, i) => [r.team.id, i]));
  const rk = side => rank.get(side.team.id) ?? 99;
  const fixed = pairs.map(([a, b]) => (b && sched?.side.get(b.team.id) === 0 ? [b, a] : [a, b]));
  const done = ([a, b]) => (b && (a.left ?? 1) === 0 && (b.left ?? 1) === 0 ? 1 : 0);
  const key = ([a, b]) => (!b ? 999 : ranked ? rk(a) + rk(b) : (sched?.order.get(a.team.id) ?? 0));
  return fixed.map((p, i) => ({ p, i })).sort((x, y) => done(x.p) - done(y.p) || key(x.p) - key(y.p) || x.i - y.i).map(x => x.p);
}
