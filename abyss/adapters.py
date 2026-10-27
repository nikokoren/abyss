import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
from .network import read_small

UTC = timezone.utc


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)


def discover(source, now=None):
    """Return newest completed candidate. Never treat publication time as capture time."""
    if source['adapter'] == 'direct':
        stamp = source.get('recorded_at')
        if stamp:
            parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('Recording timestamps must include a timezone')
        return {'url': source['video_url'], 'recorded_at': stamp}
    if source['adapter'] != 'ooi_directory':
        raise ValueError('No adapter for source')
    now = now or datetime.now(UTC)
    failures = []
    for days in range(source.get('lookback_days', 14)):
        day = now - timedelta(days=days)
        directory = urljoin(source['base_url'], day.strftime('%Y/%m/%d/'))
        try:
            parser = Links()
            parser.feed(read_small(directory, source['allowed_hosts']).decode('utf-8'))
        except Exception as exc:
            failures.append(type(exc).__name__)
            continue
        candidates = []
        for link in parser.links:
            match = re.fullmatch(r'CAMHDA301-(\d{8}T\d{6})\.mp4', link)
            if not match:
                continue
            try:
                stamp = datetime.strptime(match[1], '%Y%m%dT%H%M%S').replace(tzinfo=UTC)
            except ValueError:
                continue
            if stamp.date() == day.date() and stamp <= now - timedelta(minutes=60):
                candidates.append((stamp, urljoin(directory, link)))
        if candidates:
            stamp, url = max(candidates)
            return {'url': url, 'recorded_at': stamp.isoformat()}
    raise RuntimeError(f'No completed recordings in lookback window ({len(failures)} directory failures)')
