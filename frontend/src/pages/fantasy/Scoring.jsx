import { useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { API_BASE, useFantasyApi } from "../../components/fantasy/data";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { GLOSSARY } from "../../components/fantasy/glossary";
import { API } from "../../utils/helpers";
import "./Scoring.css";

// Rules (sidebar "Rules", /scoring): the detailed reference, design "Rules v2" on the canvas. Numbered sections in the
// order of the group summary (draft, your week, lineup, scoring, moves, season, prizes, glossary)
// with an "On this page" index. Every number comes from the league: GET /scoring (player + NBA team rules; the
// calculator is scored by POST /scoring/preview, the same server code as real games) and GET /league/settings
// (spots, IR, weeks, playoffs, draft, plus `constants`: lock minutes, waiver days, IR lock weeks, warm-up). Only the
// week example's three game scores are made up — they show the idea, not a rule.

const INPUTS = [
  ["pts", "PTS"], ["fgm", "FGM"], ["fga", "FGA"], ["fg3m", "3PM"], ["ftm", "FTM"], ["fta", "FTA"], ["oreb", "OREB"],
  ["dreb", "DREB"], ["ast", "AST"], ["stl", "STL"], ["blk", "BLK"], ["tov", "TO"], ["blkd", "BLKD"], ["clutch_pts", "Clutch"],
];
const SECTIONS = [["draft", "Draft"], ["week", "Your week"], ["lineups", "Lineups & locks"], ["scoring", "Scoring"], ["moves", "Adds, drops & waivers"], ["season", "Season & playoffs"], ["prizes", "Prize pool"], ["glossary", "Glossary"]];
const SPOT_ORDER = ["G", "F", "C", "TEAM", "FLEX", "BENCH"];
const SPOT = { G: ["G", "guard"], F: ["F", "forward"], C: ["C", "center"], TEAM: ["TM", "NBA team"], FLEX: ["FLX", "anyone"], BENCH: ["Bench", "no points"] };
const TYPE_NAMES = { snake: "Snake", snake_3rr: "Snake, 3rd-round reversal", linear: "Same order every round", auction: "Auction" };
const EXAMPLE = [["Mon", 31.5], ["Wed", 48], ["Sat", 22.5]]; // made-up scores for the week picture
const num = n => (Number.isInteger(n) ? String(n) : String(Math.round(n * 10) / 10));
const fmt = n => (n > 0 ? `+${num(n)}` : n < 0 ? `−${num(Math.abs(n))}` : "0");
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const MON = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "short" });
const secs = s => (s >= 60 && s % 60 === 0 ? `${s / 60} minute${s === 60 ? "" : "s"}` : `${s} seconds`);
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
// short names for the season strip's cells: Quarterfinals → QF, Semifinals → SF, the last round → Final
const short = (name, last) => (last ? "Final" : /finals?$/i.test(name) ? `${name[0].toUpperCase()}F` : name.slice(0, 3));

// One NBA team rule's points for a given points-allowed total (the "steps" / "threshold" rules), else null.
function allowedPoints(c, allowed) {
  if (c.stat !== "pts_allowed") return null;
  if (c.type === "steps") return allowed < c.below ? (c.below - Math.max(allowed, c.floor ?? -Infinity)) / (c.step || 1) * c.points : 0;
  if (c.type === "threshold") return allowed < c.below ? c.points : 0;
  return null;
}

// The bracket: standard seeding into 2^rounds slots (1 v 8, 4 v 5, 2 v 7, 3 v 6, …); slots past the last seed are
// byes. Returns each round's real games as [side, side] labels.
function bracket(teams, rounds) {
  let order = [1];
  while (order.length < 2 ** rounds.length) order = order.flatMap(s => [s, order.length * 2 + 1 - s]);
  let nodes = order.map(s => (s <= teams ? { seeds: [s], label: `Seed ${s}` } : null));
  return rounds.map(r => {
    const games = [], next = [];
    for (let i = 0; i < nodes.length; i += 2) {
      const a = nodes[i], b = nodes[i + 1];
      if (a && b) {
        games.push([a.label, b.label]);
        const seeds = [...a.seeds, ...b.seeds].sort((x, y) => x - y);
        next.push({ seeds, label: seeds.length <= 2 ? `${seeds.join("/")} winner` : `${r.name} winner` });
      } else next.push(a || b);
    }
    nodes = next;
    return { ...r, games };
  });
}

function Section({ id, n, title, children }) {
  return (
    <section id={id} className="ru-sec">
      <h2 className="ru-h"><span className="ru-n">{n}</span>{title}</h2>
      {children}
    </section>
  );
}

