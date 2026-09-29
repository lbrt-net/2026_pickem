// Builds src/generated/sitemap.json from the code: every route in App.jsx, the
// links between pages, and the API endpoints each page reads. Runs before
// `npm run dev` / `npm run build`, so the admin Site Map page can't drift from
// the code. Regex-based on purpose: good enough for this codebase's link styles
// (<Link to>, navigate(), sidebar path arrays, TeamLink/EntityLink helpers).
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "src");
const OUT = join(SRC, "generated", "sitemap.json");

// Site-wide chrome: shown as their own nodes instead of an edge from every page.
const NAV = {
  "components/shared/MainNav.jsx": "Top bar",
  "components/UserChip.jsx": "Top bar",
  "components/fantasy/FantasySidebar.jsx": "Fantasy sidebar",
  "components/fantasy/nav.js": "Fantasy sidebar", // sidebar/tab config: paths relative to /fantasy/2026_27
  "components/Sidebar.jsx": "Pickem sidebar",
};
const NAV_CONTAINERS = new Set(["components/fantasy/FantasyShell.jsx", "components/AppTopBar.jsx"]);
// Link/fetch helpers: never scanned directly — their use is detected via HELPERS / useFantasyApi.
const HELPER_FILES = new Set(["components/fantasy/data.js", "components/fantasy/links.jsx", "components/fantasy/features.js"]);
// The site map page itself is full of path strings that aren't links.
const SKIP_FILES = new Set(["pages/SiteMap.jsx"]);

