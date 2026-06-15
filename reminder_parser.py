import re
import unicodedata
from datetime import datetime, timedelta


WEEKDAY_MAP = {
    'segunda': 0,
    'segunda-feira': 0,
    'terca': 1,
    'terça': 1,
    'terca-feira': 1,
    'terça-feira': 1,
    'quarta': 2,
    'quarta-feira': 2,
    'quinta': 3,
    'quinta-feira': 3,
    'sexta': 4,
    'sexta-feira': 4,
    'sabado': 5,
    'sábado': 5,
    'domingo': 6,
}

TITLE_CLEANUP_PATTERNS = [
    r'\bdepois de amanhã\b',
    r'\bdepois de amanha\b',
    r'\bamanhã\b',
    r'\bamanha\b',
    r'\bhoje\b',
    r'\bsegunda(?:-feira)?\b',
    r'\bterça(?:-feira)?\b',
    r'\bterca(?:-feira)?\b',
    r'\bquarta(?:-feira)?\b',
    r'\bquinta(?:-feira)?\b',
    r'\bsexta(?:-feira)?\b',
    r'\bsábado\b',
    r'\bsabado\b',
    r'\bdomingo\b',
    r'\bdia\s+\d{1,2}\b',
    r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b',
    r'\b\d{1,2}\s+\d{1,2}(?:\s+\d{2,4})?\b',
    r'\b(?:às|as)\s+\d{1,2}(?::\d{2}|\s*h(?:\s*\d{1,2})?)?(?:\s*(?:horas?|hrs?|hr))?\b',
    r'\b\d{1,2}:\d{2}\b',
    r'\b\d{1,2}\s*h(?:\s*\d{2})?\b',
    r'\b\d{1,2}\s*(?:horas?|hrs?|hr)\b',
]


def _normalize_spaces(text):
    return ' '.join((text or '').strip().split())


def _strip_accents(text):
    return ''.join(
        char for char in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(char)
    )


def _extract_time(normalized_text):
    explicit = re.search(
        r'\b(?:as)\s+(\d{1,2})(?::(\d{2})|\s*h(?:\s*(\d{1,2}))?)?(?:\s*(?:horas?|hrs?|hr))?\b',
        normalized_text
    )
    if explicit:
        hour = int(explicit.group(1))
        minute = explicit.group(2) or explicit.group(3) or '0'
        return hour, int(minute)

    compact = re.search(
        r'\b(\d{1,2})(?::(\d{2})|\s*h(?:\s*(\d{1,2}))?|\s*(?:horas?|hrs?|hr))\b',
        normalized_text
    )
    if compact:
        hour = int(compact.group(1))
        minute = compact.group(2) or compact.group(3) or '0'
        return hour, int(minute)

    return None


def _next_weekday(reference, target_weekday):
    delta = (target_weekday - reference.weekday()) % 7
    return reference if delta == 0 else reference + timedelta(days=delta)


def _extract_date(normalized_text, now):
    if 'depois de amanha' in normalized_text:
        return now + timedelta(days=2)
    if 'amanha' in normalized_text:
        return now + timedelta(days=1)
    if 'hoje' in normalized_text:
        return now

    explicit_date = re.search(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', normalized_text)
    if explicit_date:
        day = int(explicit_date.group(1))
        month = int(explicit_date.group(2))
        raw_year = explicit_date.group(3)
        if raw_year:
            year = int(raw_year)
            if year < 100:
                year += 2000
        else:
            year = now.year
            if (month, day) < (now.month, now.day):
                year += 1

        try:
            return now.replace(year=year, month=month, day=day)
        except ValueError:
            return None

    spaced_date = re.search(r'\b(\d{1,2})\s+(\d{1,2})(?:\s+(\d{2,4}))?\b', normalized_text)
    if spaced_date:
        day = int(spaced_date.group(1))
        month = int(spaced_date.group(2))
        raw_year = spaced_date.group(3)

        if 1 <= month <= 12:
            if raw_year:
                year = int(raw_year)
                if year < 100:
                    year += 2000
            else:
                year = now.year
                if (month, day) < (now.month, now.day):
                    year += 1

            try:
                return now.replace(year=year, month=month, day=day)
            except ValueError:
                return None

    day_only = re.search(r'\bdia\s+(\d{1,2})\b', normalized_text)
    if day_only:
        day = int(day_only.group(1))
        month = now.month
        year = now.year

        while True:
            try:
                candidate = now.replace(year=year, month=month, day=day)
                if candidate.date() < now.date():
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
                    continue
                return candidate
            except ValueError:
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1

    for label, weekday in WEEKDAY_MAP.items():
        if re.search(rf'\b{re.escape(label)}\b', normalized_text):
            return _next_weekday(now, weekday)

    return None


def _clean_title(original_text):
    cleaned = original_text
    for pattern in TITLE_CLEANUP_PATTERNS:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'\b(?:às|as|em|no|na)\b', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\-,;:.()]+', ' ', cleaned)
    cleaned = _normalize_spaces(cleaned)
    return cleaned or original_text


def parse_reminder_text(reminder_text, now=None):
    now = now or datetime.now()
    original = _normalize_spaces(reminder_text)
    normalized = _strip_accents(original.lower())

    due_base = _extract_date(normalized, now)
    time_parts = _extract_time(normalized)

    due = None
    if due_base:
        hour, minute = time_parts if time_parts else (9, 0)
        due = due_base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    elif time_parts:
        hour, minute = time_parts
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due < now:
            due += timedelta(days=1)

    return {
        'reminder_text': original,
        'title': _clean_title(original)[:200],
        'due': due,
    }
