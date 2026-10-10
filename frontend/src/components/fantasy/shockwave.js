// The LaMelo slam's shockwave: three rings in a team's colors (primary, secondary, primary) ripple out from an element's center over about a second,
// drawn on top of the whole page (not inside the element's box, so nothing clips them), then removed.
// Skipped for anyone whose device asks for reduced motion.
export function shockwave(el, colors) {
  const cs = (colors || []).filter(Boolean);
  if (!el || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  const r = el.getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  [0, 160, 320].forEach((delay, i) => {
    const ring = document.createElement("div");
    ring.className = "sw-ring";
    ring.style.left = `${cx}px`;
    ring.style.top = `${cy}px`;
    ring.style.setProperty("--sw", cs.length ? cs[i % cs.length] : "var(--accent)");
    ring.style.animationDelay = `${delay}ms`;
    ring.style.opacity = "0";
    if (i) ring.style.borderWidth = `${7 - 2 * i}px`; // each echo a little thinner
    document.body.appendChild(ring);
    setTimeout(() => ring.remove(), 1200 + delay);
  });
}
