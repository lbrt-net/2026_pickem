import FantasySidebar from "./FantasySidebar";

// Skeleton-only shell: real navigation, no visual design pass yet.
// Every fantasy page renders through this — don't add per-page chrome.
export default function FantasyShell({ title, season, children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif", color: "#111" }}>
      <FantasySidebar season={season} />
      <div style={{ flexGrow: 1, padding: 24, maxWidth: 1100 }}>
        <div style={{ fontSize: 11, color: "#b45309", border: "1px solid #b45309", display: "inline-block", padding: "2px 8px", marginBottom: 12 }}>
          SKELETON — layout only, design not final
        </div>
        <h1 style={{ fontSize: 20, marginBottom: 16 }}>{title}</h1>
        {children}
      </div>
    </div>
  );
}
