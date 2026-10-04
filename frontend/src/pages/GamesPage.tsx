import { useEffect, useState } from 'react';
import { getGames, type Game, type GameTeam } from '../api/games';
import { DateToolbar } from '../components/DateToolbar';
import { EmptyGamesState } from '../components/EmptyGamesState';
import { formatDate } from '../date';

type GamesPageProps = {
  selectedDate: string;
  today: string;
  onDateChange: (date: string) => void;
};

type LoadState =
  | { status: 'loading'; date: string }
  | { status: 'error'; date: string; message: string }
  | { status: 'success'; date: string; games: Game[] };

function gameTime(gameDate: string): string | null {
  if (!gameDate.includes('T')) return null;
  const parsed = new Date(gameDate);
  if (Number.isNaN(parsed.getTime())) return null;
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(parsed);
}

function TeamLine({ team, side }: { team: GameTeam; side: 'Away' | 'Home' }) {
  return (
    <div className="game-team">
      <span className="game-side">{side}</span>
      <div className="game-team-info">
        <span className="game-team-name">{team.name}</span>
        {team.probable_pitcher_name && <span className="game-pitcher">Probable: {team.probable_pitcher_name}</span>}
      </div>
      <span className="game-score">{team.score ?? ''}</span>
    </div>
  );
}

function GameRow({ game, selectedDate }: { game: Game; selectedDate: string }) {
  const time = gameTime(game.game_date);
  const status = game.status.replace(/_/g, ' ');

  return (
    <li className="game-row">
      <div className="game-teams">
        <TeamLine team={game.away} side="Away" />
        <TeamLine team={game.home} side="Home" />
      </div>
      <div className="game-meta">
        <span className="game-status">{status}</span>
        {game.start_time_tbd ? <span>Time TBD</span> : time && <time dateTime={game.game_date}>{time}</time>}
        <a className="game-feed-link" href={`/games/${game.game_id}?date=${selectedDate}`}>View game</a>
      </div>
    </li>
  );
}

export function GamesPage({ selectedDate, today, onDateChange }: GamesPageProps) {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading', date: selectedDate });
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoadState({ status: 'loading', date: selectedDate });

    getGames(selectedDate, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setLoadState({ status: 'success', date: selectedDate, games: response.games });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadState({
            status: 'error',
            date: selectedDate,
            message: error instanceof Error ? error.message : 'Could not load games.',
          });
        }
      });

    return () => controller.abort();
  }, [selectedDate, requestVersion]);

  const currentState: LoadState = loadState.date === selectedDate
    ? loadState
    : { status: 'loading', date: selectedDate };

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Game center</p>
          <h1>{selectedDate === today ? "Today's games" : 'Games'}</h1>
          <p className="date-subtitle">{formatDate(selectedDate)}</p>
        </div>
        <DateToolbar selectedDate={selectedDate} today={today} onDateChange={onDateChange} />
      </div>

      <section className="games-section" aria-labelledby="games-heading">
        <div className="section-heading">
          <h2 id="games-heading">Schedule</h2>
          {currentState.status === 'success' && (
            <span className="games-count">{currentState.games.length} {currentState.games.length === 1 ? 'game' : 'games'}</span>
          )}
        </div>

        {currentState.status === 'loading' && <div className="games-message" role="status">Loading games...</div>}
        {currentState.status === 'error' && (
          <div className="games-message games-error" role="alert">
            <p>{currentState.message}</p>
            <button className="secondary-button" type="button" onClick={() => setRequestVersion((version) => version + 1)}>Retry</button>
          </div>
        )}
        {currentState.status === 'success' && (
          currentState.games.length === 0
            ? <EmptyGamesState />
            : <ul className="games-list">{currentState.games.map((game) => <GameRow key={game.game_id} game={game} selectedDate={selectedDate} />)}</ul>
        )}
      </section>
    </>
  );
}
