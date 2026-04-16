import { useState, useEffect, useRef } from "react";
import "./App.css";

const ROUNDS = ["First round", "Conf semis", "Conf finals", "NBA Finals"];
const COMP_W = 54;
const GAP = 6;
const N_COLS = 7;

const W = [
  [
    {
      id: "w0", locked: true,
      top: { s: 1, n: "Thunder" }, bot: { s: 8, n: "Play-in" },
      players: ["Shai Gilgeous-Alexander", "Jalen Williams", "Chet Holmgren", "Isaiah Hartenstein"],
    },
    {
      id: "w1", locked: false,
      top: { s: 2, n: "Spurs" }, bot: { s: 7, n: "Trail Blazers" },
      players: ["Victor Wembanyama", "Devin Vassell", "Scoot Henderson", "Anfernee Simons", "Jerami Grant"],
    },
    {
      id: "w2", locked: false,
      top: { s: 3, n: "Nuggets" }, bot: { s: 6, n: "Wolves" },
      players: ["Nikola Jokic", "Jamal Murray", "Michael Porter Jr.", "Anthony Edwards", "Julius Randle"],
    },
    {
      id: "w3", locked: false,
      top: { s: 4, n: "Lakers" }, bot: { s: 5, n: "Rockets" },
      players: ["LeBron James", "Anthony Davis", "Austin Reaves", "Alperen Sengun", "Jalen Green"],
    },
  ],
  [
    { id: "w4", locked: true, top: { s: null, n: "TBD" }, bot: { s: null, n: "TBD" }, players: [] },
    { id: "w5", locked: true, top: { s: null, n: "TBD" }, bot: { s: null, n: "TBD" }, players: [] },
  ],
  [
    { id: "w6", locked: true, top: { s: null, n: "TBD" }, bot: { s: null, n: "TBD" }, players: [] },
  ],
];

const E = [
  [
    {
      id: "e0", locked: true,
      top: { s: 1, n: "Pistons" }, bot: { s: 8, n: "Play-in" },
      players: ["Cade Cunningham", "Jaden Ivey", "Ausar Thompson", "Tobias Harris"],
    },
    {
      id: "e1", locked: true,
      top: { s: 2, n: "Celtics" }, bot: { s: 7, n: "76ers" },
      players: ["Jayson Tatum", "Jaylen Brown", "Jrue Holiday", "Tyrese Maxey", "Paul George"],
    },
    {
      id: "e2", locked: false,
      top: { s: 3, n: "Knicks" }, bot: { s: 6, n: "Raptors" },
      players: ["Jalen Brunson", "Karl-Anthony Towns", "OG Anunoby", "Scottie Barnes", "RJ Barrett"],
    },
    {
      id: "e3", locked: false,
      top: { s: 4, n: "Cavaliers" }, bot: { s: 5, n: "Hawks" },
      players: ["Donovan Mitchell", "Darius Garland", "Evan Mobley", "Trae Young", "Dyson Daniels"],
    },
  ],
  [
    { id: "e4", locked: true, top: { s: null, n: "TBD" }, bot: { s: null, n: "TBD" }, players: [] },
    { id: "e5", locked: true, top: { s: null, n: "TBD" }, bot: { s: null, n: "TBD" }, players: [] },
  ],
  [
    { id: "e6", locked: true, top: { s: null, n: "TBD" }, bot: { s: null, n: "TBD" }, players: [] },
  ],
];

const F = [
  { id: "f0", locked: true, top: { s: null, n: "West rep" }, bot: { s: null, n: "East rep" }, players: [] },
];

const COLS = [
  [W[0], "west", "West · R1"],
  [W[1], "west", "West · R2"],
  [W[2], "west", "West CF"],
  [F, "finals", "Finals"],
  [E[2], "east", "East CF"],
  [E[1], "east", "East · R2"],
  [E[0], "east", "East · R1"],
];

const ACTIVE_COLS = [[0, 6], [1, 5], [2, 4], [3]];

function pickClass(conf) {
  return conf === "west" ? "wp" : conf === "east" ? "ep" : "fp";
}
function dotClass(conf) {
  return conf === "west" ? "dw" : conf === "east" ? "de" : "df";
}

