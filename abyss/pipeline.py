import contextlib
import logging
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image
from .adapters import discover_many
from .imaging import render
from .network import RangeVideo
from .publication import atomic_json, catalog, publish, read_json
from .registry import eligible
from .video import extract
from .search import search

log = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def candidates(source, recording, directory, args):
    start = time.monotonic()
    video = None
    if args.local_video:
        manager = contextlib.nullcontext(str(Path(args.local_video).resolve()))
    else:
        video = RangeVideo(recording['url'], source['allowed_hosts'], args.max_bytes)
        manager = video.bridge()
    with manager as url:
        frames, diagnostics = extract(url, directory, args.interval, args.candidates)
    diagnostics.update({'elapsed_seconds': round(time.monotonic() - start, 3),
                        'bytes_downloaded': video.bytes_read if video else 0,
                        'upstream_requests': video.requests if video else 0,
                        'recording_bytes': video.total if video else Path(args.local_video).stat().st_size,
                        'range_error': video.error if video else None})
    if video and video.error:
        raise RuntimeError('Range extraction incomplete: ' + video.error)
    return frames, diagnostics


def run_source(source, args):
    path = Path(args.output) / 'state' / f'{source["id"]}.json'
    state = read_json(path, {})
    now = utcnow()
    if state.get('retry_after') and now < state['retry_after'] and not args.force:
        log.info('%s cooling down until %s', source['id'], state['retry_after'])
        return 'cooldown'
    state['last_checked_at'] = now
    try:
        recordings = ([{'url': 'local-fixture', 'recorded_at': args.recorded_at}] if args.local_video
                      else discover_many(source, limit=getattr(args, 'recordings', 3)))
        known = set(state.get('processed', []))
        pending = [r for r in recordings if args.force or r['url'] not in known]
        if not pending:
            state.update(failures=0, last_result='unchanged')
            state.pop('retry_after', None)
            atomic_json(path, state)
            return 'unchanged'
        with tempfile.TemporaryDirectory(prefix='abyss-') as temporary:
            best, diagnostics, completed = search(source, pending, temporary, args, state.get('history', []))
            state['diagnostics'] = diagnostics
            if best is None:
                raise RuntimeError('No candidate frames extracted from recent recordings: ' +
                                   '; '.join(e for r in diagnostics['recordings'] for e in r['errors'])[:1200])
            recording, seconds, frame, metrics = best['recording'], best['seconds'], best['path'], best['quality']
            score = metrics['score']
            state['last_successful_retrieval'] = utcnow()
            state['failures'] = 0
            state.pop('retry_after', None)
            processed_recordings = list(dict.fromkeys(state.get('processed', []) + completed))[-256:]
            if score < source.get('scoring', {}).get('min_score', .30):
                state['processed'] = processed_recordings
                state['last_result'] = 'no acceptable candidates; retained last good image'
                atomic_json(path, state)
                return 'rejected'
            extracted = datetime.fromtimestamp(frame.stat().st_mtime, timezone.utc).isoformat()
            with Image.open(frame) as image:
                processed = render(image, args.width, args.height, args.method, args.contrast, args.brightness)
            capture = None
            if recording.get('recorded_at'):
                stamp = datetime.fromisoformat(recording['recorded_at'].replace('Z', '+00:00'))
                if stamp.tzinfo is None:
                    raise ValueError('Recording time requires a timezone')
                capture = (stamp + timedelta(seconds=seconds)).isoformat()
            metadata = {'source_id': source['id'], 'source_name': source['name'], 'source_type': source['type'],
                        'description': source.get('description'), 'recorded_at': recording.get('recorded_at'),
                        'frame_seconds': round(seconds, 3), 'captured_at': capture, 'extracted_at': extracted,
                        'processed_at': utcnow(), 'published_at': utcnow(), 'original_url': recording['url'],
                        'attribution': source['attribution'], 'attribution_url': source['attribution_url'],
                        'license': source['license'], 'license_url': source['license_url'],
                        'width': args.width, 'height': args.height, 'method': args.method, 'quality': metrics,
                        'selection_reason': 'Best coarse/fine candidate across recent recordings with quality and recent-image similarity scoring',
                        'diagnostics': diagnostics, 'fixture': bool(args.local_video)}
            publish(args.output, source, processed, metadata, args.base_url)
            state['processed'] = processed_recordings
            state['history'] = (state.get('history', []) + [metrics['fingerprint']])[-24:]
            state['last_published_at'] = metadata['published_at']
            state['last_result'] = 'published'
            atomic_json(path, state)
            return 'published'
    except Exception as exc:
        failures = state.get('failures', 0) + 1
        state.update({'failures': failures, 'last_error': str(exc)[:2000], 'last_result': 'failed',
                      'retry_after': (datetime.now(timezone.utc) + timedelta(hours=min(48, 2 ** min(failures, 6)))).isoformat()})
        atomic_json(path, state)
        log.error('%s: %s', source['id'], exc)
        return 'failed'


def run(sources, args):
    (Path(args.output) / 'state').mkdir(parents=True, exist_ok=True)
    selected = [s for s in sources if eligible(s)]
    if args.source:
        requested = [s for s in selected if s['id'] == args.source]
        if not requested:
            log.warning('Unknown/unavailable selection; using first eligible source')
        selected = requested or selected[:1]
    results = {s['id']: run_source(s, args) for s in selected}
    catalog(args.output, sources, utcnow(), args.base_url)
    log.info('Results: %s', results or 'no validated sources; publication withheld')
    return results
