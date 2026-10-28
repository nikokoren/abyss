"""Build a self-contained A/B gallery and an immutable feature manifest."""
import argparse
import base64
import io
import json
import math
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from .adapters import discover_many
from .feedback import batch_id
from .imaging import render_for_source, similarity
from .preferences import FEATURE_SPACE, ImageEncoder, digest, load_model
from .publication import atomic_json, read_json
from .registry import eligible, load
from .search import search


def near_duplicate(a, b):
    """Conservative still-review heuristic, not a subject/change detector."""
    if (not a.get('fingerprint') or not b.get('fingerprint')
            or similarity(a['fingerprint'], b['fingerprint']) < .88
            or abs(a['quality_score'] - b['quality_score']) > .05
            or abs(a['features'][1] - b['features'][1]) > .04):
        return False
    x, y = a['features'][6:], b['features'][6:]
    if not x or len(x) != len(y):
        return False
    scale = math.sqrt(sum(v * v for v in x) * sum(v * v for v in y))
    return bool(scale and sum(v * w for v, w in zip(x, y)) / scale >= .975)


def distinct_candidates(candidates):
    """Keep the best-quality representative of each near-identical view."""
    kept = {}
    for key, candidate in sorted(candidates.items(), key=lambda item: item[1]['quality_score'], reverse=True):
        if not any(near_duplicate(candidate, previous) for previous in kept.values()):
            kept[key] = candidate
    return kept


def review_inputs(source, *, max_bytes=None, snapshot_count=9, snapshot_spacing_minutes=20):
    """Review several capture bursts without changing production byte limits."""
    if not 2 <= snapshot_count <= 12 or not 1 <= snapshot_spacing_minutes <= 1440:
        raise ValueError('Review requires 2..12 snapshots spaced 1..1440 minutes apart')
    if source['adapter'] != 'ooi_image_directory':
        limit = max_bytes if max_bytes is not None else 64 * 1024 * 1024
        if limit < 1:
            raise ValueError('Review byte budget must be positive')
        return source, discover_many(source, limit=3), limit
    ceiling = min(snapshot_count * source.get('max_image_bytes', 4 * 1024 * 1024), 256 * 1024 * 1024)
    limit = min(max_bytes, ceiling) if max_bytes is not None else ceiling
    if limit < 1:
        raise ValueError('Review byte budget must be positive')
    reviewed_source = dict(source, max_search_bytes=limit)
    records = discover_many(source, limit=snapshot_count,
                            min_spacing_seconds=snapshot_spacing_minutes * 60)
    return reviewed_source, records, limit


