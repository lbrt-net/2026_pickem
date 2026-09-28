import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import MainNav from "../components/shared/MainNav";
import useCurrentUser from "../hooks/useCurrentUser";
import sitemap from "../generated/sitemap.json";

// Admin-only map of every page, the links between them, and the data each reads.
// sitemap.json is regenerated from the code on every dev/build (scripts/gen-sitemap.mjs).

const AREAS = [
  ["site", "lbrt.net", p => !p.startsWith("/pickem") && !p.startsWith("/fantasy")],
  ["pickem", "Pickem 2026", p => p.startsWith("/pickem/2026") || p === "/pickem"],
  ["fantasy", "Fantasy 2026-27", p => p.startsWith("/fantasy/2026_27") || p === "/fantasy"],
  ["future", "Under construction", p => p.endsWith("/*")],
];
const areaOf = p => (AREAS.find(([id, , test]) => id === "future" && test(p)) || AREAS.find(([, , test]) => test(p)))[0];

// A page "has data" if it reads anything beyond who's logged in.
const hasData = page => page.api.some(a => a !== "/me");
const shortName = path => path.replace("/fantasy/2026_27", "") .replace("/pickem/2026", "") || "/";
const esc = s => s.replace(/"/g, "#quot;");

function buildChart({ showNav, showData, showNames }) {
  const ids = new Map(sitemap.pages.map((p, i) => [p.path, `n${i}`]));
  const lines = ["flowchart LR"];

  for (const [area, label] of AREAS) {
    const pages = sitemap.pages.filter(p => areaOf(p.path) === area);
    if (!pages.length) continue;
    lines.push(`  subgraph ${area}["${label}"]`);
    for (const p of pages) {
      const name = p.redirect ? "redirect" : p.label || p.component;
      lines.push(`    ${ids.get(p.path)}["<b>${esc(name)}</b><br/>${esc(shortName(p.path))}"]`);
    }
    lines.push("  end");
  }

  for (const e of sitemap.edges) {
    if (!ids.has(e.from) || !ids.has(e.to)) continue;
    if (e.kind === "name" && !showNames) continue;
    lines.push(e.kind === "redirect" ? `  ${ids.get(e.from)} -. redirect .-> ${ids.get(e.to)}` : `  ${ids.get(e.from)} --> ${ids.get(e.to)}`);
  }

  if (showNav) {
    Object.entries(sitemap.navs).forEach(([name, targets], i) => {
      lines.push(`  nav${i}(["${esc(name)}"])`);
      lines.push(`  class nav${i} nav`);
      targets.forEach(t => ids.has(t) && lines.push(`  nav${i} -.-> ${ids.get(t)}`));
    });
  }

  if (showData) {
    const endpoints = [...new Set(sitemap.pages.flatMap(p => p.api))].filter(a => a !== "/me").sort();
    const apiIds = new Map(endpoints.map((a, i) => [a, `api${i}`]));
    lines.push(`  subgraph data["Data (API)"]`);
    endpoints.forEach(a => lines.push(`    ${apiIds.get(a)}[("${esc(a)}")]`));
    lines.push("  end");
    sitemap.pages.forEach(p => p.api.forEach(a => apiIds.has(a) && lines.push(`  ${ids.get(p.path)} -.-o ${apiIds.get(a)}`)));
    lines.push(`  class ${[...apiIds.values()].join(",") || "none"} api`);
  }

  const mock = sitemap.pages.filter(p => !p.redirect && !hasData(p)).map(p => ids.get(p.path));
  if (mock.length) lines.push(`  class ${mock.join(",")} mock`);

  // Click a box to open that page (param routes have no single URL).
  sitemap.pages.filter(p => !p.path.includes(":") && !p.path.includes("*"))
    .forEach(p => lines.push(`  click ${ids.get(p.path)} "${p.path}"`));

  return lines.join("\n");
}

function Chart({ definition }) {
  const ref = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let current = true;
    (async () => {
      const { default: mermaid } = await import("mermaid");
      const css = getComputedStyle(document.documentElement);
      const v = name => css.getPropertyValue(name).trim();
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "loose",
        theme: "base",
        themeVariables: {
          darkMode: true,
          background: v("--bg"),
          primaryColor: v("--surface-2"),
          primaryTextColor: v("--text"),
          primaryBorderColor: v("--border"),
          lineColor: v("--text"),
          textColor: v("--text"),
          clusterBkg: v("--surface"),
          clusterBorder: v("--border"),
          edgeLabelBackground: v("--surface"),
          fontFamily: getComputedStyle(document.body).fontFamily,
          fontSize: "15px",
        },
        flowchart: { htmlLabels: true, curve: "basis" },
      });
      const full = `${definition}
  classDef mock stroke:${v("--accent-gold")},stroke-width:2px,stroke-dasharray:4 3
  classDef nav fill:${v("--surface")},stroke:${v("--accent-blue")}
  classDef api fill:${v("--surface")},stroke:${v("--accent-green")}`;
      try {
        const { svg, bindFunctions } = await mermaid.render(`sitemap-${Date.now()}`, full);
        if (!current || !ref.current) return;
        ref.current.innerHTML = svg;
        // Natural size + horizontal scroll, instead of shrinking to fit (unreadable).
        const el = ref.current.querySelector("svg");
        if (el) {
          el.setAttribute("width", el.viewBox.baseVal.width);
          el.style.maxWidth = "none";
          el.style.height = "auto";
        }
        bindFunctions?.(ref.current);
        setError(null);
      } catch (e) {
        if (current) setError(String(e?.message || e));
      }
    })();
    return () => { current = false; };
  }, [definition]);

  return (
    <>
      {error && <pre style={{ color: "var(--accent-red)", whiteSpace: "pre-wrap" }}>{error}</pre>}
      <div ref={ref} style={{ overflowX: "auto", border: "1px solid var(--border)", background: "var(--surface)", padding: 12, minHeight: 200 }} />
    </>
  );
}

