import { useEffect, useRef, useState } from "react";
import "./BagsLog.css";

// Hidden page (/bags, linked from nowhere): tap where each cornhole bag landed, between throws.
// Everything lives in this browser's localStorage; nothing is sent to the server.
// Distances are measured from the front edge of the thrower's own board, so the target board
// runs from 27 ft to 31 ft and the hole centre sits at 30.25 ft (9 in from the top edge).

const KEY = "lbrt.bags.v1";
const IN = 12;
const BOARD_FRONT = 27 * IN, BOARD_BACK = 31 * IN, BOARD_HALF_W = 12;
const HOLE = { x: 0, d: BOARD_BACK - 9 }, HOLE_R = 3;
// Visible area: 7 ft either side, 21 ft to 37 ft out, so far misses are still clickable.
const VIEW = { left: -7 * IN, right: 7 * IN, near: 21 * IN, far: 37 * IN };
const COLORS = { red: "Red", navy: "Navy" };

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY));
    if (s && Array.isArray(s.sessions)) return s;
  } catch { /* storage unavailable or corrupt */ }
  return { sessions: [] };
}

function save(state) {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* storage unavailable */ }
}

function today() {
  return new Date().toLocaleDateString("en-CA");  // YYYY-MM-DD, local time
}

function outcome(t) {
  if (t.d == null) return "not seen";
  if (Math.hypot(t.x - HOLE.x, t.d - HOLE.d) <= HOLE_R) return "hole";
  const onLength = t.d >= BOARD_FRONT && t.d <= BOARD_BACK;
  if (onLength && Math.abs(t.x) <= BOARD_HALF_W) return "board";
  if (t.d < BOARD_FRONT) return "short";
  if (t.d > BOARD_BACK) return "long";
  return t.x < 0 ? "wide left" : "wide right";
}

function ft(inches) {
  return `${(inches / IN).toFixed(1)} ft`;
}

function describe(t) {
  if (t.d == null) return "—";
  const parts = [];
  if (t.d < BOARD_FRONT) parts.push(`${ft(BOARD_FRONT - t.d)} short`);
  else if (t.d > BOARD_BACK) parts.push(`${ft(t.d - BOARD_BACK)} long`);
  else parts.push(`${ft(Math.hypot(t.x - HOLE.x, t.d - HOLE.d))} from hole`);
  if (Math.abs(t.x) >= 1) parts.push(`${ft(Math.abs(t.x))} ${t.x < 0 ? "left" : "right"}`);
  return parts.join(" · ");
}

function toCsv(sessions) {
  const rows = [["date", "throw", "time", "bag", "result", "distance_ft", "lateral_ft", "note"]];
  for (const s of sessions) {
    for (const t of s.throws) {
      rows.push([s.date, t.n, t.time, t.color, outcome(t),
        t.d == null ? "" : (t.d / IN).toFixed(2), t.x == null ? "" : (t.x / IN).toFixed(2), t.note || ""]);
    }
  }
  return rows.map(r => r.join(",")).join("\n");
}

