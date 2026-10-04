import { useEffect, useState } from 'react';
import { gamePlayers, playerPlays } from '../api/gameFeed';
import { formatRawJson, getRawMlbGame } from '../api/rawMlbStats';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; raw: string; loadedAt: Date };

type RawGamePageProps = { gamePk: number; selectedDate: string };

export function RawGamePage({ gamePk, selectedDate }: RawGamePageProps) {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [requestVersion, setRequestVersion] = useState(0);
  const [view, setView] = useState<'formatted' | 'raw'>('formatted');
  const [playerId, setPlayerId] = useState(() => new URLSearchParams(window.location.search).get('playerId') ?? '');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoadState({ status: 'loading' });
    setCopied(false);
    getRawMlbGame(gamePk, controller.signal)
      .then((raw) => {
        if (!controller.signal.aborted) setLoadState({ status: 'success', raw, loadedAt: new Date() });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadState({ status: 'error', message: error instanceof Error ? error.message : 'Could not load game feed.' });
        }
      });
    return () => controller.abort();
  }, [gamePk, requestVersion]);

  const players = loadState.status === 'success' ? gamePlayers(loadState.raw) : [];
  const selectedPlayer = players.find((player) => String(player.id) === playerId);
  const displayedJson = loadState.status !== 'success' ? '' : selectedPlayer
    ? JSON.stringify({ profile: selectedPlayer.profile, boxscore: selectedPlayer.boxscore, plays: playerPlays(loadState.raw, selectedPlayer.id) })
    : loadState.raw;

  const selectPlayer = (id: string) => {
    setPlayerId(id);
    setCopied(false);
    const url = new URL(window.location.href);
    if (id) url.searchParams.set('playerId', id);
    else url.searchParams.delete('playerId');
    window.history.replaceState(null, '', url);
  };

  const copyJson = async () => {
    if (loadState.status !== 'success') return;
    try {
      await navigator.clipboard.writeText(displayedJson);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">MLB Stats API</p>
          <h1>Game {gamePk} data</h1>
          <p className="date-subtitle"><a href={`/?date=${selectedDate}`}>Back to games</a></p>
        </div>
      </div>

      <section className="raw-section" aria-labelledby="raw-heading">
        <div className="section-heading raw-section-heading">
          <div>
            <h2 id="raw-heading">{selectedPlayer ? selectedPlayer.name : 'Game feed'}</h2>
            {loadState.status === 'success' && (
              <p className="raw-meta">
                {new TextEncoder().encode(displayedJson).length.toLocaleString()} bytes
                {' | '}Loaded {loadState.loadedAt.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="raw-actions">
            <label className="player-field" htmlFor="game-player">Player
              <select id="game-player" value={selectedPlayer ? playerId : ''} onChange={(event) => selectPlayer(event.target.value)} disabled={loadState.status !== 'success' || players.length === 0}>
                <option value="">Full game feed</option>
                {players.map((player) => <option key={player.id} value={player.id}>{player.name}</option>)}
              </select>
            </label>
            <div className="view-switch" role="group" aria-label="JSON display">
              <button type="button" aria-pressed={view === 'formatted'} onClick={() => setView('formatted')}>Formatted</button>
              <button type="button" aria-pressed={view === 'raw'} onClick={() => setView('raw')}>{selectedPlayer ? 'Compact' : 'Raw'}</button>
            </div>
            <button className="secondary-button" type="button" onClick={copyJson} disabled={loadState.status !== 'success'}>{copied ? 'Copied' : 'Copy JSON'}</button>
            <button className="secondary-button" type="button" onClick={() => setRequestVersion((version) => version + 1)} disabled={loadState.status === 'loading'}>Reload</button>
          </div>
        </div>
        {loadState.status === 'loading' && <div className="raw-message" role="status">Loading game feed...</div>}
        {loadState.status === 'error' && (
          <div className="raw-message raw-error" role="alert">
            <p>{loadState.message}</p>
            <button className="secondary-button" type="button" onClick={() => setRequestVersion((version) => version + 1)}>Retry</button>
          </div>
        )}
        {loadState.status === 'success' && (
          <>
            {selectedPlayer && <p className="raw-note">Player data extracted from the game feed.</p>}
            {players.length === 0 && <p className="raw-note">No player records are available in this game feed yet.</p>}
            {playerId && !selectedPlayer && <p className="raw-note">Player {playerId} is not in this feed. Showing the full game feed.</p>}
            <pre className="raw-output" aria-label={selectedPlayer ? `${selectedPlayer.name} JSON` : 'MLB Stats game feed JSON'}>
              {view === 'formatted' ? formatRawJson(displayedJson) : displayedJson}
            </pre>
          </>
        )}
      </section>
    </>
  );
}
