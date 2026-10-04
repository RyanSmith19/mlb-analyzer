# MLB Pitch Matchup Analyzer Jira Plan

## Project Summary

Build a full-stack baseball analytics application that identifies favorable and unfavorable hitter-vs-pitcher matchups using MLB Stats API operational data and Statcast pitch-level data.

After the pitch-type MVP, extend it into a daily decision-support system with independently modeled outcome probabilities, calibrated confidence, read-only prediction-market comparison, and historical evaluation. Market prices must never enter the independent baseball probability model.

The MVP should answer:

> Which hitters today have the best underlying pitch-profile matchup against the starting pitcher, and why?

The first implementation should use fixture Statcast data to validate architecture, analytics, API contracts, and UI before adding real ingestion from MLB Stats API and Baseball Savant/pybaseball.

## Jira Setup

Suggested project key: `MLB`

Suggested issue types:

- `Epic`
- `Story`
- `Task`
- `Bug`
- `Spike`

Suggested priorities:

- `P0`: Required for the first vertical slice
- `P1`: Required for MVP
- `P2`: Important after MVP
- `P3`: Later enhancement

Suggested labels:

- `backend`
- `frontend`
- `analytics`
- `data-ingestion`
- `api`
- `database`
- `testing`
- `devops`
- `mvp`
- `future`
- `probability`
- `market-data`
- `backtesting`
- `read-only`

## Release Milestones

### Milestone 1: Repository and Domain Foundation

Goal: Create the project structure, define domain contracts, and establish test infrastructure.

### Milestone 2: Fixture-Based Analytics Vertical Slice

Goal: Use local fixture Statcast data to generate pitcher profiles, hitter profiles, matchup scores, API responses, and a basic React display.

### Milestone 3: MVP Data Integration

Goal: Add MLB schedule/probable pitcher data, local Statcast storage, incremental ingestion, and game-level matchup rankings.

### Milestone 4: MVP Product Polish

Goal: Improve explainability, missing-data handling, confidence display, and production readiness.

### Milestone 5: Future Analytics Expansion

Goal: Add advanced baseball features after the MVP is validated, measuring each against the pitch-type baseline.

### Milestone 6: Probability and Mock Market Vertical Slice

Goal: Define probability, confidence, market, edge, and target-price contracts. Use fixtures and a mock provider to prove the full Statcast-to-UI path without a live market dependency.

### Milestone 7: Historical Evaluation

Goal: Persist immutable model predictions, settle outcomes, and measure calibration before enabling any live provider.

### Milestone 8: Authorized Market Data and Daily Opportunities

Goal: Investigate permitted data access, integrate a supported provider only if available, persist timestamped prices, and show read-only opportunities.

### Milestone 9: Deeper Baseball Context and Market History

Goal: Add location, count, pitch shape, recent arsenal, park, weather, bullpen, and similar-pitcher features when their measured value justifies them; add price history and optional alerts.

---

# Epics and Tickets

## Epic MLB-1: Repository Foundation and Architecture

Create the initial monorepo structure, developer tooling, application boundaries, and shared conventions.

### MLB-2: Scaffold backend project

Issue type: `Story`  
Priority: `P0`  
Labels: `backend`, `mvp`

Description:

Create the FastAPI backend structure with clear folders for API routes, clients, ingestion, database models, analytics, matchup calculation, services, configuration, and tests.

Suggested structure:

```text
backend/
  app/
    api/
    analytics/
    clients/
    ingestion/
    matchup/
    models/
    services/
    config.py
    main.py
  tests/
```

Acceptance criteria:

- `backend/app/main.py` exposes a working FastAPI app.
- Backend package imports work from tests.
- Health endpoint returns a successful response.
- Backend has a clear configuration module.
- Basic test command is documented and passes.

Dependencies:

- None

### MLB-3: Scaffold frontend project

Issue type: `Story`  
Priority: `P0`  
Labels: `frontend`, `mvp`

Description:

Create the React + TypeScript frontend structure for the matchup analyzer.

Acceptance criteria:

- Frontend app starts locally.
- Main page renders a shell for today's games.
- API base URL is configurable.
- TypeScript build succeeds.
- Frontend README instructions are added.

Dependencies:

- None

### MLB-4: Add root developer documentation

Issue type: `Task`  
Priority: `P0`  
Labels: `devops`, `testing`

Description:

Add root-level documentation describing repository layout, setup commands, local development workflow, testing, and fixture-data strategy.

Acceptance criteria:

- Root `README.md` explains backend and frontend setup.
- Local development commands are listed.
- Testing commands are listed.
- Fixture-first development approach is documented.

Dependencies:

- `MLB-2`
- `MLB-3`

### MLB-5: Define primary domain models

Issue type: `Story`  
Priority: `P0`  
Labels: `backend`, `analytics`, `mvp`

Description:

Define typed domain models for games, players, pitchers, hitters, pitch profiles, hitter profiles, matchup results, pitch matchup explanations, and confidence.

Acceptance criteria:

- Domain models exist separately from raw API/database models.
- Models include pitcher handedness, batter side, pitch type, usage, sample size, raw metrics, adjusted metrics, score, confidence, and explanation fields.
- Matchup result can represent biggest advantage and biggest disadvantage.
- Unit tests validate model serialization where applicable.

Dependencies:

- `MLB-2`

---

## Epic MLB-6: Fixture Data and Analytics Core

Build the first deterministic analytics path from sample Statcast rows to matchup results.

### MLB-7: Create fixture Statcast dataset

Issue type: `Story`  
Priority: `P0`  
Labels: `analytics`, `testing`, `mvp`

Description:

Create a small fixture dataset with known pitchers, hitters, pitch types, handedness, pitch outcomes, launch metrics, and expected values.

Acceptance criteria:

- Fixture data includes at least one pitcher with multiple pitch types.
- Fixture data includes multiple hitters with varied strengths and weaknesses.
- Fixture data includes both right-handed and left-handed pitcher splits where practical.
- Expected aggregate values are documented for deterministic tests.
- Fixture is small enough for manual verification.

Dependencies:

- `MLB-5`

### MLB-8: Implement Statcast parsing layer

Issue type: `Story`  
Priority: `P0`  
Labels: `backend`, `analytics`, `testing`

