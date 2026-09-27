import { Link } from "react-router-dom";

export default function UnderConstruction({ label }) {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, fontFamily: "system-ui, sans-serif" }}>
      <div style={{ fontSize: 16 }}>{label} — under construction</div>
      <Link to="/" style={{ fontSize: 12, color: "#666" }}>&larr; lbrt.net</Link>
    </div>
  );
}