def data_url(image):
    out = io.BytesIO(); image.save(out, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()


class Gallery:
    def __init__(self, source, reviewer, repo, model=None, *, include_similar=False):
        self.source, self.reviewer, self.repo, self.model = source, reviewer, repo, model
        self.candidates, self.images = {}, {}
        self.include_similar = include_similar

    def add(self, candidate, image, features):
        if features is None:
            raise ValueError('Gallery needs pretrained image features')
        import hashlib
        pixels = hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
        identity = digest([self.source['id'], candidate['recording']['url'], round(candidate['seconds'], 3), pixels, FEATURE_SPACE])[:32]
        metrics = candidate['quality']
        self.candidates[identity] = {'id': identity, 'source_id': self.source['id'],
            'source_name': self.source['name'], 'recording_url': candidate['recording']['url'],
            'recorded_at': candidate['recording'].get('recorded_at'), 'frame_seconds': round(candidate['seconds'], 3),
            'stage': candidate['stage'], 'features': features, 'fingerprint': metrics['fingerprint'],
            'quality_score': metrics['score'], 'selection_score': candidate['selection_score'],
            'preference_score': candidate.get('preference_score'), 'fixture': bool(self.source.get('fixture'))}
        raw = image.convert('RGB'); raw.thumbnail((640, 400), Image.Resampling.LANCZOS)
        paper = render_for_source(image, self.source)
        self.images[identity] = {'original': data_url(raw), 'paper': data_url(paper)}

    def save(self, output, encoder, diagnostics):
        if len(self.candidates) < 2:
            raise ValueError('At least two decoded frames are needed for review')
        filter_similar = self.source.get('adapter') == 'ooi_image_directory' and not self.include_similar
        candidates = distinct_candidates(self.candidates) if filter_similar else self.candidates
        status = 'ready' if len(candidates) >= 2 else 'no_review_needed'
        diversity = {'sampled_candidate_count': len(self.candidates),
                     'candidate_count': len(candidates),
                     'similar_candidates_suppressed': len(self.candidates) - len(candidates),
                     'policy': 'still_appearance_structure_v1' if filter_similar else 'unfiltered'}
        manifest = {'schema_version': 1, 'feature_space': FEATURE_SPACE,
                    'reviewer': self.reviewer, 'repository': self.repo,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'encoder': encoder.provenance, 'candidates': candidates,
                    'review_status': status, 'diversity': diversity,
                    'source_attribution': self.source.get('attribution'),
                    'source_license': self.source.get('license'),
                    'source_url': self.source.get('attribution_url')}
        manifest['batch_id'] = batch_id(manifest)
        public_candidates = [{k: v for k, v in c.items() if k not in ('features', 'fingerprint')}
                             | self.images[key] for key, c in candidates.items()]
        data = {'batch_id': manifest['batch_id'], 'reviewer': self.reviewer, 'repository': self.repo,
                'candidates': public_candidates, 'attribution': manifest['source_attribution'],
                'review_status': status,
                'license': manifest['source_license'], 'source_url': manifest['source_url'],
                'model': ({k: self.model.get(k) for k in ('status', 'comparisons', 'trained_at', 'evaluation')}
                          if self.model else {'status': 'needs_more_feedback', 'comparisons': 0})}
        resources = Path(__file__).resolve().parent.parent / 'web' / 'review'
        template = (resources / 'index.html').read_text()
        safe_json = json.dumps(data, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c').replace('&', '\\u0026')
        html = template.replace('__ABYSS_DATA__', safe_json).replace('__REVIEW_CORE__', (resources / 'core.js').read_text()).replace('__REVIEW_APP__', (resources / 'app.js').read_text())
        output = Path(output); output.mkdir(parents=True, exist_ok=True)
        (output / 'index.html').write_text(html)
        atomic_json(output / 'manifest.json', manifest)
        atomic_json(output / 'gallery-report.json', {'schema_version': 1, 'batch_id': manifest['batch_id'],
                    'source_id': self.source['id'], 'source_name': self.source['name'],
                    'review_status': status, **diversity, 'encoder': encoder.provenance,
                    'reviewer': self.reviewer, 'diagnostics': diagnostics,
                    'run_url': (f'https://github.com/{self.repo}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
                                if os.environ.get('GITHUB_RUN_ID') else None),
                    'artifact_name': 'abyss-review-gallery', 'public_pages_publication': False, 'distribution': 'GitHub Actions review artifact; access follows repository artifact permissions'})
        return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', default='sources.json')
    parser.add_argument('--source', default='ooi-axial')
    parser.add_argument('--output', default='output/review')
    parser.add_argument('--reviewer', default=os.environ.get('PREFERENCE_REVIEWER', 'nikokoren'))
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'nikokoren/abyss'))
    parser.add_argument('--preference-model', default='preferences/model.json')
    parser.add_argument('--max-bytes', type=int, help='Optional smaller retrieval cap; snapshot reviews are capped at 256 MiB')
    parser.add_argument('--snapshot-count', type=int, default=9)
    parser.add_argument('--snapshot-spacing-minutes', type=int, default=20)
    parser.add_argument('--include-similar', action='store_true', help='Include near-identical stills for manual inspection')
    parser.add_argument('--local-video')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.reviewer) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        parser.error('Invalid GitHub reviewer or repository')
    source = next((s for s in load(args.registry) if s['id'] == args.source), None)
    if not source:
        parser.error('Unknown source')
    if not eligible(source):
        parser.error('Review requires a validated source with reviewed attribution and reuse terms')
    if args.local_video and not source.get('fixture'):
        parser.error('Local review video requires a fixture-only source')
    model = load_model(args.preference_model)
    started = time.monotonic(); encoder = ImageEncoder()
    metadata = read_json(args.preference_model, {})
    if not model and (metadata.get('status') != 'needs_more_feedback' or metadata.get('feature_space') != FEATURE_SPACE or metadata.get('reviewer') != args.reviewer):
        metadata = None
    gallery = Gallery(source, args.reviewer, args.repository, model or metadata, include_similar=args.include_similar)
    if args.local_video:
        records = [{'url': 'local-fixture', 'recorded_at': None}]
        byte_limit = args.max_bytes if args.max_bytes is not None else 64 * 1024 * 1024
    else:
        source, records, byte_limit = review_inputs(source, max_bytes=args.max_bytes,
            snapshot_count=args.snapshot_count, snapshot_spacing_minutes=args.snapshot_spacing_minutes)
    search_args = argparse.Namespace(local_video=args.local_video, max_bytes=byte_limit, candidates=8,
                    coarse_candidates=4, refine_candidates=4, refine_windows=2, interval=1 if args.local_video else 60,
                    preference_model=args.preference_model, preference_encoder=encoder, review_sink=gallery.add)
    with tempfile.TemporaryDirectory(prefix='abyss-review-') as tmp:
        _, diagnostics, _ = search(source, records, tmp, search_args)
        diagnostics['gallery_elapsed_seconds'] = round(time.monotonic() - started, 3)
        diagnostics['capture_times'] = [r.get('recorded_at') for r in records]
        manifest = gallery.save(args.output, encoder, diagnostics)
    print(json.dumps({'batch_id': manifest['batch_id'], 'candidates': len(manifest['candidates']),
                      'review_status': manifest['review_status'], 'output': args.output}))


if __name__ == '__main__': main()
