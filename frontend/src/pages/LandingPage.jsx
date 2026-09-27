import { useNavigate } from "react-router-dom";
import MainNav from "../components/shared/MainNav";
import "../landing.css";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, display: "flex", justifyContent: "flex-end", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
        <MainNav showHome={false} />
      </div>
      <div className="landing-buttons">
        <button className="landing-btn" onClick={() => navigate("/pickem")}>
          Pickem
        </button>
        <button className="landing-btn" onClick={() => navigate("/fantasy")}>
          Fantasy
        </button>
        <button className="landing-btn" onClick={() => navigate("/account")}>
          User
        </button>
      </div>
    </div>
  );
}
