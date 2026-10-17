import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./BagsLog.css";
import "./BagsLibrary.css";

// Hidden page (/bags/library): one tile per filmed throw, grouped into batches, with trends across
// throws. Data is /bags/throws.json, written by bags-form/build_report.py --site. Clicking a tile
// opens its charts: the flight to scale, the swing, hand speed and bag tilt.

const BOARD = { front: 27, back: 31, frontH: 3, backH: 12, hole: 30.25 };
const fmt = (v, d = 1) => (v == null ? "–" : Number(v).toFixed(d));
// The four outcomes build_report.py assigns, in the order they're shown.
const STATUS = {
  "good": "Good",
  "off gravity": "Off gravity",
  "no bag": "No bag found",
  "no pose": "No pose",
};
const statusClass = s => `lib-s-${s.replace(" ", "-")}`;

function stats(vals) {
  const v = vals.filter(x => x != null);
  if (!v.length) return null;
  const mean = v.reduce((a, b) => a + b, 0) / v.length;
  const sd = v.length > 1 ? Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / (v.length - 1)) : 0;
  return { mean, sd, n: v.length };
}

function Chart({ series, x, y, xLabel, yLabel, marks = [], height = 170, dots = false, extra = null, aspect = null, xTicks = null, yTicks = null }) {
  const W = 420, H = aspect ? Math.round(W * aspect) : height, L = 38, R = 8, T = 12, B = 26;
  const X = v => L + (v - x[0]) / (x[1] - x[0]) * (W - L - R);
  const Y = v => T + (1 - (v - y[0]) / (y[1] - y[0])) * (H - T - B);
  const ticks = (d, n) => Array.from({ length: n + 1 }, (_, i) => d[0] + (d[1] - d[0]) * i / n);
  return (
    <svg className="lib-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yLabel} by ${xLabel}`}>
      {(yTicks || ticks(y, 4)).map(v => (
        <g key={`y${v}`}>
          <line className="lib-grid" x1={L} x2={W - R} y1={Y(v)} y2={Y(v)} />
          <text className="lib-tick" x={L - 4} y={Y(v) + 3} textAnchor="end">{Math.round(v)}</text>
        </g>
      ))}
      {(xTicks || ticks(x, 6)).map(v => (
        <text key={`x${v}`} className="lib-tick" x={X(v)} y={H - 10} textAnchor="middle">{+v.toFixed(2)}</text>
      ))}
      <text className="lib-axis" x={W - R} y={H - 1} textAnchor="end">{xLabel}</text>
      <text className="lib-axis" x={L} y={T - 2}>{yLabel}</text>
      {extra && extra(X, Y)}
      {marks.map(([v, label]) => (
        <g key={label}>
          <line className="lib-mark" x1={X(v)} x2={X(v)} y1={T} y2={H - B} />
          <text className="lib-axis" x={X(v) + 3} y={T + 9}>{label}</text>
        </g>
      ))}
      {series.map((s, i) => s.pts.length > 0 && (dots || s.dots
        ? s.pts.map(([a, b], k) => <circle key={`${i}-${k}`} className={s.cls} cx={X(a)} cy={Y(b)} r="2.6" />)
        : <polyline key={i} className={s.cls} points={s.pts.map(([a, b]) => `${X(a)},${Y(b)}`).join(" ")} />))}
    </svg>
  );
}