Description:

Parse fixture Statcast rows into internal typed records. Keep parsing logic isolated so later pybaseball/Baseball Savant ingestion can reuse the same normalized representation.

Acceptance criteria:

- Parser handles required Statcast fields.
- Parser validates required fields and handles nullable metrics safely.
- Tests cover valid rows, missing optional values, and invalid required values.
- No analytics code depends directly on raw CSV or external API field names.

Dependencies:

- `MLB-7`

### MLB-9: Build pitcher profile generator

Issue type: `Story`  
Priority: `P0`  
Labels: `analytics`, `backend`, `mvp`

Description:

Generate pitcher pitch-type profiles from normalized Statcast rows.

Metrics:

- pitch type
- usage percentage
- pitch count
- average velocity
- velocity standard deviation
- average horizontal movement
- average vertical movement
- zone percentage
- whiff percentage
- xwOBA allowed
- hard-hit percentage
- barrel percentage

Acceptance criteria:

- Pitch usage sums to approximately 100% per profile.
- Metrics are calculated per pitch type.
- Profiles support handedness splits against left-handed and right-handed batters.
- Unit tests validate calculations against fixture expected values.

Dependencies:

- `MLB-8`

### MLB-10: Build hitter profile generator

Issue type: `Story`  
Priority: `P0`  
Labels: `analytics`, `backend`, `mvp`

Description:

Generate hitter performance profiles against pitch types, split by pitcher handedness.

Metrics:

- pitch type
- pitches seen
- plate appearances where available
- xwOBA
- wOBA
- whiff percentage
- strikeout percentage
- hard-hit percentage
- barrel percentage
- average exit velocity

Acceptance criteria:

- Profiles are grouped by hitter, pitcher handedness, and pitch type.
- Sample size is retained for every metric.
- Missing launch metrics do not break profile generation.
- Unit tests validate calculations against fixture expected values.

Dependencies:

- `MLB-8`

### MLB-11: Implement sample-size regression

Issue type: `Story`  
Priority: `P0`  
Labels: `analytics`, `testing`, `mvp`

Description:

Implement configurable regression to league average so small samples do not create extreme matchup conclusions.

Formula:

```text
AdjustedMetric =
  (sample_size / (sample_size + K)) * player_metric
  +
  (K / (sample_size + K)) * league_average
```

Acceptance criteria:

- `K` is configurable.
- Raw metric, adjusted metric, sample size, and confidence are retained.
- Very small samples regress strongly toward league average.
- Large samples stay close to player metric.
- Unit tests cover edge cases, including zero sample size.

Dependencies:

- `MLB-9`
- `MLB-10`

### MLB-12: Define matchup model interface

Issue type: `Story`  
Priority: `P0`  
Labels: `analytics`, `backend`, `mvp`

Description:

Create an abstract matchup model interface that can support multiple future algorithms.

Acceptance criteria:

- Interface supports `calculate(pitcher_profile, hitter_profile) -> MatchupResult`.
- Weighted model can be added without changing API or UI contracts.
- Interface does not depend on FastAPI, SQLAlchemy, or frontend types.
- Unit tests prove a fake implementation can be swapped in.

Dependencies:

- `MLB-5`

### MLB-13: Implement weighted matchup model

Issue type: `Story`  
Priority: `P0`  
Labels: `analytics`, `backend`, `mvp`

Description:

Implement the first interpretable matchup model using pitcher pitch usage, hitter pitch-type performance, pitcher vulnerability, and sample-size adjusted metrics.

Conceptual formula:

```text
MatchupScore =
  SUM(
    pitcher_pitch_usage
    * hitter_pitch_performance
    * pitcher_pitch_vulnerability
  )
```

Acceptance criteria:

- Model produces a normalized score from `0` to `100`.
- Score bands are implemented:
  - `90-100`: Elite matchup
  - `75-89`: Strong advantage
  - `55-74`: Slight advantage
  - `45-54`: Neutral
  - `25-44`: Slight disadvantage
  - `0-24`: Poor matchup
- Model returns per-pitch-type contributions.
- Model returns biggest advantage and biggest disadvantage.
- Model returns confidence.
- Unit tests are deterministic.

Dependencies:

- `MLB-9`
- `MLB-10`
- `MLB-11`
- `MLB-12`

---

## Epic MLB-14: Backend API

Expose fixture-backed and then real-data-backed analytics through clean REST endpoints.

### MLB-15: Create matchup API schemas

Issue type: `Story`  
Priority: `P0`  
Labels: `api`, `backend`, `mvp`

Description:

Create Pydantic response schemas for matchup scores, pitch breakdowns, player summaries, pitcher profiles, hitter profiles, and game summaries.

Acceptance criteria:

- Schemas are independent of raw database entities.
- Schemas include score, confidence, pitch breakdown, sample size, and explanation fields.
- Example response matches the product brief shape.
- Schema tests validate expected JSON output.

Dependencies:

- `MLB-5`
- `MLB-13`

### MLB-16: Add fixture-backed matchup endpoint

Issue type: `Story`  
Priority: `P0`  
Labels: `api`, `backend`, `mvp`

Description:

Create a fixture-backed endpoint for a single pitcher-vs-hitter matchup.

Endpoint:

```text
GET /matchups/{pitcher_id}/{hitter_id}
```

Acceptance criteria:

- Endpoint returns matchup score and explanation for fixture players.
- Unknown pitcher or hitter returns a clear 404 response.
- Endpoint response includes pitch-type breakdown.
- API test covers successful and missing-player responses.

Dependencies:

- `MLB-13`
- `MLB-15`

### MLB-17: Add fixture-backed game matchup endpoint

Issue type: `Story`  
Priority: `P0`  
Labels: `api`, `backend`, `mvp`

Description:

Create a fixture-backed endpoint that ranks all opposing hitters against a starter.

Endpoint:

```text
GET /games/{game_id}/matchups
```

Acceptance criteria:

- Endpoint returns a game summary, starting pitcher, and ranked hitter matchups.
- Rankings sort from highest score to lowest score.
- Each hitter row includes score, confidence, and top explanation.
- API test validates ranking order.

Dependencies:

- `MLB-16`

