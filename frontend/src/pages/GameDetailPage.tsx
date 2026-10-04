import { useEffect, useState, type KeyboardEvent } from 'react';
import { getGameDetail, type GameDetail, type TeamBox } from '../api/games';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; game: GameDetail };

type GameDetailPageProps = { gamePk: number; selectedDate: string };
type DetailTab = 'boxscore' | 'plays';

function display(value: number | string | null): string {
  return value === null ? '-' : String(value);
}

function gameTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  }).format(date);
}

function LineScore({ game }: { game: GameDetail }) {
  const rows = [game.away, game.home];
  return (
    <div className="detail-table-scroll">
      <table className="line-score-table">
        <caption className="visually-hidden">Inning-by-inning line score</caption>
        <thead><tr><th scope="col">Team</th>{game.innings.map((inning) => <th scope="col" key={inning.number}>{inning.number}</th>)}<th scope="col">R</th><th scope="col">H</th><th scope="col">E</th></tr></thead>
        <tbody>{rows.map((team, index) => (
          <tr key={team.team_id}>
            <th scope="row">{team.abbreviation ?? team.name}</th>
            {game.innings.map((inning) => <td key={inning.number}>{display(index === 0 ? inning.away_runs : inning.home_runs)}</td>)}
            <td className="score-total">{display(team.score.runs)}</td>
            <td>{display(team.score.hits)}</td>
            <td>{display(team.score.errors)}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function TeamBoxScore({ team }: { team: TeamBox }) {
  return (
    <section className="team-boxscore" aria-labelledby={`team-${team.team_id}`}>
      <h3 id={`team-${team.team_id}`}>{team.name}</h3>
      <h4>Batting</h4>
      {team.batting.length === 0 ? <p className="detail-empty">No batting stats yet.</p> : (
        <div className="detail-table-scroll">
          <table className="stats-table">
            <caption className="visually-hidden">{team.name} batting</caption>
            <thead><tr><th scope="col">Player</th><th scope="col">Pos</th><th scope="col">AB</th><th scope="col">R</th><th scope="col">H</th><th scope="col">RBI</th><th scope="col">BB</th><th scope="col">K</th></tr></thead>
            <tbody>{team.batting.map((player) => (
              <tr key={player.player_id}>
                <th scope="row">{player.name}</th><td>{display(player.position)}</td><td>{display(player.at_bats)}</td><td>{display(player.runs)}</td><td>{display(player.hits)}</td><td>{display(player.rbi)}</td><td>{display(player.walks)}</td><td>{display(player.strikeouts)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <h4>Pitching</h4>
      {team.pitching.length === 0 ? <p className="detail-empty">No pitching stats yet.</p> : (
        <div className="detail-table-scroll">
          <table className="stats-table">
            <caption className="visually-hidden">{team.name} pitching</caption>
            <thead><tr><th scope="col">Player</th><th scope="col">IP</th><th scope="col">H</th><th scope="col">R</th><th scope="col">ER</th><th scope="col">BB</th><th scope="col">K</th><th scope="col">P</th></tr></thead>
            <tbody>{team.pitching.map((player) => (
              <tr key={player.player_id}>
                <th scope="row">{player.name}</th><td>{display(player.innings_pitched)}</td><td>{display(player.hits)}</td><td>{display(player.runs)}</td><td>{display(player.earned_runs)}</td><td>{display(player.walks)}</td><td>{display(player.strikeouts)}</td><td>{display(player.pitches)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function GameDetailPage({ gamePk, selectedDate }: GameDetailPageProps) {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [requestVersion, setRequestVersion] = useState(0);
  const [tab, setTab] = useState<DetailTab>('boxscore');
  const [scoringOnly, setScoringOnly] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoadState({ status: 'loading' });
    getGameDetail(gamePk, controller.signal)
      .then((game) => {
        if (!controller.signal.aborted) setLoadState({ status: 'success', game });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLoadState({ status: 'error', message: error instanceof Error ? error.message : 'Could not load game.' });
      });
    return () => controller.abort();
  }, [gamePk, requestVersion]);

  const game = loadState.status === 'success' ? loadState.game : null;
  const plays = game ? game.plays.filter((play) => !scoringOnly || play.is_scoring_play).slice().reverse() : [];
  const changeTab = (next: DetailTab) => {
    setTab(next);
    document.getElementById(`tab-${next}`)?.focus();
  };
  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      changeTab(tab === 'boxscore' ? 'plays' : 'boxscore');
    }
  };

  return (
    <>
      <div className="page-heading detail-heading">
        <div>
          <p className="eyebrow">Game center</p>
          <h1>{game ? `${game.away.name} at ${game.home.name}` : `Game ${gamePk}`}</h1>
          <p className="date-subtitle"><a href={`/?date=${selectedDate}`}>Back to games</a>{game && <> {' | '} {gameTime(game.game_date)}{game.venue && ` | ${game.venue}`}</>}</p>
        </div>
        <a className="detail-raw-link" href={`/mlb-stats/raw/games/${gamePk}?date=${selectedDate}`}>Raw feed</a>
      </div>

      {loadState.status === 'loading' && <div className="games-message detail-message" role="status">Loading game...</div>}
      {loadState.status === 'error' && (
        <div className="games-message games-error detail-message" role="alert">
          <p>{loadState.message}</p>
          <button className="secondary-button" type="button" onClick={() => setRequestVersion((version) => version + 1)}>Retry</button>
        </div>
      )}
      {game && (
        <>
          <section className="detail-summary" aria-label="Game score">
            <div className="detail-scoreboard">
              <div className="detail-score-team"><span>{game.away.name}</span><strong>{display(game.away.score.runs)}</strong></div>
              <div className="detail-score-team"><span>{game.home.name}</span><strong>{display(game.home.score.runs)}</strong></div>
              <span className="detail-status">{game.status}</span>
            </div>
            {game.innings.length > 0 && <LineScore game={game} />}
          </section>

          <div className="detail-tabs" role="tablist" aria-label="Game details">
            <button id="tab-boxscore" type="button" role="tab" tabIndex={tab === 'boxscore' ? 0 : -1} aria-selected={tab === 'boxscore'} aria-controls="panel-boxscore" onClick={() => setTab('boxscore')} onKeyDown={onTabKeyDown}>Box score</button>
            <button id="tab-plays" type="button" role="tab" tabIndex={tab === 'plays' ? 0 : -1} aria-selected={tab === 'plays'} aria-controls="panel-plays" onClick={() => setTab('plays')} onKeyDown={onTabKeyDown}>Plays <span>{game.plays.length}</span></button>
          </div>

          {tab === 'boxscore' ? (
            <div id="panel-boxscore" role="tabpanel" aria-labelledby="tab-boxscore" className="detail-panel">
              <TeamBoxScore team={game.away} />
              <TeamBoxScore team={game.home} />
            </div>
          ) : (
            <section id="panel-plays" role="tabpanel" aria-labelledby="tab-plays" className="detail-panel">
              <div className="detail-section-head">
                <h2>Play log</h2>
                <label className="detail-filter"><input type="checkbox" checked={scoringOnly} onChange={(event) => setScoringOnly(event.target.checked)} /> Scoring plays</label>
              </div>
              {plays.length === 0 ? <p className="detail-empty">No plays available.</p> : (
                <ol className="play-list">{plays.map((play, index) => (
                  <li className={play.is_scoring_play ? 'play-item scoring-play' : 'play-item'} key={`${play.inning}-${play.half}-${index}`}>
                    <div className="play-meta"><span>{play.half === 'top' ? 'Top' : 'Bottom'} {play.inning}</span><span>{play.event}</span>{play.away_score !== null && play.home_score !== null && <strong>{game.away.abbreviation ?? 'Away'} {play.away_score} - {game.home.abbreviation ?? 'Home'} {play.home_score}</strong>}</div>
                    <p>{play.description}</p>
                  </li>
                ))}</ol>
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}
