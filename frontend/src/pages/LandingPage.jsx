import { useNavigate } from "react-router-dom";
import MainNav from "../components/shared/MainNav";
import "../landing.css";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <>
    <MainNav showHome={false} />
    <div className="landing">
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
    </>
  );
}