### MLB-18: Add profile endpoints

Issue type: `Story`  
Priority: `P1`  
Labels: `api`, `backend`

Description:

Expose pitcher and hitter profile endpoints.

Endpoints:

```text
GET /pitchers/{pitcher_id}/profile
GET /hitters/{hitter_id}/profile
```

Acceptance criteria:

- Pitcher profile endpoint returns arsenal and per-pitch metrics.
- Hitter profile endpoint returns pitch-type performance split by pitcher handedness.
- Responses include sample size and adjusted metrics.
- API tests cover both endpoints.

Dependencies:

- `MLB-9`
- `MLB-10`
- `MLB-15`

---

## Epic MLB-19: Frontend Vertical Slice

Build the first user-facing workflow using fixture-backed API data.

### MLB-20: Build games list page

Issue type: `Story`  
Priority: `P0`  
Labels: `frontend`, `mvp`

Description:

Create the initial page that lists games for a selected date. Use fixture API data until real MLB schedule integration is available.

Acceptance criteria:

- Page title identifies the product as MLB Matchup Analyzer.
- Date selector or selected-date display is present.
- Game cards show teams, start time, and probable starter when available.
- User can select a game to view matchups.

Dependencies:

- `MLB-3`
- `MLB-17`

### MLB-21: Build game matchup rankings view

Issue type: `Story`  
Priority: `P0`  
Labels: `frontend`, `mvp`

Description:

Display ranked hitter matchups for a selected game.

Acceptance criteria:

- Hitters are shown from best matchup to worst matchup.
- Each row displays hitter name, score, confidence, and short reason.
- Score bands are visually distinguishable.
- Loading, error, and empty states are handled.

Dependencies:

- `MLB-20`

### MLB-22: Build hitter matchup detail view

Issue type: `Story`  
Priority: `P0`  
Labels: `frontend`, `mvp`

Description:

Create a detail view explaining why a hitter received a matchup score.

Acceptance criteria:

- Detail view shows overall score and confidence.
- View shows biggest advantage and biggest disadvantage.
- View shows pitch-by-pitch-type breakdown.
- Breakdown includes pitcher usage, hitter performance, pitcher performance, impact, and sample size.
- UI does not calculate baseball statistics client-side.

Dependencies:

- `MLB-16`
- `MLB-21`

### MLB-23: Create shared frontend API client and types

Issue type: `Story`  
Priority: `P0`  
Labels: `frontend`, `api`, `mvp`

Description:

Create a typed frontend API client for backend endpoints.

Acceptance criteria:

- API client centralizes fetch logic.
- TypeScript types match backend responses.
- Network errors are normalized for UI usage.
- Tests or type checks cover expected response shapes.

Dependencies:

- `MLB-15`
- `MLB-3`

---

## Epic MLB-24: Database and Local Statcast Storage

Store Statcast and derived analytics locally so matchup requests do not repeatedly query external data sources.

### MLB-25: Design initial database schema

Issue type: `Story`  
Priority: `P1`  
Labels: `database`, `backend`, `mvp`

Description:

Design PostgreSQL-compatible tables for players, teams, games, appearances, raw Statcast pitches, pitcher profiles, hitter profiles, and ingestion state.

Acceptance criteria:

- Schema supports SQLite for local development where practical.
- Schema stores raw Statcast rows with extensible fields.
- Schema stores derived profile snapshots or cache tables.
- Schema tracks ingestion ranges and update status.
- Schema supports player IDs from MLB Stats API.

Dependencies:

- `MLB-5`

### MLB-26: Add SQLAlchemy models and migrations

Issue type: `Story`  
Priority: `P1`  
Labels: `database`, `backend`

Description:

Implement SQLAlchemy models and migration tooling for the initial schema.

Acceptance criteria:

- Models reflect the approved schema.
- Migration creates all required tables.
- Local database setup is documented.
- Tests can run against an isolated test database.

Dependencies:

- `MLB-25`

### MLB-27: Implement profile cache persistence

Issue type: `Story`  
Priority: `P1`  
Labels: `database`, `analytics`, `backend`

Description:

Persist calculated pitcher and hitter profiles so expensive analytics can be reused.

Acceptance criteria:

- Profile cache stores calculation version.
- Profile cache can be invalidated by season/date range.
- API can read profiles from cache.
- Tests cover cache read/write behavior.

Dependencies:

- `MLB-26`
- `MLB-9`
- `MLB-10`

---

## Epic MLB-28: MLB Stats API Integration

Integrate operational MLB data through a dedicated client abstraction.

### MLB-29: Build MLB Stats API client interface

Issue type: `Story`  
Priority: `P1`  
Labels: `backend`, `api`, `data-ingestion`, `mvp`

Description:

Create an MLB API client abstraction for schedules, games, probable pitchers, lineups, teams, rosters, and players.

Acceptance criteria:

- Client exposes methods such as `get_games(date)`, `get_probable_pitchers(game_id)`, `get_lineup(game_id)`, and `get_player(player_id)`.
- Raw HTTP details are isolated inside the client.
- Application services do not depend on raw MLB API response structures.
- Tests mock external API responses.

Dependencies:

- `MLB-2`
- `MLB-5`

### MLB-30: Implement selected-date games service

Issue type: `Story`  
Priority: `P1`  
Labels: `backend`, `api`, `mvp`

Description:

Create a service that retrieves games for a selected date and normalizes them for API/frontend usage.

Acceptance criteria:

- Service returns teams, game time, status, probable pitchers, and game ID.
- Service handles missing probable pitchers gracefully.
- Service can use fixture data in tests.
- `GET /games/today` and selected-date support are available.

Dependencies:

- `MLB-29`

### MLB-31: Add lineup retrieval and fallback strategy

Issue type: `Story`  
Priority: `P1`  
Labels: `backend`, `api`, `mvp`

Description:

Retrieve confirmed or expected lineups when available, with fallback to roster or projected hitter list for incomplete pregame data.

Acceptance criteria:

- Confirmed lineups are preferred when available.
- Missing lineups return clear uncertainty metadata.
- Fallback source is identified in API responses.
- Tests cover confirmed lineup, missing lineup, and partial lineup scenarios.

Dependencies:

