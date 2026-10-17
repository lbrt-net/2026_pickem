// Shared stats-page controls: player search + team filter, and the pager that sits under each table.
export function TableFilter({ query, setQuery, team, setTeam, teams }) {
  return (
    <div className="st-filter">
      <input id="st-player" type="search" placeholder="Player" value={query} onChange={e => setQuery(e.target.value)} aria-label="Find a player" />
      <select id="st-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Team">
        <option value="">All teams</option>
        {teams.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
    </div>
  );
}

export function Pager({ page, pages, total, size, setPage }) {
  if (total <= size) return null;
  return (
    <div className="st-pager">
      <span>{page * size + 1}–{Math.min(total, (page + 1) * size)} of {total}</span>
      <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0} aria-label="Previous page">‹</button>
      <button onClick={() => setPage(Math.min(pages - 1, page + 1))} disabled={page >= pages - 1} aria-label="Next page">›</button>
    </div>
  );
}

