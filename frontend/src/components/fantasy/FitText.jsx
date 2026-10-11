import { useLayoutEffect, useRef, useState } from "react";

// Text that shrinks to fit its box before anything is cut: from `max` px down to `min` px; still too long at `min`
// (a troll name), it wraps onto a second line. Re-measures when the text or the box width changes.
export default function FitText({ text, max, min, className, style, title = text }) {
  const ref = useRef(null);
  const [fit, setFit] = useState({ size: max, wrap: false });
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const measure = () => {
      const prev = { ws: el.style.whiteSpace, d: el.style.display, lc: el.style.webkitLineClamp };
      el.style.whiteSpace = "nowrap";
      el.style.display = "block";
      el.style.webkitLineClamp = "unset";
      let size = max;
      el.style.fontSize = `${size}px`;
      while (size > min && el.scrollWidth > el.clientWidth + 0.5) {
        size -= 0.5;
        el.style.fontSize = `${size}px`;
      }
      const wrap = el.scrollWidth > el.clientWidth + 0.5;
      // put the box back the way this result renders it (React won't re-render if nothing changed)
      el.style.whiteSpace = wrap ? "normal" : "nowrap";
      el.style.display = wrap ? "-webkit-box" : "block";
      el.style.webkitLineClamp = wrap ? "2" : prev.lc && "";
      setFit(f => (f.size === size && f.wrap === wrap ? f : { size, wrap }));
    };
    measure();
    let live = true;
    document.fonts?.ready.then(() => { if (live) measure(); });  // the condensed display face loads late; measure again
    const ro = new ResizeObserver(measure);
    ro.observe(el.parentElement || el);
    return () => { live = false; ro.disconnect(); };
  }, [text, max, min]);
  return (
    <b ref={ref} title={title} className={className}
      style={{ ...style, display: "block", minWidth: 0, overflow: "hidden", fontSize: fit.size, lineHeight: fit.wrap ? 1.1 : undefined,
        whiteSpace: fit.wrap ? "normal" : "nowrap", ...(fit.wrap ? { display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" } : { textOverflow: "ellipsis" }) }}>
      {text}
    </b>
  );
}