- `MLB-29`
- `MLB-30`

---

## Epic MLB-32: Statcast Ingestion

Retrieve, normalize, store, and incrementally update Statcast pitch-level data.

### MLB-33: Build Statcast ingestion interface

Issue type: `Story`  
Priority: `P1`  
Labels: `data-ingestion`, `analytics`, `backend`, `mvp`

Description:

Create an ingestion abstraction for retrieving Statcast pitch-level data, initially compatible with pybaseball/Baseball Savant output.

Acceptance criteria:

- Ingestion interface accepts date ranges.
- Ingestion returns normalized internal pitch records.
- Required fields are validated.
- Tests use mocked or fixture Statcast data.

Dependencies:

- `MLB-8`
- `MLB-25`

### MLB-34: Store raw Statcast records locally

Issue type: `Story`  
Priority: `P1`  
Labels: `data-ingestion`, `database`, `backend`, `mvp`

Description:

Persist raw normalized Statcast pitch records to the local database.

Acceptance criteria:

- Duplicate pitch rows are not inserted during repeated ingestion.
- Insert process can handle nullable Statcast fields.
- Ingestion logs counts for inserted, skipped, and failed rows.
- Tests cover idempotent ingestion.

Dependencies:

- `MLB-26`
- `MLB-33`

### MLB-35: Implement incremental Statcast updates

Issue type: `Story`  
Priority: `P1`  
Labels: `data-ingestion`, `backend`, `mvp`

Description:

Track ingestion state and update only missing date ranges.

Acceptance criteria:

- Ingestion state records completed date ranges.
- Re-running ingestion avoids complete redownloads.
- Failed runs are marked and can be retried.
- Documentation explains local update workflow.

Dependencies:

- `MLB-34`

---

## Epic MLB-36: MVP Game Matchups

Connect real games, probable pitchers, lineups, profiles, and matchup ranking.

### MLB-37: Generate matchup rankings for real games

Issue type: `Story`  
Priority: `P1`  
Labels: `backend`, `analytics`, `api`, `mvp`

Description:

For a selected game, determine the starting pitcher and opposing hitters, then rank hitters by matchup score.

Acceptance criteria:

- Game matchup endpoint works from real MLB game IDs.
- Probable pitcher missing state is handled gracefully.
- Missing hitter profile state is handled gracefully.
- Rankings include confidence and explanation.
- Tests cover normal and missing-data scenarios.

Dependencies:

- `MLB-17`
- `MLB-27`
- `MLB-30`
- `MLB-31`
- `MLB-35`

### MLB-38: Add missing-data and uncertainty handling

Issue type: `Story`  
Priority: `P1`  
Labels: `backend`, `frontend`, `analytics`, `mvp`

Description:

Make uncertainty visible when data is missing, stale, incomplete, or based on small samples.

Acceptance criteria:

- API responses include data availability metadata.
- Frontend displays confidence and missing-data states clearly.
- Small sample warnings are surfaced.
- Matchup score is withheld or downgraded when data is insufficient.

Dependencies:

- `MLB-37`

### MLB-39: Add MVP end-to-end test path

Issue type: `Story`  
Priority: `P1`  
Labels: `testing`, `backend`, `frontend`, `mvp`

Description:

Create an end-to-end test or smoke test that validates the MVP user path from games list to matchup detail.

Acceptance criteria:

- Test starts with seeded fixture or controlled database data.
- Test opens the games list.
- Test navigates to matchup rankings.
- Test opens a hitter detail.
- Test verifies score and explanation are displayed.

Dependencies:

- `MLB-21`
- `MLB-22`
- `MLB-37`

---

## Epic MLB-40: Testing and Quality

Protect analytics correctness with focused unit, integration, and contract tests.

### MLB-41: Add deterministic analytics unit tests

Issue type: `Story`  
Priority: `P0`  
Labels: `testing`, `analytics`, `mvp`

Description:

Add deterministic tests for parsing, aggregation, sample-size regression, matchup scoring, score normalization, and explanation generation.

Acceptance criteria:

- Tests cover pitcher profile generation.
- Tests cover hitter profile generation.
- Tests cover sample-size regression.
- Tests cover weighted matchup calculations.
- Tests cover score band boundaries.
- Tests run without external network calls.

Dependencies:

- `MLB-8`
- `MLB-9`
- `MLB-10`
- `MLB-11`
- `MLB-13`

### MLB-42: Add MLB API client tests

Issue type: `Story`  
Priority: `P1`  
Labels: `testing`, `backend`, `api`

Description:

Test MLB Stats API parsing and normalization with mocked API responses.

Acceptance criteria:

- Tests cover schedule response parsing.
- Tests cover probable pitcher extraction.
- Tests cover lineup parsing where available.
- Tests cover missing or unexpected API fields.
- No tests call the live MLB API.

Dependencies:

- `MLB-29`

### MLB-43: Add API contract tests

Issue type: `Story`  
Priority: `P1`  
Labels: `testing`, `api`, `backend`

Description:

Validate backend endpoint response shapes and error behavior.

Acceptance criteria:

- Tests cover `/games/today`.
- Tests cover `/games/{game_id}/matchups`.
- Tests cover `/matchups/{pitcher_id}/{hitter_id}`.
- Tests cover profile endpoints.
- Tests verify 404 and insufficient-data responses.

Dependencies:

- `MLB-15`
- `MLB-16`
- `MLB-17`
- `MLB-18`
- `MLB-30`

---

## Epic MLB-44: Explainability and Product UX

Make matchup results understandable and useful for baseball decision-making.

### MLB-45: Add explanation generation service

Issue type: `Story`  
Priority: `P1`  
Labels: `analytics`, `backend`, `mvp`

Description:

Generate plain-language explanation summaries from matchup result components.

Acceptance criteria:

- Explanation identifies primary pitch-type driver.
- Explanation references pitcher usage and hitter performance.
- Explanation includes uncertainty when sample size is small.
- Explanation text is generated backend-side.
- Tests cover positive, neutral, negative, and low-confidence matchups.

Dependencies:

- `MLB-13`

### MLB-46: Improve score band presentation

Issue type: `Story`  
Priority: `P1`  
Labels: `frontend`, `mvp`

Description:

