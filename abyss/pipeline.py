import contextlib
import hashlib
import json
import logging
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image
from .adapters import discover_many
from .imaging import render_for_source
from .network import RangeVideo, TransferBudget
from .stills import download_image
from .publication import atomic_json, catalog, publish, read_json
from .registry import eligible
from .video import extract
from .search import search
from .preferences import load_model

log = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def candidates(source, recording, directory, args):
    start = time.monotonic()
    if recording.get('media_type') == 'image':
        budget = TransferBudget(min(args.max_bytes, source.get('max_search_bytes', args.max_bytes)))
        path, diagnostics = download_image(recording, source, directory, budget, 0)
        diagnostics.update(elapsed_seconds=round(time.monotonic() - start, 3),
                           upstream_requests=budget.requests, byte_budget=budget.limit,
                           candidates_requested=1, candidates_extracted=1, strategy='snapshot')
        return [(0, path)], diagnostics
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


def publish_candidate(source, args, candidate, diagnostics, context):
    recording, seconds, frame, metrics = candidate['recording'], candidate['seconds'], candidate['path'], candidate['quality']
    score = metrics['score']
    extracted = datetime.fromtimestamp(frame.stat().st_mtime, timezone.utc).isoformat()
    with Image.open(frame) as image:
        original_size = image.size
        display_image = image.convert('RGB') if args.method == 'native' else None
        processed = render_for_source(image, source, args.width, args.height, args.method,
                                      args.contrast, args.brightness)
    capture = None
    if recording.get('recorded_at'):
        stamp = datetime.fromisoformat(recording['recorded_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Recording time requires a timezone')
        capture = (stamp + timedelta(seconds=seconds)).isoformat()
    metadata = {'source_id': source['id'], 'source_name': source['name'], 'source_type': source['type'],
                'description': source.get('description'), 'recorded_at': recording.get('recorded_at'),
                **{key: source.get(key) for key in ('location', 'location_label', 'depth_m', 'depth_label', 'depth_status', 'depth_evidence')},
                'frame_seconds': round(seconds, 3), 'captured_at': capture, 'extracted_at': extracted,
                'processed_at': utcnow(), 'published_at': utcnow(), 'original_url': recording['url'],
                'attribution': source['attribution'], 'attribution_url': source['attribution_url'],
                'attribution_embedded': bool(source.get('image_credit_lines')),
                'license': source['license'], 'license_url': source['license_url'],
                'acknowledgment': source.get('acknowledgment'),
                'data_doi': source.get('data_doi'),
                'rights_review_url': source.get('rights_review_url'),
                'timestamp_basis': source.get('timestamp_basis'),
                'processing_note': ('Full-resolution color photo for TRMNL, with native theme-aware credit. Downloadable still has a separate credit band. TRMNL resizes and dithers for the device.'
                                    if args.method == 'native' else 'Derived still: resized, contrast adjusted and rendered for e-paper'),
                'preference': diagnostics.get('preference'), 'selection_score': candidate.get('selection_score', score),
                'width': processed.width, 'height': processed.height, 'source_width': original_size[0],
                'source_height': original_size[1], 'color_mode': processed.mode,
                'method': args.method, 'quality': metrics,
                'selection_reason': 'Best readable recent snapshot or video frame using quality, novelty and any active personal preference model',
                'diagnostics': diagnostics, 'fixture': bool(args.local_video)}
    metadata['selection_context'] = context
    publish(args.output, source, processed, metadata, args.base_url, display_image=display_image, update_latest=False)
    return metadata


def run_source(source, args):
    path = Path(args.output) / 'state' / f'{source["id"]}.json'
    directory = Path(args.output) / 'public' / 'sources' / source['id']
    state = read_json(path, {})
    now = utcnow()
    if state.get('retry_after') and now < state['retry_after'] and not args.force:
        log.info('%s cooling down until %s', source['id'], state['retry_after'])
        return 'cooldown'
    state['last_checked_at'] = now
    try:
        is_snapshot = source['adapter'] == 'ooi_image_directory'
        count = source.get('images_per_search', 9) if is_snapshot else getattr(args, 'recordings', 3)
        recordings = ([{'url': 'local-fixture', 'recorded_at': args.recorded_at}] if args.local_video
                      else discover_many(source, limit=count))
        preference = load_model(getattr(args, 'preference_model', None))
        requested_model_id = preference['model_id'] if preference else None
        render_profile = hashlib.sha256(json.dumps({
            'delivery_revision': 3, 'selection_revision': 2, 'recording_limit': count,
            'width': args.width, 'height': args.height, 'method': args.method,
            'contrast': args.contrast, 'brightness': args.brightness,
            'preserve_frame': source.get('preserve_frame', False),
            'image_credit_lines': source.get('image_credit_lines', []),
            'scoring': source.get('scoring', {}),
            'search': {key: getattr(args, key, None) for key in
                       ('candidates', 'coarse_candidates', 'refine_candidates', 'refine_windows', 'interval', 'max_bytes')},
        }, sort_keys=True).encode()).hexdigest()
        context = {'model_id': requested_model_id, 'profile': render_profile}
        same_profile = (state.get('preference_model_id') == requested_model_id
                        and state.get('render_profile') == render_profile)
        known = set(state.get('processed', [])) if same_profile else set()
        pending = [r for r in recordings if args.force or r['url'] not in known]
        if not pending:
            state.update(failures=0, last_result='unchanged')
            state.pop('retry_after', None)
            atomic_json(path, state)
            return 'unchanged'
        with tempfile.TemporaryDirectory(prefix='abyss-') as temporary:
            best, diagnostics, completed = search(source, pending, temporary, args, state.get('history', []))
            state['diagnostics'] = diagnostics
            context = {'model_id': diagnostics.get('preference', {}).get('model_id', requested_model_id),
                       'profile': render_profile}
            if best is None:
                raise RuntimeError('No candidate frames extracted from recent recordings: ' +
                                   '; '.join(e for r in diagnostics['recordings'] for e in r['errors'])[:1200])
            state.update(last_successful_retrieval=utcnow(), failures=0)
            state.pop('retry_after', None)
            processed_recordings = list(dict.fromkeys(state.get('processed', []) + completed))[-256:]
            minimum = source.get('scoring', {}).get('min_score', .30)
            index = read_json(directory / 'sessions.json', {'sessions': []})
            saved = {m['original_url']: m for m in index['sessions']}
            candidates_to_publish = [best] if is_snapshot else best.get('session_winners', [best])
            fresh = []
            for candidate in candidates_to_publish:
                if candidate['quality']['score'] >= minimum:
                    metadata = publish_candidate(source, args, candidate, diagnostics, context)
                    fresh.append(metadata)
                    if not is_snapshot:
                        saved[metadata['original_url']] = metadata
            if not is_snapshot:
                session_history = sorted(saved.values(), key=lambda m: m.get('recorded_at') or '', reverse=True)[:6]
                atomic_json(directory / 'sessions.json', {'schema_version': 1, 'source_id': source['id'],
                            'updated_at': utcnow(), 'sessions': session_history})
                recent = {r['url'] for r in recordings}
                pool = [m for m in session_history if m['original_url'] in recent
                        and m.get('selection_context') == context and m['quality']['score'] >= minimum]
            else:
                pool = fresh
            state.update(processed=processed_recordings, preference_model_id=diagnostics.get('preference', {}).get('model_id', requested_model_id),
                         render_profile=render_profile)
            if not pool:
                state['last_result'] = 'no acceptable candidates; retained last good image'
                atomic_json(path, state)
                return 'rejected'
            selected = max(pool, key=lambda m: (m['selection_score'], m.get('recorded_at') or ''))
            previous = read_json(directory / 'latest.json', {})
            unchanged = (not args.force and selected.get('image_url') == previous.get('image_url')
                         and selected.get('original_url') == previous.get('original_url')
                         and selected.get('frame_seconds') == previous.get('frame_seconds'))
            if unchanged:
                selected = dict(selected, published_at=previous['published_at'])
            atomic_json(directory / 'latest.json', selected)
            if not unchanged:
                state['history'] = (state.get('history', []) + [selected['quality']['fingerprint']])[-24:]
            state['last_published_at'] = selected['published_at']
            state['last_result'] = 'new session winners saved; current winner unchanged' if unchanged else 'published'
            atomic_json(path, state)
            return 'unchanged' if unchanged else 'published'
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
