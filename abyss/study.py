"""Metadata-only runner study of OOI cadence and multi-recording frame search."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from .adapters import discover_many
from .cadence import observe
from datetime import datetime, timezone
from .publication import atomic_json, read_json
from .registry import load
from .network import classify_failure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', default='output/observations/state.json')
    parser.add_argument('--output', default='output/observations')
    parser.add_argument('--benchmark', action='store_true')
    parser.add_argument('--registry', default='sources.json')
    parser.add_argument('--max-bytes', type=int, default=64 * 1024 * 1024)
    args = parser.parse_args()
    source = next(s for s in load(args.registry) if s['id'] == 'ooi-axial')
    output = Path(args.output)
    previous = read_json(args.state, {})
    provenance = {'environment': 'github_actions' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'local',
                  'tested_commit': os.environ.get('GITHUB_SHA'),
                  'run_url': (f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
                              if os.environ.get('GITHUB_RUN_ID') else None),
                  'imagery_published': False, 'rights_status': 'not_assessed'}
    failed = False
    try:
        cadence, state = observe(source, previous)
        atomic_json(output / 'state.json', state)
        atomic_json(output / 'cadence.json', {**cadence, **provenance})
    except Exception as exc:
        failed = True
        atomic_json(output / 'cadence.json', {**provenance, 'status': 'failed', 'checked_at': datetime.now(timezone.utc).isoformat(),
                    'failure': {'category': classify_failure(exc), 'message': str(exc)[:2000]}})
    if args.benchmark:
        try:
            from .search import search
            recordings = discover_many(source, limit=3)
            search_args = argparse.Namespace(local_video=None, max_bytes=args.max_bytes, candidates=8,
                                             coarse_candidates=4, refine_candidates=4, refine_windows=2, interval=60)
            with tempfile.TemporaryDirectory(prefix='abyss-study-') as tmp:
                best, diagnostics, completed = search(source, recordings, tmp, search_args)
                selected = ({'recording': best['recording'], 'frame_seconds': best['seconds'],
                             'stage': best['stage'], 'quality': best['quality']} if best else None)
                passed = bool(best and best['quality']['score'] >= source['scoring']['min_score'])
                report = {**provenance, 'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'passed' if passed else 'failed',
                          'selected': selected, 'diagnostics': diagnostics, 'completed_recordings': completed}
                atomic_json(output / 'search.json', report)
                failed |= not passed
        except Exception as exc:
            failed = True
            atomic_json(output / 'search.json', {**provenance, 'status': 'failed', 'checked_at': datetime.now(timezone.utc).isoformat(),
                        'failure': {'category': classify_failure(exc), 'message': str(exc)[:2000]}})
    print(json.dumps({'output': str(output), 'failed': failed, **provenance}, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
