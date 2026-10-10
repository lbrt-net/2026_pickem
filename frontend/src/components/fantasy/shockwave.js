// The LaMelo slam's effects. Built to be cheap at the moment it happens (the YouTube player is starting then too):
// the rings are made ahead of time (warmRings, while he's on the block) as their own graphics layers at full size,
// so the slam itself only scales and fades them — nothing is redrawn. Skipped for reduced motion.
const reduced = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const pool = [];

function makeRing() {
  const ring = document.createElement("div");
  ring.className = "sw-ring";
  ring.addEventListener("animationend", () => { ring.classList.remove("sw-go"); pool.push(ring); });
  document.body.appendChild(ring);
  return ring;
}

// Six rings (three per slam spot), parked invisible on the page until the slam.
export function warmRings() {
  if (reduced()) return;
  while (pool.length < 6) pool.push(makeRing());
}

// Three rings in a team's colors (primary, secondary, primary) ripple out from an element's center, ~640px over 1s.
export function shockwave(el, colors) {
  if (!el || reduced()) return;
  const cs = (colors || []).filter(Boolean);
  const r = el.getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  [0, 160, 320].forEach((delay, i) => {
    const ring = pool.pop() || makeRing();
    ring.style.left = `${cx}px`;
    ring.style.top = `${cy}px`;
    ring.style.setProperty("--sw", cs.length ? cs[i % cs.length] : "var(--accent)");
    ring.style.borderWidth = `${7 - 2 * i}px`; // each echo a little thinner
    ring.style.animationDelay = `${delay}ms`;
    ring.classList.add("sw-go");
  });
}

// A short shake of the draft room's content as the slam lands (not the whole app, so the corner card and the
// rings stay put and the browser only moves one layer).
export function shake() {
  const box = document.querySelector(".dr");
  if (!box || reduced()) return;
  box.classList.remove("sw-shake");
  void box.offsetWidth; // restart if it's already running
  box.classList.add("sw-shake");
  setTimeout(() => box.classList.remove("sw-shake"), 250);
}
