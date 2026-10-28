import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from .network import read_small, classify_failure

UTC = timezone.utc


class NoFreshRecordings(RuntimeError):
    failure_category = 'discovery_no_fresh_recordings'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)


def directory_recordings(source, day):
    directory = urljoin(source['base_url'], day.strftime('%Y/%m/%d/'))
    parser = Links()
    parser.feed(read_small(directory, source['allowed_hosts']).decode('utf-8'))
    records = {}
    parent = urlsplit(directory)
    for link in parser.links:
        url = urljoin(directory, link)
        parsed = urlsplit(url)
        if (parsed.scheme, parsed.netloc) != (parent.scheme, parent.netloc) or parsed.query or parsed.fragment:
            continue
        if parsed.path.rsplit('/', 1)[0] + '/' != parent.path:
            continue
        filename = parsed.path.rsplit('/', 1)[-1]
        image = source['adapter'] == 'ooi_image_directory'
        if image:
            camera = re.escape(source['camera_code'])
            pattern = camera + r'_[0-9.]+_(\d{8}T\d{6})_UTC\.(?:jpg|png)'
        else:
            pattern = r'CAMHDA301-(\d{8}T\d{6})\.mp4'
        match = re.fullmatch(pattern, filename)
        if not match:
            continue
        try:
            stamp = datetime.strptime(match[1], '%Y%m%dT%H%M%S').replace(tzinfo=UTC)
        except ValueError:
            continue
        if stamp.date() == day.date():
            records[url] = {'url': url, 'recorded_at': stamp.isoformat()}
            if image:
                records[url]['media_type'] = 'image'
    return sorted(records.values(), key=lambda r: r['recorded_at'], reverse=True)


def discover_many(source, now=None, limit=3, *, min_spacing_seconds=0, exclude_urls=(), recorded_after=None):
    """Newest eligible recordings, including across UTC date boundaries."""
    if not 1 <= limit <= 12:
        raise ValueError('Recording count must be 1..12')
    if not 0 <= min_spacing_seconds <= 86400:
        raise ValueError('Recording spacing must be 0..86400 seconds')
    excluded = set(exclude_urls)
    after = datetime.fromisoformat(recorded_after.replace('Z', '+00:00')) if recorded_after else None
    if after and after.tzinfo is None:
        raise ValueError('Fresh-recording cutoff needs a timezone')
    if source['adapter'] == 'direct':
        stamp = source.get('recorded_at')
        if stamp:
            parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('Recording timestamps must include a timezone')
        if source['video_url'] in excluded or (after and (not stamp or parsed <= after)):
            raise NoFreshRecordings('The direct recording has already been reviewed')
        return [{'url': source['video_url'], 'recorded_at': stamp}]
    if source['adapter'] not in {'ooi_directory', 'ooi_image_directory'}:
        raise ValueError('No adapter for source')
    now = now or datetime.now(UTC)
    cutoff = (now - timedelta(minutes=source.get('completion_delay_minutes', 60))).isoformat()
    candidates, failures, directories_read = [], [], 0
    def spaced(records):
        selected = []
        for record in sorted(records, key=lambda r: r['recorded_at'], reverse=True):
            stamp = datetime.fromisoformat(record['recorded_at'])
            if not selected or (datetime.fromisoformat(selected[-1]['recorded_at']) - stamp).total_seconds() >= min_spacing_seconds:
                selected.append(record)
            if len(selected) == limit:
                break
        return selected
    for days in range(source.get('lookback_days', 14)):
        if after and (now - timedelta(days=days)).date() < after.date():
            break
        try:
            recordings = directory_recordings(source, now - timedelta(days=days))
            directories_read += 1
        except Exception as exc:
            failures.append(classify_failure(exc))
            continue
        candidates.extend(r for r in recordings if r['recorded_at'] <= cutoff and r['url'] not in excluded
                          and (after is None or datetime.fromisoformat(r['recorded_at']) > after))
        if len(spaced(candidates)) >= limit:
            break
    if not candidates:
        if directories_read and (excluded or after):
            raise NoFreshRecordings('No new eligible recordings since the reviewed footage; wait for a fresh session')
        failure = RuntimeError(f'No eligible recordings in lookback window ({len(failures)} directory failures)')
        failure.failure_category = failures[0] if failures and len(set(failures)) == 1 else 'discovery_no_eligible_recordings'
        raise failure
    return spaced(candidates)


def discover(source, now=None):
    return discover_many(source, now, limit=1)[0]
