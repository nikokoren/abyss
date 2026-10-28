"""Validate rights-reviewed OOI still-camera candidates without enabling them."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from .adapters import discover_many
from .imaging import render_for_source
from .network import classify_failure
from .pipeline import utcnow
from .registry import load
from .search import search
from .stills import probe_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', default='docs/camera-candidates.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for source in load(args.registry):
        record = {'source_id': source['id'], 'checked_at': utcnow(), 'technical_status': 'failed',
                  'rights_status': source['validation'].get('rights_status'),
                  'reference': source['base_url'], 'technical_usable': False}
        if (source['adapter'] != 'ooi_image_directory' or not source['validation'].get('terms_reviewed_at')
                or source['validation'].get('rights_status') != 'approved_attributed_derived_stills'):
            raise ValueError('Sample imagery requires an explicitly rights-reviewed OOI still camera')
        try:
            recordings = discover_many(source, limit=source['images_per_search'])
            record['recordings'] = recordings
            try:
                record['image_header_probe'] = probe_image(recordings[0], source)
            except Exception as exc:
                record['image_header_probe'] = {'failure': str(exc)[:500]}
            search_args = SimpleNamespace(candidates=9, coarse_candidates=4, refine_candidates=0,
                                          refine_windows=1, interval=1, max_bytes=source['max_search_bytes'],
                                          local_video=None, preference_model=None)
            with tempfile.TemporaryDirectory() as temporary:
                best, diagnostics, completed = search(source, recordings, temporary, search_args)
                record['diagnostics'] = diagnostics
                if best is None:
                    raise RuntimeError('No snapshots decoded')
                record.update(technical_status='passed', completed=len(completed), best_quality=best['quality'],
                              selected_recording=best['recording'],
                              technical_usable=diagnostics['search_complete'] and best['quality']['score'] >= source['scoring']['min_score'])
                with Image.open(best['path']) as image:
                    for method in ('grayscale', 'ordered'):
                        name = source['id'] + '-' + method + '.png'
                        render_for_source(image, source, method=method).save(args.output / name)
                        record[method + '_preview'] = name
        except Exception as exc:
            record['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:1000]}
        results.append(record)
        print(source['id'], record['technical_status'], record.get('best_quality', {}).get('score'))
    report = {'schema_version': 1, 'checked_at': utcnow(), 'commit': os.environ.get('GITHUB_SHA'),
              'run_url': f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}' if os.environ.get('GITHUB_RUN_ID') else None,
              'imagery_published': any(r.get('ordered_preview') for r in results),
              'scope': 'Licensed OOI preview images and technical evidence; registry approval requires review',
              'sources': results}
    (args.output / 'image-validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