Display score bands in a clear, scannable way without hiding confidence or uncertainty.

Acceptance criteria:

- Each score shows its band label.
- Confidence is visible near the score.
- Low-confidence scores are visually differentiated.
- Color treatment remains readable and accessible.

Dependencies:

- `MLB-21`
- `MLB-22`

### MLB-47: Add pitch breakdown visualization

Issue type: `Story`  
Priority: `P2`  
Labels: `frontend`, `analytics`

Description:

Add a compact visualization showing how each pitch type contributed to the matchup score.

Acceptance criteria:

- Visualization shows positive and negative pitch contributions.
- Pitcher usage is visible.
- Sample size is visible or accessible.
- View remains usable on mobile and desktop.

Dependencies:

- `MLB-22`

---

## Epic MLB-48: DevOps and Production Readiness

Prepare the application for repeatable local setup and eventual deployment.

### MLB-49: Add environment configuration

Issue type: `Task`  
Priority: `P1`  
Labels: `devops`, `backend`, `frontend`

Description:

Define environment variables for backend database URL, API configuration, frontend API URL, and local development defaults.

Acceptance criteria:

- Example environment files are provided.
- Required variables are documented.
- Backend validates required production configuration.
- Frontend can point to local backend.

Dependencies:

- `MLB-2`
- `MLB-3`

### MLB-50: Add CI checks

Issue type: `Task`  
Priority: `P1`  
Labels: `devops`, `testing`

Description:

Add continuous integration checks for backend tests, frontend type checks, frontend tests, and linting.

Acceptance criteria:

- CI runs backend tests.
- CI runs frontend type checks.
- CI runs linting where configured.
- CI does not require live external API access.

Dependencies:

- `MLB-2`
- `MLB-3`
- `MLB-41`

---

# Future Epics

## Epic MLB-51: Advanced Pitch Similarity

Priority: `P3`  
Labels: `future`, `analytics`

Description:

Move beyond pitch-type matching by comparing physical pitch characteristics such as velocity, movement, location, and pitcher handedness.

Planned work: `MLB-64` and `MLB-72`. Compare pitch similarity against the pitch-type baseline before using it in outcome probabilities.

## Epic MLB-52: Contextual Baseball Factors

Priority: `P3`  
Labels: `future`, `analytics`

Description:

Add contextual adjustments after the MVP model is validated.

Planned work: `MLB-65` through `MLB-68`, `MLB-70`, and `MLB-71`.

## Epic MLB-53: Predictive Outcome Models

Priority: `P2`  
Labels: `probability`, `analytics`

Description:

Explore probability models for specific outcomes after deterministic matchup scoring is stable.

Planned work: `MLB-55`, `MLB-58`, and `MLB-73` through `MLB-76`. Add outcome types behind the same probability interface and validate them against historical baselines.

---

# Feature Expansion Tickets

These are proposed Jira keys for planning, not existing Jira issue IDs. Keep the original pitch-type MVP definition of done intact. The fixture-based expansion slice may be built alongside MVP architecture work; live market integration waits for calibrated probabilities and an authorized feed.

## Epic MLB-54: Probability and Mock Market Architecture

Priority: `P2`  
Labels: `analytics`, `probability`, `backend`

Deliver a provider-independent path from baseball features to a mock market comparison. The flow is one-way: baseball analytics -> probability -> market comparison. No market field is allowed in a `ProbabilityModel` input.

### MLB-55: Define outcome and probability contracts

Issue type: `Story`  
Priority: `P2`  
Labels: `probability`, `analytics`, `backend`

Description: Define `ProbabilityModel` and versioned outcome contracts for hitter hit, home run, 2+ total bases, strikeout, walk, and pitcher strikeout thresholds. Start with one fixture-supported outcome; add the others incrementally.

Acceptance criteria:

- An outcome specifies player, game, event, threshold, and settlement window so model and market refer to the same event.
- A result includes probability in `[0, 1]`, model version, input-data version, and generation time.
- The interface accepts baseball features and context only; tests reject market data as model input.
- New outcome types can be registered without changing the matchup engine or existing API contracts.

Dependencies: `MLB-5`, `MLB-12`, `MLB-13`

### MLB-56: Define a separate confidence model

Issue type: `Story`  
Priority: `P2`  
Labels: `probability`, `analytics`

Description: Define `ConfidenceModel` using pitcher and hitter sample sizes, recency, lineup and starter certainty, missing inputs, and later historical calibration.

Acceptance criteria:

- Confidence is stored separately from outcome probability and includes reason codes for reductions.
- Low or missing sample data lowers confidence or suppresses an output according to an explicit rule.
- API and UI can distinguish a 32% probability at high confidence from the same probability at low confidence.

Dependencies: `MLB-11`, `MLB-38`, `MLB-55`

### MLB-57: Define immutable comparison domain models

Issue type: `Story`  
Priority: `P2`  
Labels: `database`, `backend`, `market-data`

Description: Define `ModelPrediction`, `MarketSnapshot`, and `EdgeResult` with canonical baseball IDs, provider IDs, event identity, observation times, provenance, and version fields. This ticket establishes domain contracts; persistence follows in `MLB-75` and `MLB-82`.

Acceptance criteria:

- `ModelPrediction` records model probability, confidence, version, data version, generated time, and outcome identity.
- `MarketSnapshot` records provider, external market ID, normalized outcome, yes/no prices, price basis, and observed time.
- `EdgeResult` references the exact prediction and price snapshot used; historical comparisons are not silently recalculated.
- Schema distinguishes missing price, stale price, and unmatched market.

Dependencies: `MLB-5`, `MLB-25`, `MLB-55`

### MLB-58: Implement fixture-based outcome probability

Issue type: `Story`  
Priority: `P2`  
Labels: `probability`, `analytics`, `testing`

Description: Implement an interpretable first `ProbabilityModel` for one precisely defined outcome, then expand to other hitter and pitcher outcomes once historical labels and baselines exist.

Acceptance criteria:

- Fixture Statcast data flows through profiles and matchup features into a probability in `[0, 1]`.
- Model output is deterministic for fixed inputs and declares its training or calibration data window.
- Separate overall, power, contact, strikeout, and walk matchup scores can feed matching outcomes without being presented as probabilities.
- Baseline comparison and leakage checks are recorded before an outcome is promoted beyond fixtures.