function FlightChart({ t }) {
  const path = (t.path || []).map(([ft, inch]) => [ft, inch]);
  const bag = (t.series?.bag || []).map(([, ft, inch]) => [ft, inch]);
  const maxFt = Math.max(36, ...path.map(p => p[0] + 1), (t.landed_ft || 0) + 2);
  // Where it actually landed, from the landing log: on the board's slope or on the ground.
  const surface = ft => (ft >= BOARD.front && ft <= BOARD.back
    ? BOARD.frontH + (ft - BOARD.front) / (BOARD.back - BOARD.front) * (BOARD.backH - BOARD.frontH) : 0);
  const board = (X, Y) => (
    <g>
      <polygon className="lib-board" points={`${X(BOARD.front)},${Y(0)} ${X(BOARD.front)},${Y(BOARD.frontH)} ${X(BOARD.back)},${Y(BOARD.backH)} ${X(BOARD.back)},${Y(0)}`} />
      <line className="lib-hole" x1={X(BOARD.hole - 0.25)} x2={X(BOARD.hole + 0.25)} y1={Y(10.9)} y2={Y(10.9)} />
      {t.landed_ft != null ? (
        <g className="lib-landed">
          <path d={`M${X(t.landed_ft)},${Y(surface(t.landed_ft))} l-6,-12 h12 z`} />
          <text x={X(t.landed_ft)} y={Y(surface(t.landed_ft)) - 16} textAnchor="middle">landed {t.landed_ft.toFixed(1)} ft</text>
        </g>
      ) : t.reported ? (
        <text className="lib-landed-text" x={X(BOARD.front)} y={Y(BOARD.backH) - 26}>you: {t.reported} (no logged spot)</text>
      ) : null}
    </g>
  );
  const xt = Array.from({ length: Math.floor(maxFt / 6) + 1 }, (_, i) => i * 6);
  return <Chart series={[{ pts: path, cls: "lib-line-pred" }, { pts: bag, cls: "lib-dot-bag", dots: true }]}
                x={[-2, maxFt]} y={[0, 120]} xLabel="ft past front foot" yLabel="height, in" extra={board} aspect={0.3}
                xTicks={xt} yTicks={[0, 30, 60, 90, 120]} />;
}

