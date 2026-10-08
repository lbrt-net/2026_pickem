import { useState } from "react";
import { pick } from "./glossary";
import "./GlossaryButton.css";

// A small "?" that opens the terms a table uses (keys from glossary.js). Click again, ✕ or Esc closes.
export default function GlossaryButton({ terms, align = "left" }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="gl" onKeyDown={e => { if (e.key === "Escape") setOpen(false); }}>
      <button type="button" className="gl-btn" aria-label="Glossary" aria-expanded={open} onClick={() => setOpen(o => !o)}>?</button>
      {open && (
        <span className={`gl-pop ${align}`} role="dialog" aria-label="Glossary">
          <span className="gl-h">Glossary<button type="button" className="gl-x" aria-label="Close" onClick={() => setOpen(false)}>✕</button></span>
          {pick(terms).map(([k, v]) => <span key={k} className="gl-r"><b>{k}</b><span>{v}</span></span>)}
        </span>
      )}
    </span>
  );
}
