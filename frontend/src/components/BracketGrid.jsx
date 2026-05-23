import { useState, useEffect, useRef } from "react";
import CompressedCol from "./CompressedCol";
import { COMP_W, N_COLS, ACTIVE_COLS, computeWidths } from "../utils/helpers";

export default function BracketGrid({ round, cols, renderActive, picks = {} }) {
  const [renderRound, setRenderRound] = useState(round);
  const gridRef = useRef(null);
  const timerRef = useRef(null);
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setRenderRound(round), 220);
  }, [round]);

  useEffect(() => {
    function update() {
      setIsMobile(window.innerWidth < 768);
      if (gridRef.current) setColWidths(computeWidths(round, gridRef.current.offsetWidth));
    }
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [round]);

  const activeSet = new Set(ACTIVE_COLS[renderRound]);

  if (isMobile) {
    return (
      <div className="mobile-cards">
        {cols
          .filter((_, i) => activeSet.has(i))
          .flatMap(([colMatchups, conf]) => colMatchups.map(m => renderActive(m, conf)))}
      </div>
    );
  }

  return (
    <div className="grid" ref={gridRef}>
      {cols.map(([colMatchups, conf, label], i) => (
        <div key={i} className="col" style={{ width: colWidths[i] || COMP_W }}>
          {activeSet.has(i)
            ? <div className="col-active">{colMatchups.map(m => renderActive(m, conf))}</div>
            : <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={picks} />}
        </div>
      ))}
    </div>
  );
}
