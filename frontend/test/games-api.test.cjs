const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

const sourcePath = path.resolve(__dirname, '../src/api/games.ts');
const source = readFileSync(sourcePath, 'utf8');
const compiled = ts.transpileModule(source, {
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
const { getGames, getGameDetail } = loaded.exports;

test('getGames sends the selected date as the only query parameter and forwards the signal', async (t) => {
  const controller = new AbortController();
  const fetchMock = t.mock.method(globalThis, 'fetch', async () =>
    new Response(JSON.stringify({ date: '2026-04-01', games: [] }), {
      headers: { 'content-type': 'application/json' },
    }),
  );

  await getGames('2026-04-01', controller.signal);

  assert.equal(fetchMock.mock.callCount(), 1);
  const [url, options] = fetchMock.mock.calls[0].arguments;
  assert.equal(url, '/api/games?date=2026-04-01');
  assert.deepEqual([...new URL(url, 'http://localhost').searchParams], [['date', '2026-04-01']]);
  assert.equal(options.signal, controller.signal);
  assert.deepEqual(options.headers, { Accept: 'application/json' });
});

test('getGames returns games from a successful response', async (t) => {
  const payload = {
    date: '2026-04-01',
    games: [{
      game_id: 123,
      game_date: '2026-04-01T19:10:00Z',
      status: 'Scheduled',
      start_time_tbd: false,
      away: { team_id: 1, name: 'Away', score: null, probable_pitcher_name: null },
      home: { team_id: 2, name: 'Home', score: null, probable_pitcher_name: 'Starter' },
    }],
  };
  t.mock.method(globalThis, 'fetch', async () => Response.json(payload));

  assert.deepEqual(await getGames(payload.date, new AbortController().signal), payload);
});

test('getGames accepts a successful response with zero games', async (t) => {
  const payload = { date: '2026-04-01', games: [] };
  t.mock.method(globalThis, 'fetch', async () => Response.json(payload));

  assert.deepEqual(await getGames(payload.date, new AbortController().signal), payload);
});

test('getGames reports backend error detail', async (t) => {
  t.mock.method(globalThis, 'fetch', async () =>
    Response.json({ detail: 'Schedule unavailable' }, { status: 503 }),
  );

  await assert.rejects(
    getGames('2026-04-01', new AbortController().signal),
    { message: 'Schedule unavailable' },
  );
});

test('getGames rejects a response without a games array', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ date: '2026-04-01', games: null }));

  await assert.rejects(
    getGames('2026-04-01', new AbortController().signal),
    { message: 'Games response was invalid.' },
  );
});

test('getGames forwards abort to the in-flight request', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch', (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(signal.reason), { once: true });
  }));
  const controller = new AbortController();

  const request = getGames('2026-04-01', controller.signal);
  controller.abort();

  await assert.rejects(request, { name: 'AbortError' });
  assert.equal(fetchMock.mock.calls[0].arguments[1].signal, controller.signal);
});

test('getGameDetail requests the formatted game endpoint', async (t) => {
  const payload = {
    game_id: 849830,
    away: { name: 'Padres' },
    home: { name: 'Brewers' },
    innings: [],
    plays: [],
  };
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => Response.json(payload));
  const controller = new AbortController();

  assert.deepEqual(await getGameDetail(849830, controller.signal), payload);
  assert.equal(fetchMock.mock.calls[0].arguments[0], '/api/games/849830');
  assert.equal(fetchMock.mock.calls[0].arguments[1].signal, controller.signal);
});

test('getGameDetail reports backend errors and invalid responses', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Feed unavailable' }, { status: 502 }));
  await assert.rejects(getGameDetail(849830, new AbortController().signal), { message: 'Feed unavailable' });
  globalThis.fetch.mock.mockImplementation(async () => Response.json({ game_id: 849830, innings: [], plays: [] }));
  await assert.rejects(getGameDetail(849830, new AbortController().signal), { message: 'Game response was invalid.' });
});
