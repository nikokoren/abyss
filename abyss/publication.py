import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from .registry import eligible


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(data, out, indent=2, allow_nan=False)
            out.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_json(path, default):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def publish(root, source, image, metadata, base_url):
    from PIL import Image
    directory = Path(root) / 'public' / 'sources' / source['id']
    directory.mkdir(parents=True, exist_ok=True)
    # Immutable content-addressed image first; JSON is the commit point.
    fd, temporary = tempfile.mkstemp(dir=directory, suffix='.png')
    os.close(fd)
    try:
        image.save(temporary, format='PNG')
        with Image.open(temporary) as check:
            check.verify()
        digest = hashlib.sha256(Path(temporary).read_bytes()).hexdigest()[:20]
        filename = f'{digest}.png'
        os.replace(temporary, directory / filename)
        metadata['image_url'] = f'{base_url.rstrip("/")}/sources/{source["id"]}/{filename}'
        metadata['image_sha256'] = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
        atomic_json(directory / 'latest.json', metadata)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return metadata


def catalog(root, sources, now, base_url):
    public = Path(root) / 'public'
    entries = {}
    options = []
    for source in sources:
        if not eligible(source):
            continue
        state = read_json(Path(root) / 'state' / f'{source["id"]}.json', {})
        latest = read_json(public / 'sources' / source['id'] / 'latest.json', None)
        if latest is None:
            continue
        latest = dict(latest)
        latest.pop('fingerprint', None)
        latest['available'] = state.get('failures', 0) < 3
        latest['last_checked_at'] = state.get('last_checked_at')
        latest['last_successful_retrieval'] = state.get('last_successful_retrieval')
        latest['stale'] = False
        if latest.get('captured_at') and source['type'] != 'archive':
            age = (datetime.fromisoformat(now) - datetime.fromisoformat(latest['captured_at'])).total_seconds()
            latest['stale'] = age > source.get('stale_after_hours', 48) * 3600
        latest['health'] = ('stale recording; showing last good frame' if latest['stale'] else 'available') if latest['available'] else 'unavailable; showing last good frame'
        entries[source['id']] = latest
        if latest['available']:
            options.append({'label': f'{source["name"]} ({source["type"].replace("_", " ")})', 'value': source['id'],
                            'description': source.get('description', '')})
    default = options[0]['value'] if options else None
    # Stable default object keeps a retained good image visible during total outage.
    fallback = entries.get(default) or next(iter(entries.values()), None)
    atomic_json(public / 'catalog.json', {'schema_version': 1, 'updated_at': now, 'default_source': default,
                                        'default_image': fallback, 'options': options, 'sources': entries})
    atomic_json(public / 'health.json', {'checked_at': now, 'sources': {
        s['id']: {'registry_status': s['status'], **{k: v for k, v in read_json(Path(root) / 'state' / f'{s["id"]}.json', {}).items() if k in {'failures', 'last_result', 'last_error', 'last_checked_at', 'retry_after', 'last_published_at', 'last_successful_retrieval', 'diagnostics'}}} for s in sources}})
    return options
