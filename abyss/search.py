"""Coarse-to-fine ranking across a bounded set of recent recordings."""
import contextlib
import time
from pathlib import Path
from PIL import Image
from .imaging import quality
from .network import RangeVideo, TransferBudget
from .video import extract_positions, probe


def search(source, recordings, directory, args, history=()):
    started = time.monotonic()
    maximum = args.candidates
    coarse = min(getattr(args, 'coarse_candidates', 4), maximum)
    refinement_limit = getattr(args, 'refine_candidates', 4)
    windows = getattr(args, 'refine_windows', 2)
    if not 1 <= maximum <= 48 or not 1 <= coarse <= 48 or not 0 <= refinement_limit <= 48 or not 1 <= windows <= 8:
        raise ValueError('Invalid coarse/fine search limits')
    if args.interval < 1 or not 1 <= len(recordings) <= 12:
        raise ValueError('Invalid interval or recording count')
    budget = TransferBudget(args.max_bytes)
    sessions, candidates = [], []
    profile = source.get('scoring', {})

    def score_frames(frames, session, stage):
        for seconds, path in frames:
            with Image.open(path) as image:
                metrics = quality(image, history, profile.get('novelty_weight', .12))
            candidates.append({'recording': session['recording'], 'seconds': seconds,
                               'path': path, 'quality': metrics, 'stage': stage,
                               'session': session})
            session['positions'].add(round(seconds, 3))

    with contextlib.ExitStack() as stack:
        for index, recording in enumerate(recordings):
            session = {'recording': recording, 'video': None, 'positions': set(),
                       'errors': [], 'coarse_requested': 0, 'coarse_extracted': 0,
                       'fine_requested': 0, 'fine_extracted': 0, 'index': index}
            sessions.append(session)
            try:
                if args.local_video:
                    url = str(Path(args.local_video).resolve())
                else:
                    session['video'] = RangeVideo(recording['url'], source['allowed_hosts'],
                                                  args.max_bytes, budget=budget)
                    url = stack.enter_context(session['video'].bridge())
                session['url'] = url
                duration, codec = probe(url)
                session.update(duration=duration, codec=codec)
                count = min(coarse, max(1, int(duration // args.interval)))
                positions = [duration * (i + .5) / count for i in range(count)]
                session['spacing'] = duration / count
                session['coarse_requested'] = count
                frames, details = extract_positions(url, directory, positions, duration=duration,
                                                     codec=codec, prefix=f'r{index}-coarse')
                session['coarse_extracted'] = len(frames)
                session['errors'].extend(details['extraction_errors'])
                score_frames(frames, session, 'coarse')
            except Exception as exc:
                session['errors'].append(str(exc)[:1500])

        # Only refine promising, technically usable moments. Deduplicate offsets
        # within a recording and honor both total and per-recording candidate caps.
        promising = sorted(candidates, key=lambda c: c['quality']['score'], reverse=True)
        chosen, used = [], 0
        for candidate in promising:
            session = candidate['session']
            if candidate['quality']['score'] < profile.get('min_score', .30):
                continue
            if session['errors'] or (session['video'] and session['video'].error):
                continue
            if any(c['session'] is session and abs(c['seconds'] - candidate['seconds']) < session['spacing'] / 2 for c in chosen):
                continue
            if len(chosen) >= windows or used >= refinement_limit:
                break
            room = maximum - len(session['positions'])
            slots = min(room, 2, refinement_limit - used)
            if slots <= 0:
                continue
            offset = session['spacing'] / 4
            positions = [round(max(0, min(session['duration'] - .001, candidate['seconds'] + sign * offset)), 3)
                         for sign in (-1, 1)]
            positions = [p for p in dict.fromkeys(positions) if p not in session['positions']][:slots]
            if not positions:
                continue
            chosen.append(candidate)
            used += len(positions)
            session['fine_requested'] += len(positions)
            try:
                frames, details = extract_positions(session['url'], directory, positions,
                                                     duration=session['duration'], codec=session['codec'],
                                                     prefix=f'r{session["index"]}-fine{len(chosen)}')
                session['fine_extracted'] += len(frames)
                session['errors'].extend(details['extraction_errors'])
                score_frames(frames, session, 'fine')
            except Exception as exc:
                session['errors'].append(str(exc)[:1500])

    reports, completed = [], []
    for session in sessions:
        video = session['video']
        errors = list(session['errors'])
        if video and video.error and video.error not in errors:
            errors.append(video.error)
        complete = (not errors and session['coarse_extracted'] == session['coarse_requested'] > 0
                    and session['fine_extracted'] == session['fine_requested'])
        if complete:
            completed.append(session['recording']['url'])
        reports.append({'recording': session['recording'], 'complete': complete,
                        'duration_seconds': session.get('duration'), 'codec': session.get('codec'),
                        'coarse_requested': session['coarse_requested'], 'coarse_extracted': session['coarse_extracted'],
                        'fine_requested': session['fine_requested'], 'fine_extracted': session['fine_extracted'],
                        'bytes_downloaded': video.bytes_read if video else 0,
                        'upstream_requests': video.requests if video else 0, 'errors': errors,
                        'recording_bytes': video.total if video else None})
    best = max(candidates, key=lambda c: (c['quality']['score'], c['recording'].get('recorded_at') or ''), default=None)
    diagnostics = {'strategy': 'coarse_to_fine', 'recordings_considered': len(recordings),
                   'candidates_extracted': len(candidates), 'coarse_extracted': sum(s['coarse_extracted'] for s in sessions),
                   'fine_extracted': sum(s['fine_extracted'] for s in sessions),
                   'bytes_downloaded': budget.used, 'byte_budget': budget.limit,
                   'upstream_requests': budget.requests,
                   'search_complete': all(r['complete'] for r in reports),
                   'budget_exhausted': any('budget' in e.lower() for r in reports for e in r['errors']),
                   'elapsed_seconds': round(time.monotonic() - started, 3), 'recordings': reports,
                   'candidate_scores': [{'recording_url': c['recording']['url'], 'frame_seconds': c['seconds'],
                                         'stage': c['stage'], **c['quality']} for c in candidates]}
    return best, diagnostics, completed
