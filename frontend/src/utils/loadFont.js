// Load a Google Fonts stylesheet once, from the page that needs it — so every other page doesn't download faces it
// never uses (index.html loads only the site's own Barlow / Barlow Condensed).
const done = new Set();
export default function loadFont(families) {
  if (typeof document === "undefined" || done.has(families)) return;
  done.add(families);
  const l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = `https://fonts.googleapis.com/css2?${families}&display=swap`;
  document.head.appendChild(l);
}
