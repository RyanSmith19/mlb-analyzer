import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


FIXTURE = Path(__file__).parent / "fixtures" / "statcast_pitches.csv"


def fixture_rows() -> list[dict[str, str]]:
    with FIXTURE.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_fixture_has_complete_pitch_and_plate_appearance_keys() -> None:
    rows = fixture_rows()
    assert len(rows) == 20
    assert all(None not in row and all(value is not None for value in row.values()) for row in rows)
    assert {row["game_pk"] for row in rows} == {"9900001", "9900002"}
    assert {row["p_throws"] for row in rows} == {"R", "L"}
    assert {row["stand"] for row in rows} == {"R", "L"}
    assert len({(row["game_pk"], row["at_bat_number"], row["pitch_number"]) for row in rows}) == len(rows)

    appearances = defaultdict(list)
    for row in rows:
        appearances[(row["game_pk"], row["at_bat_number"])].append(row)
    assert len(appearances) == 8
    for pitches in appearances.values():
        assert [int(row["pitch_number"]) for row in pitches] == list(range(1, len(pitches) + 1))
        assert len(pitches) in (2, 3)
        assert all(row["events"] == "" for row in pitches[:-1])
        assert pitches[-1]["events"] != ""
        if pitches[-1]["events"] == "strikeout":
            assert [row["description"] for row in pitches] == ["called_strike", "foul", "swinging_strike"]

    for game_pk in ("9900001", "9900002"):
        for batter in ("900201", "900202"):
            at_bats = sorted({int(row["at_bat_number"]) for row in rows if row["game_pk"] == game_pk and row["batter"] == batter})
            assert len(at_bats) == 2
            assert at_bats[1] - at_bats[0] >= 9


def test_fixture_pitch_mix_velocity_and_whiffs_match_documented_values() -> None:
    rows = fixture_rows()
    expected = {
        ("900101", "FF"): (5, 95.0, 1),
        ("900101", "SL"): (5, 84.8, 1),
        ("900102", "FF"): (5, 92.0, 0),
        ("900102", "CH"): (5, 82.0, 1),
    }
    for key, (count, velocity, whiffs) in expected.items():
        sample = [row for row in rows if (row["pitcher"], row["pitch_type"]) == key]
        assert len(sample) == count
        assert mean(float(row["release_speed"]) for row in sample) == velocity
        assert sum(row["description"] == "swinging_strike" for row in sample) == whiffs
        assert count / sum(row["pitcher"] == key[0] for row in rows) == 0.5

    expected_splits = {
        ("900101", "R"): {"FF": 3, "SL": 2},
        ("900101", "L"): {"FF": 2, "SL": 3},
        ("900102", "R"): {"FF": 2, "CH": 3},
        ("900102", "L"): {"FF": 3, "CH": 2},
    }
    for (pitcher, batter_side), pitch_counts in expected_splits.items():
        split = [row for row in rows if row["pitcher"] == pitcher and row["stand"] == batter_side]
        assert len(split) == 5
        assert Counter(row["pitch_type"] for row in split) == pitch_counts

    assert {row["pitcher"] for row in rows if row["pitch_type"] == "FF" and row["launch_speed"]} == {"900101", "900102"}


def test_fixture_hitter_outcomes_and_nullable_launch_metrics() -> None:
    rows = fixture_rows()
    expected = {
        ("900201", "R"): ({"strikeout", "single"}, 0.700, (1, 1)),
        ("900201", "L"): ({"home_run", "strikeout"}, 0.970, (1, 1)),
        ("900202", "R"): ({"double", "field_out"}, 0.485, (1, 2)),
        ("900202", "L"): ({"single", "field_out"}, 0.420, (1, 2)),
    }
    for key, (outcomes, xwoba, hard_hit) in expected.items():
        sample = [row for row in rows if (row["batter"], row["p_throws"]) == key]
        batted = [row for row in sample if row["launch_speed"]]
        assert len(sample) == 5
        assert {row["events"] for row in sample if row["events"]} == outcomes
        assert mean(float(row["estimated_woba_using_speedangle"]) for row in batted) == xwoba
        assert (sum(float(row["launch_speed"]) >= 95 for row in batted), len(batted)) == hard_hit

    assert sum(bool(row["launch_speed"]) for row in rows) == 6
    assert all(bool(row["launch_speed"]) == bool(row["launch_angle"]) == bool(row["estimated_woba_using_speedangle"]) for row in rows)
