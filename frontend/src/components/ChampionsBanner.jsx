import { useState, useEffect } from "react";
import { API } from "../utils/helpers";

export default function ChampionsBanner() {
  const [visible, setVisible] = useState(true);
  const [winner, setWinner] = useState(null);

  useEffect(() => {
    fetch(`${API}/scores`, { credentials: "include" })
      .then(r => r.json())
      .then(data => { if (data?.length) setWinner(data[0]); })
      .catch(() => {});
  }, []);

  if (!visible) return null;

  return (
    <div onClick={() => setVisible(false)} style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.82)",
      display: "flex", alignItems: "center", justifyContent: "center",
      cursor: "pointer",
    }}>
      <div style={{
        background: "linear-gradient(160deg, #1d2c5e 0%, #002f6c 50%, #1d2c5e 100%)",
        border: "3px solid #f58426",
        borderRadius: 16,
        padding: "40px 56px",
        textAlign: "center",
        boxShadow: "0 0 60px rgba(245,132,38,0.4), 0 8px 32px rgba(0,0,0,0.8)",
        maxWidth: 480,
        width: "90vw",
        userSelect: "none",
      }}>
        <img
          src="/trophy.png"
          alt="Larry O'Brien Trophy"
          style={{ width: 100, height: 100, objectFit: "contain", marginBottom: 8 }}
        />

        <img
          src="/nyk.png"
          alt="New York Knicks"
          style={{ width: 96, height: 96, objectFit: "contain", marginBottom: 16 }}
        />

        <div style={{
          color: "#f58426",
          fontWeight: 800,
          fontSize: 13,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          marginBottom: 6,
        }}>
          2026 NBA Champions
        </div>

        <div style={{
          color: "#ffffff",
          fontWeight: 800,
          fontSize: 28,
          lineHeight: 1.2,
          marginBottom: 28,
        }}>
          New York Knicks
        </div>

        {winner && (
          <div style={{
            borderTop: "1px solid rgba(245,132,38,0.3)",
            paddingTop: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
          }}>
            {winner.avatar_url && (
              <img
                src={winner.avatar_url}
                alt={winner.username}
                style={{ width: 44, height: 44, borderRadius: "50%", border: "2px solid #f58426" }}
              />
            )}
            <div style={{ textAlign: "left" }}>
              <div style={{ color: "#f58426", fontWeight: 700, fontSize: 16 }}>{winner.username}</div>
              <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>Pick'em Champion · {winner.points} pts</div>
            </div>
          </div>
        )}

        <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11, marginTop: 20 }}>
          click anywhere to dismiss
        </div>
      </div>
    </div>
  );
}