export default function BagsLog() {
  const [state, setState] = useState(load);
  const [color, setColor] = useState("red");
  const [flash, setFlash] = useState("");
  const [confirmNew, setConfirmNew] = useState(false);
  const svgRef = useRef(null);

  useEffect(() => {
    document.title = "Bags Log · LBRT";
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => meta.remove();
  }, []);

  useEffect(() => save(state), [state]);

  const session = state.sessions.find(s => s.date === today() && !s.closed) || null;
  const throws = session ? session.throws : [];
  const nextN = throws.length + 1;

  function update(fn) {
    setState(prev => {
      const sessions = prev.sessions.map(s => ({ ...s, throws: [...s.throws] }));
      let cur = sessions.find(s => s.date === today() && !s.closed);
      if (!cur) {
        cur = { id: Date.now(), date: today(), throws: [] };
        sessions.push(cur);
      }
      fn(cur, sessions);
      return { sessions };
    });
  }

  function log(spot) {
    const t = { n: nextN, time: new Date().toLocaleTimeString("en-GB"), color, ...spot };
    update(cur => cur.throws.push(t));
    setColor(c => (c === "red" ? "navy" : "red"));
    setFlash(`Throw ${t.n} (${COLORS[t.color]}): ${outcome(t)}${t.d != null && outcome(t) !== "hole" ? `, ${describe(t)}` : ""}`);
  }

  function undo() {
    if (!throws.length) return;
    const last = throws[throws.length - 1];
    update(cur => cur.throws.pop());
    setColor(last.color);
    setFlash(`Removed throw ${last.n}`);
  }

  function onBoardClick(e) {
    const svg = svgRef.current;
    const p = svg.createSVGPoint();
    p.x = e.clientX;
    p.y = e.clientY;
    const { x, y } = p.matrixTransform(svg.getScreenCTM().inverse());
    log({ x: Math.round(x), d: Math.round(VIEW.far - y) });
  }

  useEffect(() => {
    function onKey(e) {
      if (e.target.tagName === "INPUT" || e.metaKey || e.ctrlKey) return;
      const k = e.key.toLowerCase();
      if (k === "h") log({ x: HOLE.x, d: HOLE.d });
      else if (k === "n") log({ x: null, d: null });
      else if (k === "u" || k === "backspace") undo();
      else if (k === "c") setColor(c => (c === "red" ? "navy" : "red"));
      else return;
      e.preventDefault();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  function copyCsv() {
    const csv = toCsv(state.sessions);
    navigator.clipboard.writeText(csv).then(() => setFlash("CSV copied"), () => setFlash("Couldn't copy; use Download"));
  }

  function downloadCsv() {
    const blob = new Blob([toCsv(state.sessions)], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bags-${today()}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function startNew() {
    setState(prev => ({ sessions: prev.sessions.map(s => (s === session ? { ...s, closed: true } : s)) }));
    setConfirmNew(false);
    setColor("red");
    setFlash("New session started");
  }

  const counts = {};
  for (const t of throws) counts[outcome(t)] = (counts[outcome(t)] || 0) + 1;

  const W = VIEW.right - VIEW.left, Hh = VIEW.far - VIEW.near;
  const Y = d => VIEW.far - d;
  const past = state.sessions.filter(s => s !== session && s.throws.length);

  return (
    <div className="bags site-ui">
      <header className="bags-head">
        <h1>Bags log</h1>
        <div className="bags-next">
          <span>Throw {nextN}</span>
          <button type="button" className={`bags-chip bags-chip-${color}`} onClick={() => setColor(c => (c === "red" ? "navy" : "red"))}
                  title="Switch bag colour (C)">
            {COLORS[color]} bag
          </button>
        </div>
      </header>

      <div className="bags-main">
        <div className="bags-board-wrap">
          <svg ref={svgRef} className="bags-board" viewBox={`${VIEW.left} 0 ${W} ${Hh}`} onClick={onBoardClick}
               role="img" aria-label="Target board seen from above. Click where the bag landed.">
            {Array.from({ length: 15 }, (_, i) => i - 7).map(f => (
              <g key={`x${f}`}>
                <line className={f === 0 ? "bags-grid bags-grid-mid" : "bags-grid"} x1={f * IN} x2={f * IN} y1={0} y2={Hh} />
                {f !== 0 && <text className="bags-tick" x={f * IN} y={Hh - 2} textAnchor="middle">{Math.abs(f)} {f < 0 ? "L" : "R"}</text>}
              </g>
            ))}
            {Array.from({ length: 15 }, (_, i) => 22 + i).map(f => (
              <g key={f}>
                <line className={f === 27 || f === 31 ? "bags-grid bags-grid-mid" : "bags-grid"} x1={VIEW.left} x2={VIEW.right} y1={Y(f * IN)} y2={Y(f * IN)} />
                <text className="bags-tick" x={VIEW.left + 2} y={Y(f * IN) - 1.5}>{f} ft</text>
              </g>
            ))}
            <rect className="bags-target" x={-BOARD_HALF_W} y={Y(BOARD_BACK)} width={BOARD_HALF_W * 2} height={BOARD_BACK - BOARD_FRONT} />
            <circle className="bags-hole" cx={HOLE.x} cy={Y(HOLE.d)} r={HOLE_R} />
            {throws.filter(t => t.d != null).map((t, i, arr) => (
              <g key={t.n} className={i === arr.length - 1 ? "bags-dot bags-dot-last" : "bags-dot"}>
                <rect className={`bags-dot-${t.color}`} x={t.x - 4} y={Y(t.d) - 4} width="8" height="8" rx="1" />
                <text x={t.x} y={Y(t.d) - 6}>{t.n}</text>
              </g>
            ))}
          </svg>
          <p className="bags-hint">Click where the bag landed. You throw from the bottom. Keys: H hole · N didn't see · U undo · C colour</p>
        </div>

        <aside className="bags-side">
          <div className="bags-actions">
            <button type="button" onClick={() => log({ x: HOLE.x, d: HOLE.d })}>In the hole</button>
            <button type="button" onClick={() => log({ x: null, d: null })}>Didn't see</button>
            <button type="button" onClick={undo} disabled={!throws.length}>Undo</button>
          </div>
          <p className="bags-flash" aria-live="polite">{flash}</p>

          <div className="bags-counts">
            {["hole", "board", "short", "long", "wide left", "wide right", "not seen"].filter(k => counts[k]).map(k => (
              <span key={k}><b>{counts[k]}</b> {k}</span>
            ))}
          </div>

          <div className="bags-table-wrap">
            <table className="bags-table">
              <thead><tr><th>#</th><th>Time</th><th>Bag</th><th>Result</th><th>Spot</th></tr></thead>
              <tbody>
                {[...throws].reverse().map(t => (
                  <tr key={t.n}>
                    <td>{t.n}</td><td>{t.time}</td>
                    <td><span className={`bags-swatch bags-dot-${t.color}`} />{COLORS[t.color]}</td>
                    <td>{outcome(t)}</td><td>{describe(t)}</td>
                  </tr>
                ))}
                {!throws.length && <tr><td colSpan={5}>No throws yet today. Click the board after each throw.</td></tr>}
              </tbody>
            </table>
          </div>

          <div className="bags-export">
            <button type="button" onClick={copyCsv}>Copy CSV</button>
            <button type="button" onClick={downloadCsv}>Download CSV</button>
            {!confirmNew
              ? <button type="button" onClick={() => setConfirmNew(true)} disabled={!throws.length}>New session</button>
              : <span className="bags-confirm">Start over at throw 1? Today's throws stay saved.
                  <button type="button" onClick={startNew}>Yes</button>
                  <button type="button" onClick={() => setConfirmNew(false)}>No</button></span>}
          </div>
          {past.length > 0 && <p className="bags-past">{past.length} earlier session{past.length > 1 ? "s" : ""} saved ({past.reduce((a, s) => a + s.throws.length, 0)} throws), included in the CSV.</p>}
        </aside>
      </div>
    </div>
  );
}
