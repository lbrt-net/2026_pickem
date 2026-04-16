export default function Rules({ onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Scoring Rules</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="rules-body">
          <p className="rules-section-title">Points per series</p>
          <table className="rules-table">
            <tbody>
              <tr><td>Correct winner</td><td className="rules-pts">2 pts</td></tr>
              <tr><td>Correct games (exact)</td><td className="rules-pts">2 pts</td></tr>
              <tr><td>Correct games (1 off)</td><td className="rules-pts">1 pt</td></tr>
              <tr><td>Correct stat leader</td><td className="rules-pts">1 pt</td></tr>
              <tr className="rules-max"><td>Max per series</td><td className="rules-pts">5 pts</td></tr>
            </tbody>
          </table>
          <p className="rules-note">Games points apply regardless of whether your winner was correct.</p>
          <p className="rules-section-title" style={{ marginTop: 18 }}>Round multipliers</p>
          <table className="rules-table">
            <tbody>
              <tr><td>First round</td><td className="rules-pts">1×</td></tr>
              <tr><td>Conference semifinals</td><td className="rules-pts">2×</td></tr>
              <tr><td>Conference finals</td><td className="rules-pts">4×</td></tr>
              <tr><td>NBA Finals</td><td className="rules-pts">8×</td></tr>
            </tbody>
          </table>
          <p className="rules-note">A perfect Finals series = <span className="rules-highlight">40 pts</span>.</p>
        </div>
      </div>
    </div>
  );
}