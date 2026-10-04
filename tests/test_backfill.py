# tests/test_backfill.py
from mage.pipelines.backfill.blocks.run_range import iter_dates


def test_iter_dates_range():
    assert iter_dates("2026-08-10", "2026-08-12") == ["2026-08-10", "2026-08-11", "2026-08-12"]


def test_iter_dates_single():
    assert iter_dates("2026-08-10", "2026-08-10") == ["2026-08-10"]
