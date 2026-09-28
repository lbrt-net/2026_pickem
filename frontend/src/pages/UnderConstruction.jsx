import { Link } from "react-router-dom";

export default function UnderConstruction({ label }) {
  return (
    <div className="site-ui" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, background: "var(--bg)" }}>
      <div style={{ fontSize: 16 }}>{label} — under construction</div>
      <Link to="/" style={{ fontSize: 12, color: "var(--text)" }}>&larr; lbrt.net</Link>
    </div>
  );
}
