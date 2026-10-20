"""Hora peninsular española (Europe/Madrid) sin base de datos de zonas horarias.

Python en Windows no trae tzdata, así que aplicamos la regla de la UE:
horario de verano (UTC+2) desde el último domingo de marzo a las 01:00 UTC
hasta el último domingo de octubre a las 01:00 UTC; el resto del año, UTC+1.
"""
from datetime import date, datetime, time, timedelta, timezone

CET = timezone(timedelta(hours=1))
CEST = timezone(timedelta(hours=2))
UTC = timezone.utc
HOUR = timedelta(hours=1)


def _last_sunday(year, month):
    first_next = date(year + (month == 12), month % 12 + 1, 1)
    d = first_next - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def dst_bounds(year):
    """Instantes UTC de inicio y fin del horario de verano de ese año."""
    start = datetime.combine(_last_sunday(year, 3), time(1), tzinfo=UTC)
    end = datetime.combine(_last_sunday(year, 10), time(1), tzinfo=UTC)
    return start, end


def offset_at(instant):
    u = instant.astimezone(UTC)
    start, end = dst_bounds(u.year)
    return CEST if start <= u < end else CET


def to_madrid(instant):
    return instant.astimezone(offset_at(instant))


def now_madrid():
    return to_madrid(datetime.now(UTC))


def local_midnight(day):
    """Medianoche local de `day` (nunca cae en un cambio de hora)."""
    naive = datetime.combine(day, time(0))
    for tz in (CET, CEST):
        candidate = naive.replace(tzinfo=tz)
        if offset_at(candidate) == tz:
            return candidate
    raise ValueError(day)


def day_hours(day):
    """Inicio de cada hora del día local `day`: 23, 24 o 25 instantes."""
    t = local_midnight(day).astimezone(UTC)
    end = local_midnight(day + timedelta(days=1)).astimezone(UTC)
    out = []
    while t < end:
        out.append(to_madrid(t))
        t += HOUR
    return out


def parse_iso(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