Dependencies: `MLB-9`, `MLB-10`, `MLB-13`, `MLB-55`, `MLB-69`

### MLB-59: Add market provider and normalizer interfaces with fixtures

Issue type: `Story`  
Priority: `P2`  
Labels: `market-data`, `backend`, `testing`, `read-only`

Description: Define `MarketDataProvider` (`get_events`, `get_markets`, `get_market`, `get_current_prices`) and `MarketNormalizer`; implement `MockMarketProvider` with deterministic fixture prices.

Acceptance criteria:

- Providers normalize market type, threshold, player, game, yes/no side, price basis, currency where applicable, and observation time.
- Mock provider supports unavailable, stale, and unmatched markets as well as a valid price.
- Analytics and probability code depend on neither provider-specific types nor provider availability.
- Interface exposes read-only retrieval operations only.

Dependencies: `MLB-55`, `MLB-57`

### MLB-60: Implement edge and target-price policies

Issue type: `Story`  
Priority: `P2`  
Labels: `analytics`, `market-data`, `testing`

Description: Define `EdgeEngine` and configurable `TargetPricePolicy`. The initial policy uses a minimum desired probability-point disagreement; later versions may account for uncertainty, fees, spread, liquidity, and slippage.

Acceptance criteria:

- For matched `YES` events, raw disagreement equals model probability minus normalized market probability, in percentage points when displayed.
- With probability `0.284`, market price `0.210`, and required edge `0.050`, raw edge is `+0.074` and maximum target is `0.234`.
- Negative, zero, missing, stale, and unmatched prices have explicit results; values never imply guaranteed profit.
- Policy inputs, version, price basis, and rounding rules are recorded with the result.

Dependencies: `MLB-56`, `MLB-57`, `MLB-59`

### MLB-61: Expose the mock opportunity vertical slice

Issue type: `Story`  
Priority: `P2`  
Labels: `api`, `frontend`, `market-data`

Description: Add a fixture-backed API response and frontend detail view for one modeled outcome, confidence, mock price, disagreement, target price, and structured baseball explanation.

Acceptance criteria:

- Data flows from Statcast fixture -> profiles -> matchup -> probability -> confidence -> mock price -> edge -> target -> API -> UI.
- UI labels model probability, market price, disagreement, target, confidence, and as-of time distinctly.
- Missing market data leaves baseball analysis available and hides comparison values.
- Explanations and risks derive from structured features; no arbitrary prose generation is required.

Dependencies: `MLB-16`, `MLB-22`, `MLB-23`, `MLB-45`, `MLB-58`, `MLB-59`, `MLB-60`

### MLB-62: Test the expansion vertical slice

Issue type: `Story`  
Priority: `P2`  
Labels: `testing`, `probability`, `market-data`

Description: Add deterministic unit, contract, and end-to-end tests for the new domain contracts and mock provider path.

Acceptance criteria:

- Tests cover the `0.284` / `0.210` / `0.050` example and probability-point units.
- Tests prove provider prices cannot change the same model probability for fixed baseball inputs.
- Tests cover stale price, wrong player/event/threshold, missing lineup, and low confidence.
- Tests run without live MLB, Statcast, or market calls.

Dependencies: `MLB-61`

## Epic MLB-63: Deeper Baseball Features

Priority: `P3`  
Labels: `future`, `analytics`

Add features as independently measurable components. Preserve raw hitter/pitcher profiles and keep context adjustments explainable.

### MLB-64: Prototype physical pitch similarity

Issue type: `Spike`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Define a pitch vector with type, velocity, movement, release, extension, location, and pitcher hand.
- Test nearest-neighbor or clustering approaches against pitch-type baseline using held-out data.
- Report sparse-sample behavior and whether similarity adds predictive value.

Dependencies: `MLB-8`, `MLB-13`

### MLB-65: Build location compatibility features

Issue type: `Story`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Pitcher location and hitter performance maps share documented plate-zone definitions and handedness splits.
- Compare zone-level xwOBA, whiff, hard-hit, and barrel signals with sample-size controls.
- Expose per-zone contributions and test whether the feature improves held-out outcomes.
- Compare a deterministic coordinate-clustering candidate (for example, K-means) with the zone baseline only after enough `plate_x`/`plate_z` observations exist; fit centroids on training dates only, version them, and retain zone fallback for sparse or missing coordinates.

Dependencies: `MLB-9`, `MLB-10`, `MLB-11`

### MLB-66: Add count-specific tendencies

Issue type: `Story`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Profile 0-0, ahead, behind, two-strike, three-ball, and full-count pitch use.
- Compare hitter performance in equivalent count states without conflating pitch and plate-appearance denominators.
- Sparse count splits fall back to broader rates and expose uncertainty.

Dependencies: `MLB-9`, `MLB-10`, `MLB-11`

### MLB-67: Detect pitcher arsenal changes

Issue type: `Story`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Compare season, last 30 days, and last five starts for pitch mix, velocity, movement, and release point.
- Flag new or abandoned pitches only when evidence passes a configurable sample threshold.
- Store change evidence and dates so explanations can distinguish recent identity from season average.

Dependencies: `MLB-9`, `MLB-68`

### MLB-68: Add rolling windows and recency weighting

Issue type: `Story`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Support full season, 60/30/15 days, and last N starts with explicit cutoff and timezone rules.
- Provide sample counts and regression for every window.
- Compare recency weighting against fixed windows on historical data.

Dependencies: `MLB-9`, `MLB-10`, `MLB-11`

### MLB-69: Separate matchup dimensions

Issue type: `Story`  
Priority: `P2`  
Labels: `analytics`, `probability`

Acceptance criteria:

- Return overall, power, contact, strikeout, and walk matchup scores with documented direction and scale.
- Each dimension has feature contributions and uncertainty; UI does not label scores as event probabilities.
- Existing overall score remains available for MVP clients.

Dependencies: `MLB-13`, `MLB-15`

### MLB-70: Add separate park and weather context

Issue type: `Story`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Park factors and weather observations are versioned context inputs, separate from raw player profiles.
- Missing or stale weather does not block raw matchup analysis.
- Explain and evaluate each adjustment against a context-free baseline.

