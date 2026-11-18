import { useNavigate } from "react-router-dom";
import MainNav from "../components/shared/MainNav";
import "../landing.css";

// `logo` is set only by the admin logo-test pages (/admin/logos/1, /2): top-bar lockup + big logo above the buttons.
// The real home page passes nothing and stays the plain "LBRT" text.
export default function LandingPage({ logo }) {
  const navigate = useNavigate();

  return (
    <>
    <MainNav brand={logo && <img className="main-nav-logo" src={logo.bar} alt="LBRT" />} />
    <div className={logo ? "landing landing-has-logo" : "landing"}>
      {logo && <img className="landing-logo" src={logo.full} alt="LBRT" />}
      <div className="landing-buttons">
        <button className="landing-btn" onClick={() => navigate("/pickem")}>
          Pickem
        </button>
        <button className="landing-btn" onClick={() => navigate("/fantasy")}>
          Fantasy
        </button>
        <button className="landing-btn" onClick={() => navigate("/stats/nba")}>
          Stats
        </button>
        <button className="landing-btn" onClick={() => navigate("/account")}>
          User
        </button>
      </div>
    </div>
    </>
  );
}