// Template-literal variables with a known value.
const VARS = { BASE: "/fantasy/2026_27", base: "/fantasy/2026_27", season: "2026_27", SEASON: "2026_27", year: "2026" };
const HELPERS = [
  [/\bteamPath\(|<TeamLink\b/, "/fantasy/2026_27/team/:p"],
  [/\bentityPath\(|<EntityLink\b/, "/fantasy/2026_27/players/:p"],
];

const HELPER_TARGETS = new Set(HELPERS.map(([, t]) => t));

const read = rel => readFileSync(join(SRC, rel), "utf8");
const rel = abs => relative(SRC, abs).split("\\").join("/");

function resolveImport(fromRel, spec) {
  if (!spec.startsWith(".")) return null;
  const base = join(SRC, dirname(fromRel), spec);
  for (const cand of [base, `${base}.jsx`, `${base}.js`, join(base, "index.jsx")]) {
    if (existsSync(cand) && !cand.endsWith("/")) {
      try { readFileSync(cand); return rel(cand); } catch { /* directory */ }
    }
  }
  return null;
}

const localImports = fileRel =>
  [...read(fileRel).matchAll(/import\s+[^'"]*?from\s+["']([^"']+)["']/g)]
    .map(m => resolveImport(fileRel, m[1]))
    .filter(f => f && /\.jsx?$/.test(f));

// Substitute known ${VARS}; unknown ${x} after "/" becomes a :param, otherwise dropped.
function normalize(lit) {
  let s = lit.replace(/\$\{(\w+)\}/g, (m, v) => (v in VARS ? VARS[v] : m));
  s = s.replace(/\/\$\{[^}]*\}/g, "/:p").replace(/\$\{[^}]*\}/g, "");
  return s.split(/[?#]/)[0].replace(/\/$/, "") || "/";
}

function scanFile(fileRel) {
  const src = read(fileRel);
  const links = new Set(), api = new Set();
  for (const m of src.matchAll(/(["'`])((?:\$\{API\}|\$\{BASE\}|\$\{base\}|\/)[^"'`\s]*)\1/g)) {
    const raw = m[2];
    if (/(startsWith|isOn|gate)\(\s*$/.test(src.slice(Math.max(0, m.index - 20), m.index))) continue; // active-link / feature checks, not links
    if (raw.startsWith("${API}")) {
      const path = normalize(raw.slice(6));
      if (!path.startsWith("/auth")) api.add(path);
      continue;
    }
    const path = normalize(raw);
    if (/^\/[\w\-/:]*$/.test(path)) links.add(path); // no "." = skips static assets like /trophy.png
  }
  for (const m of src.matchAll(/useFantasyApi\(\s*["']([^"']+)["']/g)) api.add(`/fantasy/2026_27/${m[1]}`);
  for (const [re, target] of HELPERS) if (re.test(src)) links.add(target);
  if (/\$\{API\}\/auth\/discord/.test(src)) links.add("(Discord login)");
  return { links, api };
}

// ---- routes from App.jsx ----
const app = read("App.jsx");
const components = {};
for (const m of app.matchAll(/import\s+(\w+)\s+from\s+["'](\.[^"']+)["']/g)) components[m[1]] = resolveImport("App.jsx", m[2]);

const routes = [];
// element={<Comp />} or, for pages switched off in features.js, element={gate("/x", <Comp />)}
const featuresSrc = read("components/fantasy/features.js");
const offPaths = new Set([...featuresSrc.matchAll(/"([^"]+)":\s*false/g)].map(m => m[1]));
for (const m of app.matchAll(/<Route\s+path="([^"]+)"\s+element=\{(?:gate\("([^"]+)",\s*)?<(\w+)([^>]*)\/?>\s*\)?\s*\}/g)) {
  const [, path, gatePath, comp, props] = m;
  const r = { path, component: comp, file: components[comp] || null };
  if (gatePath && offPaths.has(gatePath)) r.label = `${comp} (off this round)`;
  if (comp === "Navigate") r.redirect = /to="([^"]+)"/.exec(props)?.[1];
  const label = /label="([^"]+)"/.exec(props)?.[1];
  if (label) r.label = label;
  routes.push(r);
}

function matchRoute(target) {
  const t = target.split("/").filter(Boolean);
  let best = null, bestScore = -1;
  for (const r of routes) {
    const p = r.path.split("/").filter(Boolean);
    const splat = p[p.length - 1] === "*";
    const segs = splat ? p.slice(0, -1) : p;
    if (splat ? t.length < segs.length : t.length !== segs.length) continue;
    let score = 0, ok = true;
    segs.forEach((s, i) => {
      if (s === t[i]) score += 2;
      else if (s.startsWith(":") && t[i].startsWith(":")) score += 3; // param link -> param route beats a static sibling
      else if (s.startsWith(":") || t[i].startsWith(":")) score += 1;
      else ok = false;
    });
    if (ok && score > bestScore) { best = r; bestScore = score; }
  }
  return best;
}

// ---- walk each page (plus the non-nav components it imports) ----
function collect(fileRel, seen = new Set(), navs = new Set()) {
  const links = new Set(), api = new Set();
  const walk = f => {
    if (seen.has(f)) return;
    seen.add(f);
    if (NAV[f]) { navs.add(NAV[f]); return; }
    if (HELPER_FILES.has(f) || SKIP_FILES.has(f)) return;
    if (NAV_CONTAINERS.has(f)) { localImports(f).forEach(walk); return; }
    const s = scanFile(f);
    s.links.forEach(l => links.add(l));
    s.api.forEach(a => api.add(a));
    localImports(f).forEach(walk);
  };
  walk(fileRel);
  return { links, api, navs };
}

const dead = [];
const edges = [];
const pages = routes.map(r => {
  if (r.redirect) {
    edges.push({ from: r.path, to: r.redirect, kind: "redirect" });
    return { ...r, api: [], navs: [], links: [] };
  }
  if (!r.file) return { ...r, api: [], navs: [], links: [] };
  const { links, api, navs } = collect(r.file);
  const out = [];
  for (const l of links) {
    if (l === "(Discord login)") { out.push(l); continue; }
    const hit = matchRoute(l);
    if (!hit) dead.push({ from: r.path, target: l });
    else if (hit.path !== r.path) {
      out.push(hit.path);
      edges.push({ from: r.path, to: hit.path, kind: HELPER_TARGETS.has(l) ? "name" : "link" });
    }
  }
  return { ...r, api: [...api].sort(), navs: [...navs].sort(), links: [...new Set(out)].sort() };
});

// ---- nav components: their own link lists ----
const navNodes = {};
for (const [file, name] of Object.entries(NAV)) {
  const s = scanFile(file);
  navNodes[name] ??= new Set();
  for (const l of s.links) {
    let hit = matchRoute(l);
    // Sidebar arrays hold paths relative to the product root.
    if (!hit && file.includes("fantasy")) hit = matchRoute(`/fantasy/2026_27${l === "/" ? "" : l}`);
    if (hit) navNodes[name].add(hit.path);
    else if (l !== "(Discord login)") dead.push({ from: name, target: l });
  }
}

const seenEdges = new Set();
const uniqueEdges = edges.filter(e => {
  const k = `${e.from}>${e.to}>${e.kind}`;
  return seenEdges.has(k) ? false : seenEdges.add(k);
});

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({
  pages,
  edges: uniqueEdges,
  navs: Object.fromEntries(Object.entries(navNodes).map(([k, v]) => [k, [...v].sort()])),
  dead,
}, null, 2) + "\n");
console.log(`sitemap: ${pages.length} routes, ${uniqueEdges.length} links, ${dead.length} dead`);
