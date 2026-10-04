const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

function loadTypeScript(relativePath) {
  const sourcePath = path.resolve(__dirname, relativePath);
  const compiled = ts.transpileModule(readFileSync(sourcePath, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  });
  const loaded = new Module(sourcePath, module);
  loaded.filename = sourcePath;
  loaded.paths = Module._nodeModulePaths(path.dirname(sourcePath));
  loaded.require = function (specifier) {
    if (specifier === '../config') return { apiBaseUrl: '/api' };
    return Module.prototype.require.call(this, specifier);
  };
  loaded._compile(compiled.outputText, sourcePath);
  return loaded.exports;
}

const { getRawMlbGame } = loadTypeScript('../src/api/rawMlbStats.ts');
const { gamePlayers, playerPlays } = loadTypeScript('../src/api/gameFeed.ts');
const { scheduleGames } = loadTypeScript('../src/api/scheduleGames.ts');

test('game feed request uses the game ID and returns the unchanged JSON text', async (t) => {
  const raw = '{"gamePk":123, "gameData":{"players":{}}}';
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => new Response(raw));
  const controller = new AbortController();

  assert.equal(await getRawMlbGame(123, controller.signal), raw);
  assert.equal(fetchMock.mock.calls[0].arguments[0], '/api/raw/mlb-stats/games/123');
  assert.equal(fetchMock.mock.calls[0].arguments[1].signal, controller.signal);
});

test('game feed request reports backend errors', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Feed unavailable' }, { status: 502 }));
  await assert.rejects(getRawMlbGame(123, new AbortController().signal), { message: 'Feed unavailable' });
});

test('player extraction includes profile and matching boxscore entry', () => {
  const raw = JSON.stringify({
    gameData: { players: { ID42: { id: 42, fullName: 'Casey Smith' }, ID7: { id: 7, fullName: 'Alex Jones' } } },
    liveData: { boxscore: { teams: { away: { players: { ID42: { stats: { batting: { hits: 2 } } } } }, home: { players: {} } } } },
  });
  assert.deepEqual(gamePlayers(raw), [
    { id: 7, name: 'Alex Jones', profile: { id: 7, fullName: 'Alex Jones' }, boxscore: null },
    { id: 42, name: 'Casey Smith', profile: { id: 42, fullName: 'Casey Smith' }, boxscore: { stats: { batting: { hits: 2 } } } },
  ]);
});

test('player extraction tolerates missing player data and invalid JSON', () => {
  assert.deepEqual(gamePlayers('{}'), []);
  assert.deepEqual(gamePlayers('not json'), []);
});

test('player plays include batting, pitching, and running involvement', () => {
  const batting = { matchup: { batter: { id: 42 }, pitcher: { id: 7 } }, playEvents: [{ pitchNumber: 1 }] };
  const running = { matchup: { batter: { id: 9 }, pitcher: { id: 7 } }, runners: [{ details: { runner: { id: 42 } } }] };
  const unrelated = { matchup: { batter: { id: 9 }, pitcher: { id: 7 } } };
  const raw = JSON.stringify({ liveData: { plays: { allPlays: [batting, running, unrelated] } } });
  assert.deepEqual(playerPlays(raw, 42), [batting, running]);
  assert.deepEqual(playerPlays(raw, 7), [batting, running, unrelated]);
  assert.deepEqual(playerPlays('{}', 42), []);
});

test('schedule game links use gamePk and team names', () => {
  const raw = JSON.stringify({ dates: [{ games: [
    { gamePk: 123, teams: { away: { team: { name: 'Mets' } }, home: { team: { name: 'Cubs' } } } },
    { gamePk: 456 },
  ] }] });
  assert.deepEqual(scheduleGames(raw), [
    { gamePk: 123, label: 'Mets at Cubs' },
    { gamePk: 456, label: 'Game 456' },
  ]);
  assert.deepEqual(scheduleGames('invalid'), []);
});