const cell = { padding: "6px 8px", textAlign: "left", verticalAlign: "top" };
const heading = { fontSize: 16, margin: "24px 0 8px" };

export default function SiteMap() {
  const user = useCurrentUser();
  const [showNav, setShowNav] = useState(false);
  const [showData, setShowData] = useState(false);
  const [showNames, setShowNames] = useState(false);

  if (user === undefined || !user?.isAdmin) {
    return (
      <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)" }}>
        <MainNav />
        <p style={{ padding: 24, fontSize: 14 }}>{user === undefined ? "Checking…" : "Admins only."}</p>
      </div>
    );
  }

  const inbound = path => sitemap.edges.filter(e => e.to === path && e.kind !== "redirect").length;
  const pages = sitemap.pages.filter(p => !p.redirect);

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <MainNav />
      <div style={{ padding: "16px 16px 40px", maxWidth: 1400, margin: "0 auto", fontSize: 14 }}>
        <h1 style={{ fontSize: 22, marginBottom: 6 }}>Site Map</h1>
        <p style={{ marginBottom: 12 }}>
          Built from the code on every deploy. Solid arrows are in-page links. Gold dashed boxes read no data (static or mock).
          Click a box to open that page.
        </p>

        <div style={{ display: "flex", gap: 16, marginBottom: 12, flexWrap: "wrap" }}>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={showNav} onChange={e => setShowNav(e.target.checked)} /> Sidebar &amp; top bar links (blue)
          </label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={showNames} onChange={e => setShowNames(e.target.checked)} /> Team &amp; player name links
          </label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={showData} onChange={e => setShowData(e.target.checked)} /> Data each page reads (green)
          </label>
        </div>

        <Chart definition={buildChart({ showNav, showData, showNames })} />

        <h2 style={heading}>Broken links ({sitemap.dead.length})</h2>
        {sitemap.dead.length === 0
          ? <p>None — every link points at a real route.</p>
          : <ul>{sitemap.dead.map((d, i) => <li key={i}>{d.from} → {d.target}</li>)}</ul>}

        <h2 style={heading}>Pages</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                <th style={cell}>Page</th><th style={cell}>Data it reads</th><th style={cell}>Links to</th>
                <th style={cell} title="In-page links pointing here (not counting sidebar/top bar)">Linked from</th><th style={cell}>Nav</th>
              </tr>
            </thead>
            <tbody>
              {pages.map(p => (
                <tr key={p.path} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <td style={cell}>
                    <b>{p.label || p.component}</b><br />
                    {p.path.includes(":") || p.path.includes("*") ? p.path : <Link to={p.path}>{p.path}</Link>}
                  </td>
                  <td style={cell}>{hasData(p) ? p.api.filter(a => a !== "/me").map(a => <div key={a}>{a}</div>) : <span style={{ color: "var(--accent-gold)" }}>none</span>}</td>
                  <td style={cell}>{p.links.length ? p.links.map(l => <div key={l}>{l}</div>) : "—"}</td>
                  <td style={cell}>{inbound(p.path)}</td>
                  <td style={cell}>{p.navs.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
