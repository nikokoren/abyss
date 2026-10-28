"""Build owner preference comparisons from the exact saved 42-image Offshore cohort."""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from abyss.about import OOI_ACKNOWLEDGMENT
from abyss.imaging import quality, render_for_source
from abyss.network import TransferBudget, check_url
from abyss.preferences import ImageEncoder, load_model, rank
from abyss.registry import load
from abyss.review import Gallery
from abyss.stills import download_image


def cohort_records(evidence, source):
    """Only capture identity is input: visual annotations never become training labels."""
    if (evidence.get('source_id') != source['id'] or source['id'] != 'ooi-oregon-offshore'
            or source['adapter'] != 'ooi_image_directory'
            or source.get('validation', {}).get('rights_status') != 'approved_attributed_derived_stills'
            or not source['validation'].get('terms_reviewed_at')):
        raise ValueError('Cohort review requires the explicitly rights-reviewed Offshore camera')
    records = []
    for sample in evidence['samples']:
        url = sample['original_url']
        check_url(url, source['allowed_hosts'])
        if not url.startswith(source['base_url'].rstrip('/') + '/'):
            raise ValueError('Snapshot must belong to the reviewed Offshore deployment')
        records.append({'url': url, 'recorded_at': sample['captured_at'], 'media_type': 'image'})
    if len(records) != 42 or len({r['url'] for r in records}) != 42:
        raise ValueError('Expected the complete, unique 42-image sampling cohort')
    return records


def build(evidence, source, output, reviewer, repository, model, encoder):
    records = cohort_records(evidence, source)
    # Explicitly retain this time-spread cohort: static-background dedup can hide animal changes.
    credited = dict(source, license=source['license'] + ' ' + OOI_ACKNOWLEDGMENT)
    gallery = Gallery(credited, reviewer, repository, model, include_similar=True,
                      evaluation_context={'eligible': False, 'fresh_recordings_only': False,
                                          'purpose': 'Owner preference training on a fixed still-image cohort'})
    budget = TransferBudget(512 * 1024 * 1024)
    with tempfile.TemporaryDirectory() as temporary:
        for index, record in enumerate(records):
            path, details = download_image(record, source, temporary, budget, index)
            with Image.open(path) as image:
                metrics = quality(image)
                features = encoder.encode(image, metrics)
                candidate = {'recording': record, 'seconds': 0, 'stage': 'snapshot',
                             'quality': metrics, **rank(metrics, features, model)}
                gallery.add(candidate, image, features)
                # Larger attributed colour previews make small animals easier to judge.
                # Feature extraction above uses full original pixels, without the credit band.
                preview = render_for_source(image, source, method='native')
                preview.thumbnail((1536, 1250), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                preview.save(buffer, format='JPEG', quality=90, optimize=True)
                identity = next(reversed(gallery.candidates))
                gallery.images[identity]['original'] = 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()
            path.unlink()
            print(f'{index + 1}/42 original snapshots encoded; {budget.used} bytes', flush=True)
    manifest = gallery.save(output, encoder, {'bytes_downloaded': budget.used,
        'requests': budget.requests, 'sampling_run_url': evidence['sampling_run_url'],
        'sampling_evidence_commit': evidence['sampling_evidence_commit'],
        'cohort_candidates': len(records), 'automatic_preference_labels': 0,
        'production_source_enabled': False})
    if (Path(output) / 'index.html').stat().st_size > 90 * 1024 * 1024:
        raise ValueError('Self-contained gallery exceeds its 90 MiB artifact budget')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preference-model', required=True)
    parser.add_argument('--reviewer', default=os.environ.get('PREFERENCE_REVIEWER', 'nikokoren'))
    args = parser.parse_args()
    evidence = json.loads(Path('docs/evidence/offshore-wildlife-review-20261028.json').read_text())
    source = next(s for s in load('sources.json') if s['id'] == 'ooi-oregon-offshore')
    manifest = build(evidence, source, args.output, args.reviewer,
                     os.environ.get('GITHUB_REPOSITORY', 'nikokoren/abyss'),
                     load_model(args.preference_model), ImageEncoder())
    print(json.dumps({'batch_id': manifest['batch_id'], 'candidates': len(manifest['candidates'])}))


if __name__ == '__main__':
    main()