function Detail({ t, onClose }) {
  useEffect(() => {
    const k = e => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  const swing = t.series?.swing || [];
  const tilt = t.series?.tilt || [];
  const est = t.release_traced ? " (estimate)" : "";
  const rows = [
    ["Status", `${STATUS[t.status]}: ${t.status_detail}`],
    ...(t.issues?.length ? [["Issues", t.issues.join("; ")]] : []),
    ["Bag speed", `${fmt(t.speed_mph)} mph`], ["Launch angle", `${fmt(t.angle_deg, 0)}°`],
    ["Release height", `${fmt(t.height_in, 0)} in${est}`], ["Peak height", `${fmt(t.apex_in, 0)} in`],
    ["Landing, no drag", `${fmt(t.landing_ft)} ft`], ["Spin", `${t.spin || "–"} (tilt change ${fmt(t.tilt_change_deg, 0)}°)`],
    ["Backswing", t.backswing_deg == null ? "before clip start" : `${fmt(t.backswing_deg, 0)}° behind vertical`],
    ["Forward swing", t.forward_swing_s == null ? "–" : `${fmt(t.forward_swing_s, 2)} s`],
    ["Hand speed at release", `${fmt(t.hand_mph)} mph${est}`],
    ["Arm alone would give", t.arm_only_mph == null ? "needs slow-mo swing" : `${fmt(t.arm_only_mph)} mph (gap ${fmt(t.flick_gap_mph)})`],
    ["Elbow, 0.1 s before → release", `${fmt(t.elbow_before_deg, 0)}° → ${fmt(t.elbow_release_deg, 0)}°`],
    ["Tracked by", t.tracked_by === "motion" ? "flight arc (colour-blind)" : `${t.tracked_by} colour`],
    ["Your result", t.reported || "not recorded"],
  ];
  return (
    <div className="lib-modal" role="dialog" aria-modal="true" aria-label={`Throw ${t.n}`} onClick={onClose}>
      <div className="lib-panel" onClick={e => e.stopPropagation()}>
        <div className="lib-panel-head">
          <h2>Throw {t.n} · {t.clip}</h2>
          <span>{t.recorded} · batch {t.batch}</span>
          <button type="button" onClick={onClose} aria-label="Close">Close</button>
        </div>
        {t.status === "no bag" || t.status === "no pose" ? <p>{STATUS[t.status]}: {t.status_detail}. No measurements for this throw.</p> : (
          <div className="lib-panel-grid">
            <section className="lib-flight"><h3>Flight, to scale</h3>
              <p className="lib-sub">Dots: tracked bag. Dashed: predicted arc, no air drag (real throws land shorter). Gold marker: where it actually landed (landing log). Board 27–31 ft.</p>
              <FlightChart t={t} /></section>
            <section className="lib-numbers">
              <table className="lib-table"><tbody>{rows.map(([k, v]) => <tr key={k}><td>{k}</td><td>{v}</td></tr>)}</tbody></table></section>
            <section><h3>Arm angle</h3><p className="lib-sub">0° straight down, + in front, 0 s = release</p>
              <Chart series={[{ pts: swing.map(s => [s[0], s[1]]), cls: "lib-line" }]} x={[-1, 0.3]} y={[-90, 120]}
                     xLabel="s" yLabel="degrees" marks={[[0, "release"]]} height={150} /></section>
            <section><h3>Hand speed</h3><p className="lib-sub">Wrist marker{est}</p>
              <Chart series={[{ pts: swing.map(s => [s[0], s[2]]), cls: "lib-line" }]} x={[-1, 0.3]} y={[0, 30]}
                     xLabel="s" yLabel="mph" marks={[[0, "release"]]} height={150} /></section>
            <section><h3>Bag tilt in flight</h3><p className="lib-sub">Flat = steady line; steady climb = end over end</p>
              <Chart series={[{ pts: tilt, cls: "lib-line" }]} x={[0, 0.4]} y={[-90, 90]} xLabel="s after release" yLabel="tilt °" height={150} /></section>
          </div>
        )}
      </div>
    </div>
  );
}

// Whole throw numbers on the x axis: every one when few, otherwise every 2nd/5th/10th.
function throwTicks(n) {
  const step = [1, 2, 5, 10, 20, 50].find(s => n / s <= 12) || 100;
  return Array.from({ length: Math.floor(n / step) }, (_, i) => (i + 1) * step).filter(v => v <= n);
}

function Trend({ throws, field, label, unit, y, yt }) {
  const pts = throws.filter(t => t[field] != null);
  const batches = [...new Set(throws.map(t => t.batch))];
  const starts = batches.map(b => throws.find(t => t.batch === b).n).slice(1);
  const ext = (X, Y) => (
    <g>
      {starts.map(n => <line key={n} className="lib-mark" x1={X(n - 0.5)} x2={X(n - 0.5)} y1={Y(y[1])} y2={Y(y[0])} />)}
      {pts.map(t => {
        const tip = <title>{`Throw ${t.n} (${t.clip}): ${fmt(t[field])} ${unit}${t.status === "good" ? "" : `, ${STATUS[t.status].toLowerCase()}`}`}</title>;
        const cx = X(t.n), cy = Y(Math.min(y[1], Math.max(y[0], t[field])));
        return t.status === "good"
          ? <circle key={t.n} className="lib-dot" cx={cx} cy={cy} r="4.2">{tip}</circle>
          : <g key={t.n} className="lib-x">{tip}<line x1={cx - 4} x2={cx + 4} y1={cy - 4} y2={cy + 4} /><line x1={cx - 4} x2={cx + 4} y1={cy + 4} y2={cy - 4} /></g>;
      })}
    </g>
  );
  return (
    <div className="lib-trend">
      <h3>{label}</h3>
      <Chart series={[]} x={[0.5, throws.length + 0.5]} y={y} xLabel="throw #" yLabel={unit} extra={ext} height={150}
             xTicks={throwTicks(throws.length)} yTicks={yt} />
    </div>
  );
}

export default function BagsLibrary() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    document.title = "Throw Library · LBRT";
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    fetch("/bags/throws.json", { cache: "no-store" })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch(e => setError(`Couldn't load the throw data (${e.message}). Run build_report.py --site and deploy.`));
    return () => meta.remove();
  }, []);

  if (error) return <div className="bags site-ui"><p>{error}</p></div>;
  if (!data) return <div className="bags site-ui"><p>Loading throws…</p></div>;

  const throws = data.throws;
  const batches = [...new Set(throws.map(t => t.batch))];
  const countBy = list => Object.keys(STATUS).map(s => [s, list.filter(t => t.status === s).length]).filter(([, c]) => c);

  return (
    <div className="bags site-ui">
      <header className="bags-head">
        <h1>Throw library</h1>
        <div className="lib-meta">
          {throws.length} throws · {batches.length} batches · updated {data.built}
          <span className="lib-counts">{countBy(throws).map(([s, c]) => <span key={s} className={`lib-pill ${statusClass(s)}`}>{c} {STATUS[s]}</span>)}</span>
          <Link to="/bags">Landing log →</Link>
        </div>
      </header>

      <section className="lib-trends">
        <Trend throws={throws} field="speed_mph" label="Bag speed" unit="mph" y={[10, 30]} yt={[10, 15, 20, 25, 30]} />
        <Trend throws={throws} field="angle_deg" label="Launch angle" unit="°" y={[20, 60]} yt={[20, 30, 40, 50, 60]} />
        <Trend throws={throws} field="height_in" label="Release height" unit="in" y={[0, 60]} yt={[0, 12, 24, 36, 48, 60]} />
      </section>
      <p className="lib-sub"><span className="lib-key-dot" /> good · <span className="lib-key-x">×</span> off gravity (measured, but don't trust the numbers) · vertical lines split batches.
        Good means the tracked bag falls at about 1 g on a clean arc; off gravity means it doesn't, or there were too few points to check.</p>

      {batches.map(b => {
        const bt = throws.filter(t => t.batch === b);
        const ok = bt.filter(t => t.status === "good");
        const sp = stats(ok.map(t => t.speed_mph)), an = stats(ok.map(t => t.angle_deg)), ht = stats(ok.map(t => t.height_in));
        return (
          <section key={b} className="lib-batch">
            <div className="lib-batch-head">
              <h2>Batch {b}</h2>
              <span>{bt[0].recorded.slice(0, 16)} – {bt[bt.length - 1].recorded.slice(11, 16)} · {bt.length} throws</span>
              <span className="lib-counts">{countBy(bt).map(([s, c]) => <span key={s} className={`lib-pill ${statusClass(s)}`}>{c} {STATUS[s]}</span>)}</span>
              {sp && <span>Good throws: bag speed {fmt(sp.mean)} ± {fmt(sp.sd)} mph · launch {fmt(an.mean, 0)} ± {fmt(an.sd, 0)}° · release height {fmt(ht.mean, 0)} ± {fmt(ht.sd, 0)} in</span>}
            </div>
            <div className="lib-grid">
              {bt.map(t => (
                <button type="button" key={t.clip} className={`lib-tile ${statusClass(t.status)}`} onClick={() => setOpen(t)}>
                  {t.thumb ? <img src={`/bags/${t.thumb}`} alt="" loading="lazy" /> : <div className="lib-nothumb">{STATUS[t.status]}</div>}
                  <div className="lib-tile-top"><b>#{t.n}</b><span>{t.recorded.slice(11, 19)}</span>
                    <span className={`lib-pill ${statusClass(t.status)}`}>{STATUS[t.status]}</span></div>
                  {t.speed_mph != null && (
                    <div className="lib-tile-stats">
                      <div><b>{fmt(t.speed_mph)}</b>bag mph</div>
                      <div><b>{fmt(t.angle_deg, 0)}°</b>launch</div>
                      <div><b>{fmt(t.height_in, 0)}</b>release ht, in{t.release_traced ? " (est.)" : ""}</div>
                      <div><b>{fmt(t.landing_ft)}</b>predicted ft</div>
                    </div>
                  )}
                  <div className="lib-tile-foot">
                    {t.status === "good" ? `${t.spin || "–"} · ` : `${t.status_detail} · `}
                    {t.reported ? `you: ${t.reported}` : "result not logged"}
                  </div>
                </button>
              ))}
            </div>
          </section>
        );
      })}
      <p className="lib-sub">Release ht (est.): the bag was first seen after it left your hand, so the release point was traced back along its arc.</p>
      {open && <Detail t={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
