"""Date helpers, Wednesday generation, and hotfix branch naming."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Iterator

from dateutil.relativedelta import relativedelta


def quarter_for_date(d: date) -> int:
    """Calendar quarter: Q1 Jan–Mar, Q2 Apr–Jun, Q3 Jul–Sep, Q4 Oct–Dec."""
    return (d.month - 1) // 3 + 1


def quarter_month_range(quarter: int) -> tuple[int, int]:
    """First and last calendar month numbers (1–12) for the given quarter."""
    start_month = 3 * (quarter - 1) + 1
    return start_month, start_month + 2


def wednesdays_in_calendar_quarter(d: date) -> list[date]:
    """All Wednesdays in the same calendar quarter as ``d``."""
    q = quarter_for_date(d)
    y = d.year
    sm, em = quarter_month_range(q)
    out: list[date] = []
    for month in range(sm, em + 1):
        out.extend(wednesdays_in_month(y, month))
    return out


def hotfix_week_number_in_quarter(hotfix_date: date, skip_leading: int = 0) -> int | None:
    """
    Branch suffix N for the selected hotfix Wednesday: position in the quarter's Wednesday
    list (1-based), minus ``skip_leading`` leading Wednesdays that are not numbered.

    Returns None if this Wednesday falls before numbering starts (e.g. skip_leading excludes it).
    """
    weds = wednesdays_in_calendar_quarter(hotfix_date)
    if hotfix_date not in weds:
        return None
    ordinal = weds.index(hotfix_date) + 1
    n = ordinal - skip_leading
    if n < 1:
        return None
    return n


def year_suffix_two_digit(d: date) -> str:
    return f"{d.year % 100:02d}"


def hotfix_prefix_for_date(hotfix_date: date) -> str:
    """e.g. hotfix_r26q2 for 2026-04-15."""
    yy = year_suffix_two_digit(hotfix_date)
    q = quarter_for_date(hotfix_date)
    return f"hotfix_r{yy}q{q}"


def hotfix_branch_regex(prefix: str) -> re.Pattern[str]:
    """Match hotfix_rYYqQ.N (N is one or more digits)."""
    escaped = re.escape(prefix)
    return re.compile(rf"^{escaped}\.(\d+)$")


def parse_hotfix_sequence(branch_name: str, prefix: str) -> int | None:
    m = hotfix_branch_regex(prefix).match(branch_name)
    if not m:
        return None
    return int(m.group(1))


def max_hotfix_sequence(branch_names: list[str], prefix: str) -> int | None:
    seqs = [s for n in branch_names if (s := parse_hotfix_sequence(n, prefix)) is not None]
    return max(seqs) if seqs else None


def release_branch_name(release_live_date: date) -> str:
    """
    release_monthYY e.g. 2026-04-08 -> release_april26
    Uses full English month name, lowercase.
    """
    month = release_live_date.strftime("%B").lower()
    yy = year_suffix_two_digit(release_live_date)
    return f"release_{month}{yy}"


def release_branch_name_day_short(release_live_date: date) -> str:
    """e.g. 2026-05-06 -> release_6may26 (day + short month + yy)."""
    months = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    m = months[release_live_date.month - 1]
    yy = year_suffix_two_digit(release_live_date)
    return f"release_{release_live_date.day}{m}{yy}"


def release_branch_display_name(
    release_live_date: date,
    override: str | None,
    naming: str,
) -> str:
    """
    Canonical release branch ref for UI and rules.

    ``naming``: ``\"full_month\"`` (release_april26) or ``\"day_short_month\"`` (release_6may26).
    """
    o = (override or "").strip()
    if o:
        return o
    if naming == "day_short_month":
        return release_branch_name_day_short(release_live_date)
    return release_branch_name(release_live_date)


def wednesdays_in_month(year: int, month: int) -> list[date]:
    """All Wednesdays in the given calendar month."""
    _, last_day = calendar.monthrange(year, month)
    out: list[date] = []
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        if d.weekday() == 2:  # Wednesday
            out.append(d)
    return out


def upcoming_wednesdays(today: date | None = None, months_ahead: int = 1) -> list[date]:
    """
    Wednesdays in the current month and the next `months_ahead` months (inclusive span).
    Default: current + next month.
    """
    today = today or date.today()
    seen: set[date] = set()
    ordered: list[date] = []
    for i in range(months_ahead + 1):
        ref = today + relativedelta(months=i)
        for w in wednesdays_in_month(ref.year, ref.month):
            if w not in seen:
                seen.add(w)
                ordered.append(w)
    return sorted(ordered)


def date_in_freeze(hotfix_date: date, freeze_start: date | None, freeze_end: date | None) -> bool:
    if freeze_start is None or freeze_end is None:
        return False
    return freeze_start <= hotfix_date <= freeze_end


def format_date_display(d: date) -> str:
    return d.isoformat()
