import { useNavigate } from "react-router-dom";
import "../landing.css";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <div className="landing-buttons">
        <button className="landing-btn" onClick={() => navigate("/pickem")}>
          Pickem
        </button>
        <button className="landing-btn" onClick={() => navigate("/fantasy")}>
          Fantasy
        </button>
        <button className="landing-btn landing-btn-disabled" disabled title="Not built yet">
          User
        </button>
      </div>
    </div>
  );
}