Dependencies: `MLB-58`

### MLB-71: Model expected bullpen matchup

Issue type: `Spike`  
Priority: `P3`  
Labels: `future`, `analytics`

Acceptance criteria:

- Estimate starter innings and reliever mix from usage, rest, handedness, and role.
- Report starter, expected bullpen, and combined game matchup separately.
- Express uncertainty when reliever identity or starter workload is unclear.

Dependencies: `MLB-37`, `MLB-58`

### MLB-72: Show similar pitchers as evidence

Issue type: `Story`  
Priority: `P3`  
Labels: `future`, `analytics`, `frontend`

Acceptance criteria:

- Rank comparable pitchers by pitch mix, velocity, movement, release, and handedness.
- Show hitter outcomes against comparable pitchers with sample counts and dates.
- Similarity evidence is labeled as supporting context, not a guaranteed prediction.

Dependencies: `MLB-64`

## Epic MLB-73: Prediction History and Backtesting

Priority: `P2`  
Labels: `backtesting`, `probability`, `database`

Historical evaluation is a release gate for live market comparison. Preserve what the model knew at prediction time, then settle outcomes from final game data.

### MLB-74: Define outcome labels and temporal data rules

Issue type: `Story`  
Priority: `P2`  
Labels: `backtesting`, `analytics`

Acceptance criteria:

- Settlement rules match each modeled event and threshold, including void/cancelled/postponed games.
- Training, calibration, and test windows are chronological; no post-prediction data leaks into features.
- Final game data is linked to an outcome without modifying the original prediction.

Dependencies: `MLB-55`, `MLB-58`

### MLB-75: Persist model predictions and settlements

Issue type: `Story`  
Priority: `P2`  
Labels: `backtesting`, `database`

Acceptance criteria:

- Store immutable prediction probability, confidence, model/data versions, feature snapshot reference, generation time, and outcome identity.
- Store later settlement and result as separate records or fields with audit history.
- Replaying a model never overwrites what an older version predicted.

Dependencies: `MLB-26`, `MLB-57`, `MLB-74`

### MLB-76: Measure calibration and predictive quality

Issue type: `Story`  
Priority: `P2`  
Labels: `backtesting`, `analytics`, `testing`

Acceptance criteria:

- Report Brier score, log loss, reliability/calibration bins, and sample counts by outcome and model version.
- Break down results by confidence and, when available, market and edge bucket.
- Compare to a documented baseline on held-out dates and record agreed release thresholds before enabling a live provider.

Dependencies: `MLB-74`, `MLB-75`

### MLB-77: Analyze closing-price movement separately

Issue type: `Story`  
Priority: `P3`  
Labels: `backtesting`, `market-data`

Acceptance criteria:

- Store observed, target, and closing price with explicit market cutoff and price basis.
- Report market movement separately from whether the baseball event occurred.
- Missing or sparse market snapshots produce an incomplete-history status rather than a fabricated closing price.

Dependencies: `MLB-76`, `MLB-82`

## Epic MLB-78: Authorized Market Data

Priority: `P2`  
Labels: `market-data`, `read-only`

Treat DraftKings Predictions as a possible provider, distinct from DraftKings Sportsbook. Do not assume website visibility implies API access. The product must work without a live provider.

### MLB-79: Investigate authorized market feeds

Issue type: `Spike`  
Priority: `P2`  
Labels: `market-data`, `api`

Acceptance criteria:

- Review current official provider documentation for supported MLB market-data access, authentication, rate limits, and permitted use.
- Record supported event types, price semantics, update cadence, and availability for DraftKings Predictions or an alternative.
- If no authorized reliable feed is found, document the finding and leave the real provider disabled; do not scrape or use undocumented endpoints.

Dependencies: `MLB-59`, `MLB-76`

### MLB-80: Map provider entities to canonical MLB identities

Issue type: `Story`  
Priority: `P2`  
Labels: `market-data`, `database`

Acceptance criteria:

- Store provider player, team, game, and market IDs linked to canonical MLB identities when verified.
- Matching uses IDs and explicit reconciliation; names alone cannot automatically approve a match.
- Ambiguous or unmapped events are excluded from edge calculations and surfaced for review.

Dependencies: `MLB-25`, `MLB-57`, `MLB-79`

### MLB-81: Add an authorized live provider behind a flag

Issue type: `Story`  
Priority: `P2`  
Labels: `market-data`, `api`, `read-only`

Acceptance criteria:

- Implement only the supported read-only feed identified in `MLB-79`; use the same normalized contract as the mock provider.
- Respect documented auth, rate limits, retries, and error behavior; provider failure never blocks baseball analysis.
- A disabled flag leaves fixture/mock flows usable, and no transaction or account-funds operations exist.

Dependencies: `MLB-76`, `MLB-79`, `MLB-80`, `MLB-82`

### MLB-82: Persist append-only market snapshots

Issue type: `Story`  
Priority: `P2`  
Labels: `market-data`, `database`, `backtesting`

Acceptance criteria:

- Every retrieved price is timestamped, linked to provider and normalized market, and appended rather than overwriting history.
- Store yes/no prices, price basis, observed time, and ingestion time; distinguish repeated observations from changed quotes.
- Backtests join a prediction only to prices observed no later than its comparison time.

Dependencies: `MLB-26`, `MLB-57`, `MLB-59`

## Epic MLB-83: Daily Decision Support

Priority: `P2`  
Labels: `frontend`, `market-data`, `read-only`

Show useful baseball analysis even when no market provider is configured. Market comparison is informational and never submits a position.

### MLB-84: Build daily opportunity scanner

Issue type: `Story`  
Priority: `P2`  
Labels: `frontend`, `api`, `market-data`

Acceptance criteria:

- Today's games, probable starters, top hitter/pitcher matchups, and available model/market disagreements appear together.
- Ranking uses configurable edge, confidence, sample-quality, and market-quality weights; the formula and as-of time are visible.
- Missing or stale prices and uncertain starters are clearly represented and do not create false opportunities.

Dependencies: `MLB-30`, `MLB-37`, `MLB-61`, `MLB-76`; live prices additionally require `MLB-81`.

