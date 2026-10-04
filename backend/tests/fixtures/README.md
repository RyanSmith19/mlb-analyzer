# Synthetic Statcast fixture

`app/data/statcast_pitches.csv` contains 20 invented pitch-level rows sampled from two invented games. The IDs are deliberately outside real MLB game/player ranges. This packaged file is a deterministic test and local API input, not a live or historical MLB extract.

| ID | Fixture role | Handedness |
| --- | --- | --- |
| 900101 | Pitcher A | Right |
| 900102 | Pitcher B | Left |
| 900201 | Hitter A | Right |
| 900202 | Hitter B | Left |

Game `9900001` has Pitcher A facing both hitters on July 1; game `9900002` has Pitcher B facing the same hitters on July 2. These are selected appearances, not complete game logs. Each hitter has two sampled plate appearances against each pitcher, at least nine at-bat slots apart, with two or three pitches per appearance. `game_pk` plus `at_bat_number` identifies a plate appearance; only its final pitch has an `events` value. Empty launch and estimated-wOBA fields mean the pitch was not a ball in play. The movement and velocity fields use familiar Statcast column names, with `pfx_x`/`pfx_z` in feet.

The fixture game registry assigns both hitters to Fixture Visitors (`900002`). Pitcher A belongs to Fixture Hosts (`900001`) in game `9900001`; Pitcher B belongs to Fixture Southpaws (`900003`) in game `9900002`. These teams and IDs are invented game-summary metadata, not columns inferred from Statcast.

## Expected aggregates

| Pitcher | Hand | Pitch type | Pitches | Usage | Mean velocity (mph) | Swinging misses |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 900101 | R | FF | 5 | 0.50 | 95.0 | 1 |
| 900101 | R | SL | 5 | 0.50 | 84.8 | 1 |
| 900102 | L | FF | 5 | 0.50 | 92.0 | 0 |
| 900102 | L | CH | 5 | 0.50 | 82.0 | 1 |

Each pitcher throws five pitches to a right-handed batter and five to a left-handed batter. Pitcher A's right-handed split is three FF/two SL; its left-handed split is two FF/three SL. Pitcher B's right-handed split is two FF/three CH; its left-handed split is three FF/two CH. There are eight completed plate appearances: six balls in play and two three-strike strikeouts. Both pitchers have at least one fastball ball in play.

| Hitter | Pitcher hand | Pitches | PA | Outcomes | BIP mean estimated wOBA | Hard-hit BIP (95+ mph) |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| 900201 | R | 5 | 2 | Strikeout, single | 0.700 | 1/1 |
| 900201 | L | 5 | 2 | Home run, strikeout | 0.970 | 1/1 |
| 900202 | R | 5 | 2 | Double, field out | 0.485 | 1/2 |
| 900202 | L | 5 | 2 | Single, field out | 0.420 | 1/2 |

The xwOBA averages use only rows with `estimated_woba_using_speedangle`, not all pitches or plate appearances. For example, Hitter B versus the right-hander is `(0.850 + 0.120) / 2 = 0.485`. This fixture is intentionally small; it does not define league averages or sufficient sample size for real baseball conclusions.
