import { useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { API_BASE, useFantasyApi } from "../../components/fantasy/data";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { GLOSSARY } from "../../components/fantasy/glossary";
import { API } from "../../utils/helpers";
import "./Scoring.css";

// Rules (sidebar "Rules", /scoring). Scoring first, then Schedule, Rosters & locks, Draft, Glossary — with a
// table of contents. Everything is read from the league: GET /scoring (stat weights; the calculator is scored
// by POST /scoring/preview, the same server code as real games) and GET /league/settings (spots, weeks,
// playoffs, draft). Nothing here is hardcoded except the plain-language explanations.

// Raw box score inputs for the calculator (misses are derived from made/attempted server-side).
const INPUTS = [
  ["pts", "Points"], ["fgm", "FG made"], ["fga", "FG attempted"], ["fg3m", "3PT made"],
  ["ftm", "FT made"], ["fta", "FT attempted"], ["oreb", "Off reb"], ["dreb", "Def reb"],
  ["ast", "Assists"], ["stl", "Steals"], ["blk", "Blocks"], ["tov", "Turnovers"], ["blkd", "Own shots blocked"],
];
const EXAMPLES = [
  ["Makes a 3-pointer", "3 points + 0.5 for the 3 = 3.5"],
  ["Makes 2 of 3 free throws", "2 points − 1 for the miss = 1"],
  ["Misses a layup and gets blocked", "−0.5 missed shot − 0.5 blocked = −1"],
];
const SECTIONS = [["scoring", "Scoring"], ["schedule", "Schedule"], ["rosters", "Rosters & locks"], ["draft", "Draft"], ["glossary", "Glossary"]];
const SPOTS = [["G", "G"], ["F", "F"], ["C", "C"], ["TEAM", "TM"], ["FLEX", "FLX"], ["BENCH", "Bench"]];
const TYPE_NAMES = { snake: "Snake", snake_3rr: "Snake, 3rd-round reversal", linear: "Normal order", auction: "Auction" };
const fmt = n => (n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : "0");
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const clock = s => (s >= 60 ? `${Math.round(s / 60)} min` : `${s} sec`);

function Section({ id, title, children }) {
  return (
    <section id={id} className="ru-sec">
      <h2 className="ru-h"><span aria-hidden="true" />{title}</h2>
      {children}
    </section>
  );
}

function List({ rows }) {
  return <dl className="ru-list">{rows.filter(Boolean).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>;
}

export default function Scoring() {
  const [scenario] = useFantasyScenario();
  const rules = useFantasyApi("scoring");
  const league = useFantasyApi("league/settings");
  const [line, setLine] = useState({ pts: 28, fgm: 10, fga: 20, fg3m: 3, ftm: 5, fta: 6, oreb: 2, dreb: 7, ast: 6, stl: 2, blk: 1, tov: 3, blkd: 1 });
  const [result, setResult] = useState(null);

  useEffect(() => {
    let current = true;
    fetch(`${API}${API_BASE}/scoring/preview?scenario=${scenario}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(line),
    }).then(r => (r.ok ? r.json() : null)).catch(() => null).then(v => { if (current) setResult(v); });
    return () => { current = false; };
  }, [line, scenario]);

  const s = league?.settings;
  const weeks = league?.weeks || [];
  const label = key => rules?.rules?.find(r => r.key === key)?.label ?? key;
  const regular = weeks.filter(w => w.kind === "regular");
  const playoffs = weeks.filter(w => w.kind === "playoffs");
  const allStar = weeks.find(w => w.all_star);
  const rounds = s ? Object.values(s.roster_slots).reduce((a, b) => a + b, 0) : null;
  const auction = s?.draft_type === "auction";

  return (
    <FantasyShell title="Rules">
      <nav className="ru-toc" aria-label="On this page">
        {SECTIONS.map(([id, t], i) => <a key={id} href={`#${id}`}><span>{i + 1}</span>{t}</a>)}
      </nav>

      <Section id="scoring" title="Scoring">
        <div className="ru-card">
          <div className="ru-sub">How a week is scored</div>
          <ol className="ru-steps">
            <li><b>Every game</b> a player plays gets fantasy points from his box score, with the weights below.</li>
            <li><b>A player's week is his best single game</b> that week (his MAX) — not the total, not the average. Every game is a free shot at it; a quiet night costs nothing.</li>
            <li><b>An NBA team's week</b> is {rules?.team?.week === "best_game" ? "its best game of the week, scored with the team rules below" : "its games added up, scored with the team rules below"}.</li>
            <li><b>Your team's score</b> is every starting spot added up. Bench spots don't count.</li>
            <li><b>The higher score wins the matchup.</b> A tie counts as half a win.</li>
          </ol>
        </div>
        <div className="ru-grid">
          <div className="ru-card">
            <div className="ru-sub">Points per stat</div>
            {rules === undefined ? <p className="ru-p">Loading…</p> : !rules ? <p className="ru-p">Couldn't load the rules.</p> : (
              <table className="ru-tb">
                <thead><tr><th className="l">Stat</th><th className="l">What it is</th><th>Points</th></tr></thead>
                <tbody>
                  {rules.rules.map(r => (
                    <tr key={r.key}><td className="l">{r.label}</td><td className="l">{r.name}{rules.pending?.[r.key] ? ` · ${rules.pending[r.key]}` : ""}</td>
                      <td className={r.points < 0 ? "neg" : ""}>{fmt(r.points)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="ru-card">
            <div className="ru-sub">NBA teams · per game</div>
            {rules?.team && (
              <table className="ru-tb">
                <thead><tr><th className="l">Rule</th><th>Points</th></tr></thead>
                <tbody>
                  {rules.team.components.map(c => (
                    <tr key={c.id}><td className="l">{c.name}</td>
                      <td className={c.points < 0 ? "neg" : ""}>{c.type === "per_stat" ? `${fmt(c.points)} each` : c.type === "steps" ? `${fmt(c.points)} each` : fmt(c.points)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="ru-card">
            <div className="ru-sub">Examples · one play</div>
            <table className="ru-tb">
              <tbody>{EXAMPLES.map(([t, m]) => <tr key={t}><td className="l">{t}</td><td className="l">{m}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
        <div className="ru-card">
          <div className="ru-sub">Calculator · enter a stat line</div>
          <div className="ru-calc">
            {INPUTS.map(([key, name]) => (
              <label key={key}>{name}
                <input type="number" min={0} value={line[key] ?? 0} onChange={e => setLine(l => ({ ...l, [key]: Math.max(0, Number(e.target.value) || 0) }))} />
              </label>
            ))}
          </div>
          {result && (
            <div className="ru-calc-out">
              <table className="ru-tb">
                <thead><tr>{Object.entries(result.breakdown).filter(([, v]) => v !== 0).map(([k]) => <th key={k}>{label(k)}</th>)}<th>FPTS</th></tr></thead>
                <tbody><tr>{Object.entries(result.breakdown).filter(([, v]) => v !== 0).map(([k, v]) => <td key={k} className={v < 0 ? "neg" : ""}>{fmt(v)}</td>)}<td><b>{result.fantasy_points}</b></td></tr></tbody>
              </table>
            </div>
          )}
        </div>
      </Section>

      <Section id="schedule" title="Schedule">
        {s && (
          <div className="ru-grid">
            <div className="ru-card">
              <List rows={[
                ["Weeks", "Monday to Sunday. Each week is one matchup."],
                ["Matchups", s.matchup_schedule === "round_robin" ? "Round robin — everyone plays everyone, then it repeats." : s.matchup_schedule],
                s.fuse_all_star && ["All-Star break", `Joined with the week around it into one ${allStar ? `${allStar.calendar_weeks}-week` : "longer"} period — still one best game.`],
                ["Regular season", `${regular.length} weeks; ends ${s.cutoff_days} days before the NBA's regular season does.`],
                ["Playoffs", `Top ${s.playoff_teams} teams · ${s.playoff_rounds.map(r => `${r.name}${r.weeks > 1 ? ` (${r.weeks} weeks)` : ""}`).join(" → ")}`],
                league.playoff_byes > 0 && ["Byes", `Top ${league.playoff_byes} seeds skip the first round.`],
              ]} />
            </div>
            <div className="ru-card">
              <div className="ru-scroll">
                <table className="ru-tb weeks">
                  <thead><tr><th className="l">Wk</th><th className="l">Dates</th><th className="l">Week</th></tr></thead>
                  <tbody>
                    {weeks.map(w => (
                      <tr key={w.week}><td className="l">{w.week}</td><td className="l">{MD(w.start)} – {MD(w.end)}</td>
                        <td className="l">{w.kind === "playoffs" ? w.label : w.all_star ? `All-Star · ${w.calendar_weeks} weeks` : w.calendar_weeks > 1 ? `${w.calendar_weeks} weeks` : ""}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
        {playoffs.length === 0 && !s && <p className="ru-p">Loading…</p>}
      </Section>

      <Section id="rosters" title="Rosters & locks">
        {s && (
          <div className="ru-card">
            <List rows={[
              ["Spots", <span className="ru-spots">{SPOTS.filter(([k]) => s.roster_slots[k]).map(([k, l]) => <span key={k}>{l} <i>{s.roster_slots[k]}</i></span>)}</span>],
              ["Who fits", "G, F, C: a player at that position. TM: an NBA team. FLX: any player or NBA team. Bench: anyone — Bench doesn't score."],
              ["Locks", "Each player locks 5 minutes before his NBA team's first game of the week."],
              ["Locked", "A locked player can't be moved that week. Set next week's lineup from next week."],
            ]} />
          </div>
        )}
      </Section>

      <Section id="draft" title="Draft">
        {s && (
          <div className="ru-card">
            <List rows={[
              ["Type", TYPE_NAMES[s.draft_type] || s.draft_type],
              !auction && ["Rounds", `${rounds} — one per roster spot, bench included`],
              !auction && ["Pick clock", clock(s.pick_seconds)],
              auction && ["Budget", `$${s.auction_budget} per team · $${s.auction_min_bid} minimum bid`],
              auction && ["Clocks", `${clock(s.nomination_seconds)} to nominate · ${clock(s.bid_seconds)} per bid`],
              ["Clock runs out", auction ? "Auto-nominate: the first player in your queue who fits, else the best available." : "Auto-pick: the first player in your queue who fits your roster, else the best available."],
              ["Best available", "Ranked by PROJ MAX."],
              ["Starts", s.draft_start_at ? new Date(s.draft_start_at).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }) : "Not scheduled yet"],
            ]} />
          </div>
        )}
      </Section>

      <Section id="glossary" title="Glossary">
        <div className="ru-card"><List rows={GLOSSARY} /></div>
      </Section>
    </FantasyShell>
  );
}
