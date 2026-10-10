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

// A short screen shake as the slam lands (a few px, ~0.35 s). Shakes the app root, not <body>, so the rings
// (on <body>) stay put. Skipped for reduced motion.
export function shake() {
  const root = document.getElementById("root");
  if (!root || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  root.classList.remove("sw-shake");
  void root.offsetWidth; // restart the animation if it's already running
  root.classList.add("sw-shake");
  setTimeout(() => root.classList.remove("sw-shake"), 400);
}