function MatchupCard({ matchup, conf, picks, onPick }) {
  const p = pickClass(conf);
  const pick = picks[matchup.id] || {};
  const tp = pick.winner === "top";
  const bp = pick.winner === "bot";

  function setPick(field, value) {
    onPick(matchup.id, { ...pick, [field]: value });
  }

  if (matchup.locked) {
    return (
      <div className="matchup locked">
        <div className="locked-badge">Locked</div>
        <div className="trow">
          {matchup.top.s !== null && <span className="seed">{matchup.top.s}</span>}
          <span className="tname muted">{matchup.top.n}</span>
        </div>
        <div className="mdiv" />
        <div className="trow">
          {matchup.bot.s !== null && <span className="seed">{matchup.bot.s}</span>}
          <span className="tname muted">{matchup.bot.n}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="matchup">
      <div className={`trow ${tp ? p : ""}`} onClick={() => setPick("winner", tp ? null : "top")}>
        {matchup.top.s !== null && <span className="seed">{matchup.top.s}</span>}
        <span className={`tname ${tp ? p : ""}`}>{matchup.top.n}</span>
        {tp && <span className="checkmark">✓</span>}
      </div>
      <div className="mdiv" />
      <div className={`trow ${bp ? p : ""}`} onClick={() => setPick("winner", bp ? null : "bot")}>
        {matchup.bot.s !== null && <span className="seed">{matchup.bot.s}</span>}
        <span className={`tname ${bp ? p : ""}`}>{matchup.bot.n}</span>
        {bp && <span className="checkmark">✓</span>}
      </div>

      <div className="pick-extras">
        <div className="pick-row">
          <span className="pick-label">Games</span>
          <div className="games-picker">
            {[4, 5, 6, 7].map((g) => (
              <button
                key={g}
                className={`game-btn ${pick.games === g ? "selected " + p : ""}`}
                onClick={() => setPick("games", pick.games === g ? null : g)}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        <div className="pick-row">
          <span className="pick-label">Stat leader</span>
          <select
            className="player-select"
            value={pick.statLeader || ""}
            onChange={(e) => setPick("statLeader", e.target.value || null)}
          >
            <option value="">— pick a player —</option>
            {matchup.players.map((pl) => (
              <option key={pl} value={pl}>{pl}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function CompressedCol({ matchups, conf, label, picks }) {
  return (
    <div className="cinner">
      <span className="vlabel">{label}</span>
      {matchups.map((m) => (
        <div key={m.id} className={`dot ${picks[m.id]?.winner ? dotClass(conf) : ""}`} />
      ))}
    </div>
  );
}

export default function App() {
  const [round, setRound] = useState(0);
  const [picks, setPicks] = useState({});
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [renderRound, setRenderRound] = useState(0);
  const gridRef = useRef(null);
  const timerRef = useRef(null);

  function computeWidths(activeRound, containerWidth) {
    const active = new Set(ACTIVE_COLS[activeRound]);
    const nActive = ACTIVE_COLS[activeRound].length;
    const nComp = N_COLS - nActive;
    const totalGaps = (N_COLS - 1) * GAP;
    const compTotal = nComp * COMP_W;
    const activeW = (containerWidth - totalGaps - compTotal) / nActive;
    return Array.from({ length: N_COLS }, (_, i) => (active.has(i) ? activeW : COMP_W));
  }

  useEffect(() => {
    function updateWidths() {
      if (!gridRef.current) return;
      setColWidths(computeWidths(round, gridRef.current.offsetWidth));
    }
    updateWidths();
    window.addEventListener("resize", updateWidths);
    return () => window.removeEventListener("resize", updateWidths);
  }, [round]);

  function handleRoundChange(r) {
    setRound(r);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setRenderRound(r), 220);
  }

  function handlePick(id, pickData) {
    setPicks((prev) => ({ ...prev, [id]: pickData }));
  }

  const activeSet = new Set(ACTIVE_COLS[renderRound]);

  return (
    <div className="app">
      <div className="topbar">
        <span className="site-title">NBA Pick'em</span>
        <span className="user-tag">Logged in as Allan</span>
      </div>

      <div className="tabs">
        {ROUNDS.map((r, i) => (
          <button
            key={i}
            className={`tab ${round === i ? "active" : ""}`}
            onClick={() => handleRoundChange(i)}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="conf-labels">
        <span className="conf-west">Western Conference</span>
        <span className="conf-east">Eastern Conference</span>
      </div>

      <div className="grid" ref={gridRef}>
        {COLS.map(([matchups, conf, label], i) => (
          <div key={i} className="col" style={{ width: colWidths[i] || COMP_W }}>
            {activeSet.has(i) ? (
              <div className="col-active">
                {matchups.map((m) => (
                  <MatchupCard
                    key={m.id}
                    matchup={m}
                    conf={conf}
                    picks={picks}
                    onPick={handlePick}
                  />
                ))}
              </div>
            ) : (
              <CompressedCol matchups={matchups} conf={conf} label={label} picks={picks} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}