import { useState } from 'react';
import { toLocalDateInputValue } from './date';
import { GamesPage } from './pages/GamesPage';
import { GameDetailPage } from './pages/GameDetailPage';
import { RawMlbStatsPage } from './pages/RawMlbStatsPage';
import { RawGamePage } from './pages/RawGamePage';

const path = window.location.pathname.replace(/\/+$/, '');
const gameMatch = /^\/mlb-stats\/raw\/games\/([1-9]\d*)$/.exec(path);
const detailMatch = /^\/games\/([1-9]\d*)$/.exec(path);
const isRawPage = path === '/mlb-stats/raw' || gameMatch !== null;

function initialDate(today: string): string {
  const value = new URLSearchParams(window.location.search).get('date');
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return today;
  const parsed = new Date(`${value}T00:00:00`);
  return !Number.isNaN(parsed.getTime()) && toLocalDateInputValue(parsed) === value ? value : today;
}

export function App() {
  const today = toLocalDateInputValue(new Date());
  const [selectedDate, setSelectedDate] = useState(() => initialDate(today));
  const changeDate = (date: string) => {
    setSelectedDate(date);
    const url = new URL(window.location.href);
    url.searchParams.set('date', date);
    window.history.replaceState(null, '', url);
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <div className="header-inner">
          <div className="brand-mark" aria-hidden="true">M</div>
          <div className="brand-name">MLB Matchup Analyzer</div>
          <nav className="header-nav" aria-label="Primary">
            <a className={!isRawPage ? 'header-link active' : 'header-link'} href={`/?date=${selectedDate}`} aria-current={!isRawPage ? 'page' : undefined}>Games</a>
            <a className={isRawPage ? 'header-link active' : 'header-link'} href={`/mlb-stats/raw?date=${selectedDate}`} aria-current={isRawPage ? 'page' : undefined}>Raw data</a>
          </nav>
        </div>
      </header>

      <main id="main-content" className="main-content">
        {gameMatch ? (
          <RawGamePage gamePk={Number(gameMatch[1])} selectedDate={selectedDate} />
        ) : isRawPage ? (
          <RawMlbStatsPage selectedDate={selectedDate} today={today} onDateChange={changeDate} />
        ) : detailMatch ? (
          <GameDetailPage gamePk={Number(detailMatch[1])} selectedDate={selectedDate} />
        ) : (
          <GamesPage selectedDate={selectedDate} today={today} onDateChange={changeDate} />
        )}
      </main>
    </div>
  );
}
