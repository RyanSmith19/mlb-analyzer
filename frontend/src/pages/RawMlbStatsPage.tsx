import { useEffect, useState } from 'react';
import { formatRawJson, getRawMlbSchedule } from '../api/rawMlbStats';
import { scheduleGames } from '../api/scheduleGames';
import { DateToolbar } from '../components/DateToolbar';
import { formatDate } from '../date';

type RawMlbStatsPageProps = {
  selectedDate: string;
  today: string;
  onDateChange: (date: string) => void;
};

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; raw: string; loadedAt: Date };

export function RawMlbStatsPage({ selectedDate, today, onDateChange }: RawMlbStatsPageProps) {
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' });
  const [requestVersion, setRequestVersion] = useState(0);
  const [view, setView] = useState<'formatted' | 'raw'>('formatted');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoadState({ status: 'loading' });
    setCopied(false);

    getRawMlbSchedule(selectedDate, controller.signal)
      .then((raw) => {
        if (!controller.signal.aborted) setLoadState({ status: 'success', raw, loadedAt: new Date() });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadState({ status: 'error', message: error instanceof Error ? error.message : 'Could not load schedule.' });
        }
      });

    return () => controller.abort();
  }, [selectedDate, requestVersion]);

  const reload = () => setRequestVersion((version) => version + 1);
  const games = loadState.status === 'success' ? scheduleGames(loadState.raw) : [];
  const copyRaw = async () => {
    if (loadState.status !== 'success') return;
    try {
      await navigator.clipboard.writeText(loadState.raw);
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
          <h1>Raw schedule</h1>
          <p className="date-subtitle">{formatDate(selectedDate)}</p>
        </div>
        <DateToolbar selectedDate={selectedDate} today={today} onDateChange={onDateChange} />
      </div>

      <section className="raw-section" aria-labelledby="raw-heading">
        <div className="section-heading raw-section-heading">
          <div>
            <h2 id="raw-heading">Response</h2>
            {loadState.status === 'success' && (
              <p className="raw-meta">
                {new TextEncoder().encode(loadState.raw).length.toLocaleString()} bytes
                {' | '}Loaded {loadState.loadedAt.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="raw-actions">
            <div className="view-switch" role="group" aria-label="JSON display">
              <button type="button" aria-pressed={view === 'formatted'} onClick={() => setView('formatted')}>Formatted</button>
              <button type="button" aria-pressed={view === 'raw'} onClick={() => setView('raw')}>Raw</button>
            </div>
            <button className="secondary-button" type="button" onClick={copyRaw} disabled={loadState.status !== 'success'}>
              {copied ? 'Copied' : 'Copy JSON'}
            </button>
            <button className="secondary-button" type="button" onClick={reload} disabled={loadState.status === 'loading'}>
              Reload
            </button>
          </div>
        </div>

        {loadState.status === 'loading' && <div className="raw-message" role="status">Loading schedule...</div>}
        {loadState.status === 'error' && (
          <div className="raw-message raw-error" role="alert">
            <p>{loadState.message}</p>
            <button className="secondary-button" type="button" onClick={reload}>Retry</button>
          </div>
        )}
        {loadState.status === 'success' && (
          <>
            {games.length > 0 && (
              <nav className="raw-game-nav" aria-label="Game feeds">
                {games.map((game) => <a key={game.gamePk} href={`/mlb-stats/raw/games/${game.gamePk}?date=${selectedDate}`}>{game.label}</a>)}
              </nav>
            )}
            <pre className="raw-output" aria-label="MLB Stats schedule JSON">
              {view === 'formatted' ? formatRawJson(loadState.raw) : loadState.raw}
            </pre>
          </>
        )}
      </section>
    </>
  );
}
