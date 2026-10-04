export function EmptyGamesState() {
  return (
    <div className="empty-state" role="status">
      <div className="empty-state-icon" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <h3>No games scheduled</h3>
      <p>There are no games for this date.</p>
    </div>
  );
}
