"""Date and label helpers for monthly release tickets."""

from __future__ import annotations

from datetime import date, timedelta

import config


def month_number(month_name: str) -> int:
    """January → 1."""
    return list(config.RELEASE_MONTHS).index(month_name) + 1


def default_processing_days(year: int, month_name: str) -> tuple[date, date, date]:
    """First Wed → Thu → Sat in the selected month/year."""
    month = month_number(month_name)
    for day in range(1, 32):
        try:
            wed = date(year, month, day)
        except ValueError:
            break
        if wed.weekday() == 2:
            thu = wed + timedelta(days=1)
            sat = wed + timedelta(days=3)
            return wed, thu, sat
    return date(year, month, 10), date(year, month, 11), date(year, month, 13)


def quarter_label(release_code: str, quarter: str) -> str:
    """e.g. R26 + Q2 → R26Q2."""
    return f"{release_code.strip()}{quarter.strip()}"


def title_date_range(day_wed: date, day_thu: date, day_sat: date) -> str:
    """Title segment: June/10 - June/13, 2026 (first → last chronologically)."""
    days = sorted([day_wed, day_thu, day_sat])
    first, last = days[0], days[-1]
    return f"{first.strftime('%B')}/{first.day} - {last.strftime('%B')}/{last.day}, {last.year}"


def processing_date_label(d: date) -> str:
    """Mail processing line: Mar/11, 2026."""
    return f"{d.strftime('%b')}/{d.day}, {d.year}"


def release_document_title(release_code: str, month: str, date_range: str) -> str:
    """R26 June Release document (June/10 - June/13, 2026)."""
    return f"{release_code} {month} Release document ({date_range})"


def form_generator_query(backup_suffix: str) -> str:
    suffix = backup_suffix.strip() or "SUFFIX"
    return f"CREATE TABLE CLIENT_XMLS_BKP_{suffix} SELECT * FROM CLIENT_XMLS;"
