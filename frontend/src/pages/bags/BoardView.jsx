import { IN, BOARD_FRONT, BOARD_BACK, BOARD_HALF_W, HOLE, HOLE_R } from "./boardGeometry";

// Top-down target board with a 1 ft grid, shared by the landing log (/bags, clickable) and the
// throw library popup (a tighter crop around one logged landing). Units: inches (boardGeometry.js).

export default function BoardView({ view, dots = [], svgRef = null, onClick = null, className = "bags-board", label }) {
  const W = view.right - view.left, Hh = view.far - view.near;
  const Y = d => view.far - d;
  const xs = [], ds = [];
  for (let f = Math.ceil(view.left / IN); f <= Math.floor(view.right / IN); f++) xs.push(f);
  for (let f = Math.ceil(view.near / IN) + 1; f <= Math.floor(view.far / IN); f++) ds.push(f);
  return (
    <svg ref={svgRef} className={className} viewBox={`${view.left} 0 ${W} ${Hh}`} onClick={onClick} role="img" aria-label={label}>
      {xs.map(f => (
        <g key={`x${f}`}>
          <line className={f === 0 ? "bags-grid bags-grid-mid" : "bags-grid"} x1={f * IN} x2={f * IN} y1={0} y2={Hh} />
          {f !== 0 && <text className="bags-tick" x={f * IN} y={Hh - 2} textAnchor="middle">{Math.abs(f)} {f < 0 ? "L" : "R"}</text>}
        </g>
      ))}
      {ds.map(f => (
        <g key={f}>
          <line className={f === 27 || f === 31 ? "bags-grid bags-grid-mid" : "bags-grid"} x1={view.left} x2={view.right} y1={Y(f * IN)} y2={Y(f * IN)} />
          <text className="bags-tick" x={view.left + 2} y={Y(f * IN) - 1.5}>{f} ft</text>
        </g>
      ))}
      <rect className="bags-target" x={-BOARD_HALF_W} y={Y(BOARD_BACK)} width={BOARD_HALF_W * 2} height={BOARD_BACK - BOARD_FRONT} />
      <circle className="bags-hole" cx={HOLE.x} cy={Y(HOLE.d)} r={HOLE_R} />
      {dots.map(t => (
        <g key={t.key} className={t.last ? "bags-dot bags-dot-last" : "bags-dot"}>
          <rect className={`bags-dot-${t.color}`} x={t.x - 4} y={Y(t.d) - 4} width="8" height="8" rx="1" />
          <text x={t.x} y={Y(t.d) - 6}>{t.label}</text>
        </g>
      ))}
    </svg>
  );
}