function Rows({ rows }) {
  return <dl className="ru-rows">{rows.filter(Boolean).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>;
}

export default function Scoring() {
  const [scenario] = useFantasyScenario();
  const rules = useFantasyApi("scoring");
  const league = useFantasyApi("league/settings");
  const [line, setLine] = useState({ pts: 28, fgm: 10, fga: 20, fg3m: 3, ftm: 5, fta: 6, oreb: 2, dreb: 7, ast: 6, stl: 2, blk: 1, tov: 3, blkd: 1, clutch_pts: 4 });
  const [result, setResult] = useState(null);
  const [here, setHere] = useState("draft");

  useEffect(() => {
    let current = true;
    fetch(`${API}${API_BASE}/scoring/preview?scenario=${scenario}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(line),
    }).then(r => (r.ok ? r.json() : null)).catch(() => null).then(v => { if (current) setResult(v); });
    return () => { current = false; };
  }, [line, scenario]);

  // "On this page": the section you're reading
  useEffect(() => {
    const io = new IntersectionObserver(es => {
      const top = es.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (top) setHere(top.target.id);
    }, { rootMargin: "-20% 0px -70% 0px" });
    SECTIONS.forEach(([id]) => { const el = document.getElementById(id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, [rules, league]);

  const s = league?.settings;
  const k = league?.constants || {};
  const weeks = league?.weeks || [];
  const regular = weeks.filter(w => w.kind === "regular");
  const allStar = weeks.find(w => w.all_star);
  const byes = league?.playoff_byes || 0;
  const auction = s?.draft_type === "auction";
  const spots = s ? SPOT_ORDER.flatMap(t => Array(s.roster_slots[t] || 0).fill(t)) : [];
  const player = rules?.player || {};
  const team = rules?.team || {};
  const pw = Object.fromEntries((player.components || []).map(c => [c.id, c.points]));
  const p = id => pw[id] || 0;
  const playerBest = player.week !== "sum";
  const weekScore = playerBest ? Math.max(...EXAMPLE.map(e => e[1])) : EXAMPLE.reduce((a, e) => a + e[1], 0);
  const held = 98;
  const heldPts = (team.components || []).map(c => allowedPoints(c, held)).filter(v => v != null).reduce((a, b) => a + b, 0);
  const examples = [
    ["Makes a 3", 3 * p("pts") + p("fg3m")],
    ["Makes 2 of 3 free throws", 2 * p("pts") + p("ftx")],
    ["Misses a layup, gets blocked", p("fgx") + p("blkd")],
    pw.clutch_pts != null && ["Go-ahead 3 in clutch time", 3 * p("pts") + p("fg3m") + 3 * p("clutch_pts")],
    heldPts ? [`NBA team holds the opponent to ${held}`, heldPts] : null,
  ].filter(Boolean);
  const weights = Object.fromEntries((player.components || []).map(c => [c.label, c]));
  const glossary = GLOSSARY.map(([term, text]) => [term, weights[term] ? `${text} ${fmt(weights[term].points)} each.` : text]);
  const startsAt = s?.draft_start_at
    ? new Date(s.draft_start_at).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" })
    : "Not scheduled yet";
  const months = weeks.map((w, i) => (i === 0 ? MD(w.start) : MON(w.start) !== MON(weeks[i - 1].start) ? MON(w.start) : ""));
  const cols = weeks.reduce((a, w) => a + (w.calendar_weeks || 1), 0);

  return (
    <FantasyShell title="Rules">
      <div className="ru">
        <div className="ru-body">
          <Section id="draft" n={1} title="Draft">
            {s && (
              <div className="ru-card">
                <Rows rows={[
                  ["Type", auction
                    ? `Auction · $${s.auction_budget} per team · $${s.auction_min_bid} minimum bid · ${plural(spots.length, "player")} each`
                    : `${TYPE_NAMES[s.draft_type] || s.draft_type} · ${plural(spots.length, "round")}, one per roster spot`],
                  ["Starts", `${startsAt}${s.draft_start_at ? `, after a ${k.warmup_seconds ?? 10}-second warm-up` : ""}`],
                  !auction && ["Pick clock", `${secs(s.pick_seconds)}${s.pick_seconds_by_round?.length ? ` (rounds 1–${s.pick_seconds_by_round.length}: ${s.pick_seconds_by_round.map(secs).join(", ")})` : ""}. If it runs out, the first player in your queue who fits is picked, else the best available.`],
                  auction && ["Nominating", `Teams take turns in draft order. ${secs(s.nomination_seconds)}; if it runs out, the first player in your queue who fits is nominated at $${s.auction_min_bid}, else the best available.`],
                  auction && ["Bidding", `Each bid beats the high bid by at least ${s.auction_min_raise_pct}% of it, rounded up ($1 at least). The ${secs(s.bid_seconds)} clock restarts on every bid.`],
                  auction && s.auction_open_step_ms > 0 && ["Bidding opens", `The team after the nominator can bid right away; each team after waits ${s.auction_open_step_ms / 1000} seconds more.`],
                  auction && ["Money", `You can spend everything on one player. Once you can't afford $${s.auction_min_bid}, you're done. Your roster is who you won.`],
                ]} />
              </div>
            )}
          </Section>

          <Section id="week" n={2} title="Your week">
            <div className="ru-card">
              <div className="ru-sub">{playerBest ? "A player's week is his best game" : "A player's week is his games added up"}</div>
              <div className="ru-week">
                {EXAMPLE.map(([d, v]) => <div key={d} className={`ru-game${playerBest && v === weekScore ? " best" : ""}`}><span>{d}</span><b>{num(v)}</b></div>)}
                <span className="ru-arrow" aria-hidden="true">→</span>
                <div className="ru-wk"><span>His week</span><b>{num(weekScore)}</b></div>
              </div>
              <Rows rows={[
                ["Player", playerBest ? "Fantasy points from his best single game that week. More games = more chances; a bad night costs nothing." : "Fantasy points from every game he plays that week, added up."],
                ["NBA team (TM)", team.week === "best_game" ? "Its best game of the week, scored with the NBA team rules below." : "Its games that week added up, scored with the NBA team rules below."],
                ["Your score", "Every starting spot added up. Bench and IR don't count."],
                ["Matchup", "Higher score wins the week. A tie is half a win."],
              ]} />
            </div>
          </Section>

          <Section id="lineups" n={3} title="Lineups & locks">
            {s && (
              <div className="ru-card">
                <div className="ru-strip">
                  {spots.map((t, i) => (
                    <div key={i} className={`ru-spot${t === "BENCH" ? " bench" : ""}${t === "BENCH" && spots[i - 1] !== "BENCH" ? " gap" : ""}`}>{SPOT[t][0]}<span>{SPOT[t][1]}</span></div>
                  ))}
                  {Array.from({ length: s.ir_slots || 0 }, (_, i) => <div key={`ir${i}`} className={`ru-spot ir${i === 0 ? " gap" : ""}`}>IR<span>extra spot</span></div>)}
                </div>
                <Rows rows={[
                  ["Who fits", "G / F / C: a player listed at that position. TM: an NBA team. FLX: any player or NBA team. Bench: anyone."],
                  ["Locks", `Each player locks ${k.lock_minutes ?? 5} minutes before his NBA team's first game of the week. Locked players can't change spots until next week.`],
                  ["Drops", "Anyone, any time, locked or not. Dropped after his lock, he still counts for you that week."],
                  s.ir_slots > 0 && ["IR", `${plural(s.ir_slots, "extra spot")}, not drafted, ${s.ir_slots === 1 ? "never scores" : "never score"}. Only a player who's Out or Day-to-Day can go there. Moving him in locks him on IR for the next ${k.ir_lock_weeks ?? 4} weeks: no moves, no drop.`],
                ]} />
              </div>
            )}
          </Section>

          <Section id="scoring" n={4} title="Scoring">
            <div className="ru-grid">
              <div className="ru-card">
                <div className="ru-sub">Points per stat · players</div>
                {rules === undefined ? <p className="ru-p">Loading…</p> : !rules ? <p className="ru-p">Couldn't load the rules.</p> : (
                  <table className="ru-tb"><tbody>
                    {(player.components || []).map(c => <tr key={c.id}><td>{c.name}</td><td className={`p${c.points < 0 ? " neg" : ""}`}>{fmt(c.points)}</td></tr>)}
                  </tbody></table>
                )}
              </div>
              <div className="ru-card">
                <div className="ru-sub">Points per game · NBA teams</div>
                <table className="ru-tb"><tbody>
                  {(team.components || []).map(c => (
                    <tr key={c.id}><td>{c.name}</td><td className="p">{c.type === "per_stat" || c.type === "steps" ? `${fmt(c.points)} each` : fmt(c.points)}</td></tr>
                  ))}
                </tbody></table>
              </div>
            </div>
            <div className="ru-grid wide">
              <div className="ru-card">
                <div className="ru-sub">One play</div>
                <table className="ru-tb"><tbody>
                  {examples.map(([t, v]) => <tr key={t}><td>{t}</td><td className="p">{fmt(v)}</td></tr>)}
                </tbody></table>
              </div>
            <div className="ru-card">
              <div className="ru-sub">Calculator</div>
              <div className="ru-calc">
                {INPUTS.map(([key, name]) => (
                  <label key={key}>{name}
                    <input type="number" min={0} value={line[key] ?? 0} onChange={e => setLine(l => ({ ...l, [key]: Math.max(0, Number(e.target.value) || 0) }))} />
                  </label>
                ))}
              </div>
              {result && (
                <div className="ru-calc-out">
                  <span>{Object.entries(result.breakdown).filter(([, v]) => v !== 0).map(([key, v]) => `${(player.components || []).find(c => c.id === key)?.label || key} ${fmt(v)}`).join(" · ")}</span>
                  <b>{num(result.fantasy_points)}</b>
                </div>
              )}
            </div>
            </div>
          </Section>

          <Section id="moves" n={5} title="Adds, drops & waivers">
            <div className="ru-card">
              <div className="ru-flow">
                <div className="ru-step"><span className="k">Free agent</span><b>Add him now</b>Instant. Your roster has to fit after the move.</div>
                <div className="ru-step"><span className="k">Dropped player</span><b>Waivers · {plural(k.waiver_days ?? 2, "day")}</b>Nobody can add him, not even the team that dropped him. Put in a claim.</div>
                <span className="ru-arrow" aria-hidden="true">→</span>
                <div className="ru-step"><span className="k">Claims settle</span><b>Lowest team wins</b>Worst record, then fewest points. No claim → free agent.</div>
              </div>
              <Rows rows={[
                ["Not a real drop", "Added and dropped before he ever locked in your lineup: straight back to free agent, no waivers."],
                ["Opens", "After the draft."],
              ]} />
            </div>
          </Section>

          <Section id="season" n={6} title="Season & playoffs">
            {s && (
              <>
                <div className="ru-card">
                  <div className="ru-sub">{plural(cols, "week")} · Monday to Sunday · one matchup each</div>
                  <div className="ru-season" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
                    {weeks.map(w => (
                      <div key={w.week} title={`${w.label} · ${MD(w.start)} – ${MD(w.end)}`} className={w.kind === "playoffs" ? "po" : w.all_star ? "as" : ""}
                        style={{ gridColumn: `span ${w.calendar_weeks || 1}` }}>
                        {w.kind === "playoffs" ? short(w.label, w === weeks[weeks.length - 1]) : w.all_star ? "All-Star" : w.week}
                      </div>
                    ))}
                  </div>
                  <div className="ru-months" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
                    {weeks.map((w, i) => <span key={w.week} style={{ gridColumn: `span ${w.calendar_weeks || 1}` }}>{months[i]}</span>)}
                  </div>
                  <Rows rows={[
                    ["Regular season", `${plural(regular.length, "week")}, ${s.matchup_schedule === "round_robin" ? "round robin: everyone plays everyone, then again" : s.matchup_schedule}. ${s.cutoff_days ? `Ends ${s.cutoff_days} days before the NBA's does.` : "Runs to the NBA's last week."}`],
                    s.fuse_all_star && allStar && ["All-Star break", `Joined with the week after it into one ${allStar.calendar_weeks}-week matchup. ${playerBest ? "Still one best game." : ""}`],
                  ]} />
                </div>
                <div className="ru-card">
                  <div className="ru-sub">Playoffs · top {s.playoff_teams}{byes > 0 ? ` · top ${byes} skip the first round` : ""}</div>
                  <div className="ru-bracket" style={{ gridTemplateColumns: `repeat(${s.playoff_rounds.length}, minmax(0, 1fr))` }}>
                    {bracket(s.playoff_teams, s.playoff_rounds).map(r => (
                      <div key={r.name} className="ru-col">
                        <span className="k">{r.name} · {plural(r.weeks, "week")}</span>
                        {r.games.map(([a, b]) => <div key={a + b} className="ru-m"><span>{a}</span><span>{b}</span></div>)}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </Section>

          <Section id="prizes" n={7} title="Prize pool">
            <div className="ru-card">
              <div className="ru-uc"><span>To be decided</span></div>
            </div>
          </Section>

          <Section id="glossary" n={8} title="Glossary">
            <div className="ru-card"><Rows rows={glossary} /></div>
          </Section>
        </div>

        <nav className="ru-index" aria-label="On this page">
          <span className="k">On this page</span>
          {SECTIONS.map(([id, t], i) => <a key={id} href={`#${id}`} className={here === id ? "on" : ""}><b>{i + 1}</b>{t}</a>)}
        </nav>
      </div>
    </FantasyShell>
  );
}