### MLB-85: Add filters and structured opportunity detail

Issue type: `Story`  
Priority: `P2`  
Labels: `frontend`, `api`, `market-data`

Acceptance criteria:

- Filter by game, team, player, market type, hitter/pitcher, minimum edge, confidence, and sample size.
- Detail shows probability, confidence, price, edge, target, baseball drivers, risks, and data freshness.
- Reasons come from structured model features; wording says model-market disagreement, not guaranteed profit.

Dependencies: `MLB-45`, `MLB-84`

### MLB-86: Show price history with model overlay

Issue type: `Story`  
Priority: `P3`  
Labels: `frontend`, `market-data`

Acceptance criteria:

- Chart timestamped market prices and optionally overlay the model probability with its generation time.
- Distinguish historical quotes from the latest actionable price and label gaps in data.
- Empty history has a clear state without suppressing baseball analysis.

Dependencies: `MLB-75`, `MLB-82`, `MLB-84`

### MLB-87: Design informational alerts

Issue type: `Spike`  
Priority: `P3`  
Labels: `future`, `market-data`, `read-only`

Acceptance criteria:

- Specify thresholds for price, edge, and confidence with freshness and deduplication rules.
- Alert design surfaces opportunities for manual review only; it has no trade execution path.
- Delivery mechanism is selected only after daily scanner and provider behavior are validated.

Dependencies: `MLB-84`, `MLB-86`

## Expansion Release Gates

1. **Mock slice (`MLB-55`-`MLB-62`, `MLB-69`):** Fixed baseball inputs yield the same model probability regardless of mock price. The fixture example returns edge `+0.074` and target `0.234`, and the API/UI display both with confidence and provenance.
2. **Historical evaluation (`MLB-74`-`MLB-76`):** Outcome labels and prediction snapshots are reproducible; held-out Brier score, log loss, calibration, and baseline comparisons meet thresholds agreed before live integration.
3. **Live data (`MLB-79`-`MLB-82`):** A documented authorized feed exists, entity and market matching are verified, and snapshots carry timestamps and price basis. Otherwise keep the mock provider and label fixture opportunities clearly.
4. **Daily product (`MLB-84`-`MLB-86`):** Scanner handles unavailable or stale data and retains game analysis without market data. All market features remain read-only.

## Expansion Implementation Order

1. `MLB-55`, `MLB-56`, `MLB-57`, `MLB-69`: Outcome, confidence, snapshot, and matchup-dimension contracts.
2. `MLB-58`, `MLB-59`, `MLB-60`: First fixture probability, mock provider, edge, and target policy.
3. `MLB-61`, `MLB-62`: Full fixture-to-frontend path and tests.
4. `MLB-74`, `MLB-75`, `MLB-76`: Historical labels, immutable predictions, and calibration gate.
5. `MLB-79`, `MLB-80`, `MLB-82`: Authorized-feed research, identity mapping, and append-only snapshots.
6. `MLB-81`, `MLB-84`, `MLB-85`: Conditional live provider and daily opportunity product.
7. `MLB-64`-`MLB-68`, `MLB-70`-`MLB-72`, `MLB-77`, `MLB-86`, `MLB-87`: Evidence-driven baseball and history enhancements.

---

# Recommended Implementation Order

1. `MLB-2`: Scaffold backend project
2. `MLB-3`: Scaffold frontend project
3. `MLB-5`: Define primary domain models
4. `MLB-7`: Create fixture Statcast dataset
5. `MLB-8`: Implement Statcast parsing layer
6. `MLB-9`: Build pitcher profile generator
7. `MLB-10`: Build hitter profile generator
8. `MLB-11`: Implement sample-size regression
9. `MLB-12`: Define matchup model interface
10. `MLB-13`: Implement weighted matchup model
11. `MLB-15`: Create matchup API schemas
12. `MLB-16`: Add fixture-backed matchup endpoint
13. `MLB-17`: Add fixture-backed game matchup endpoint
14. `MLB-23`: Create shared frontend API client and types
15. `MLB-20`: Build games list page
16. `MLB-21`: Build game matchup rankings view
17. `MLB-22`: Build hitter matchup detail view
18. `MLB-41`: Add deterministic analytics unit tests
19. `MLB-25`: Design initial database schema
20. `MLB-29`: Build MLB Stats API client interface
21. `MLB-33`: Build Statcast ingestion interface
22. `MLB-37`: Generate matchup rankings for real games
23. `MLB-38`: Add missing-data and uncertainty handling
24. `MLB-39`: Add MVP end-to-end test path

---

# MVP Definition of Done

The MVP is complete when:

- A user can select today's games or a selected date.
- The app can identify probable starting pitchers when available.
- Historical Statcast data is stored locally.
- Pitcher arsenals are generated from Statcast data.
- Hitter pitch-type profiles are generated from Statcast data.
- Hitter profiles are split by pitcher handedness.
- Matchup scores are calculated using an interpretable weighted model.
- Small samples are regressed toward league average.
- Hitters are ranked for each game.
- Each matchup includes a clear explanation and confidence value.
- Backend analytics are covered by deterministic unit tests.
- External API calls are mocked in automated tests.
- The frontend displays game list, matchup rankings, and matchup details.

---

# Key Assumptions

- Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, and Pandas or Polars are acceptable backend choices.
- SQLite may be used for local development, but schema decisions should remain PostgreSQL-compatible.
- React and TypeScript are acceptable frontend choices.
- pybaseball may be used initially for Statcast retrieval.
- Fixture data should be used first to validate architecture before live external data is integrated.
- MLB lineups may be incomplete or unavailable before games, so the product must represent uncertainty.

# Key Technical Risks

- MLB Stats API response shapes may differ by game state, date, or endpoint.
- Statcast ingestion can be slow, rate-limited, or temporarily unavailable.
- Small samples can mislead users if confidence and regression are not handled carefully.
- Player identity mapping between MLB Stats API and Statcast data must be reliable.
- Pitch-type labels and classifications may change over time.
- Calculating plate appearances from pitch-level data requires care.
- Frontend should not duplicate analytics logic, or scores may drift from backend calculations.
- Premature advanced modeling could slow MVP delivery before the interpretable baseline is validated.
