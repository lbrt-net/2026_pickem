// Shared list controls for the Players page and the draft list (2026-10-15: one look, so they can't drift):
// tabs pick what you're looking at, recessed switches filter, numbered pages, and each row's NBA team color at its edge.
import "./ListControls.css";

export function Seg({ options, value, onChange, kind = "switch" }) {
  return (
    <span className={kind === "tabs" ? "lc-tabs" : "lc-sw"} role="radiogroup">
      {options.map(o => {
        const [key, text] = Array.isArray(o) ? o : [o, o];
        return <button key={key} type="button" role="radio" aria-checked={value === key} onClick={() => onChange(key)}>{text}</button>;
      })}
    </span>
  );
}

// first, last, and two either side of the current page; gaps as null
const pageList = (cur, n) => [...new Set([0, n - 1, ...[-2, -1, 0, 1, 2].map(d => cur + d)])].filter(p => p >= 0 && p < n).sort((a, b) => a - b)
  .flatMap((p, k, a) => (k && p - a[k - 1] > 1 ? [null, p] : [p]));

export function Pager({ page, total, size, onPage }) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav className="lc-foot" aria-label="Pages">
      <span>{page * size + 1}–{Math.min(total, (page + 1) * size)} of {total}</span>
      <span className="lc-pages">
        <button type="button" className="lc-pg" aria-label="Previous page" disabled={page === 0} onClick={() => onPage(page - 1)}>‹</button>
        {pageList(page, pages).map((p, k) => p == null ? <span key={`g${k}`} className="lc-gap">…</span>
          : <button key={p} type="button" className={`lc-pg${p === page ? " on" : ""}`} aria-current={p === page ? "page" : undefined} onClick={() => onPage(p)}>{p + 1}</button>)}
        <button type="button" className="lc-pg" aria-label="Next page" disabled={page >= pages - 1} onClick={() => onPage(page + 1)}>›</button>
      </span>
    </nav>
  );
}
