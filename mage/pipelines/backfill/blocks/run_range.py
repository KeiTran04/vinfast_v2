from __future__ import annotations

from datetime import datetime, timedelta


def iter_dates(start: str, end: str) -> list[str]:
    s = datetime.strptime(start, "%Y-%m-%d").date()  # noqa: DTZ007 - date-only batch param
    e = datetime.strptime(end, "%Y-%m-%d").date()  # noqa: DTZ007 - date-only batch param
    out, d = [], s
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def main(start_date: str, end_date: str, runner) -> None:
    for ds in iter_dates(start_date, end_date):
        runner(ds)
