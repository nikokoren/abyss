"""Prospective evaluation of frozen gallery predictions on unreviewed recordings."""
import re
from pathlib import Path

from .publication import read_json


def feedback_context(state, reviewer, source_id):
    seen, stamps = set(), []
    for path in sorted((Path(state) / 'feedback').glob('*.json')):
        doc = read_json(path, {})
        if doc.get('reviewer') != reviewer:
            continue
        seen.update(frame['recording_url'] for frame in doc.get('frames', {}).values())
        identity = doc.get('batch_id', '')
        if not re.fullmatch('[0-9a-f]{32}', identity):
            continue
        manifest = read_json(Path(state) / 'batches' / (identity + '.json'), {})
        for key in doc.get('frames', {}):
            frame = manifest.get('candidates', {}).get(key, {})
            if frame.get('source_id') == source_id and frame.get('recorded_at'):
                stamps.append(frame['recorded_at'])
    return {'training_recording_urls': sorted(seen), 'recorded_after': max(stamps) if stamps else None}


def prospective_report(documents, manifests, reviewer):
    # Only predictions captured before this batch was reviewed are eligible.
    latest = {}
    for doc in documents:
        if doc.get('reviewer') != reviewer:
            continue
        for row in doc.get('comparisons', []):
            order = (doc['updated_at'], doc['issue_number'])
            if row['key'] not in latest or order > latest[row['key']][0]:
                latest[row['key']] = (order, doc['batch_id'], row)
    batches = {}
    for _, batch_id, row in latest.values():
        manifest = manifests.get(batch_id, {})
        context = manifest.get('evaluation_context', {})
        if not context.get('eligible') or not context.get('model_id'):
            continue
        if row['choice'] not in ('a', 'b'):
            continue
        a, b = (manifest.get('candidates', {}).get(row[key]) for key in ('a', 'b'))
        if not a or not b or any(c['recording_url'] in context.get('training_recording_urls', []) for c in (a, b)):
            continue
        if any(c.get('preference_score') is None for c in (a, b)):
            continue
        bucket = batches.setdefault(batch_id, {'model_id': context['model_id'], 'comparisons': 0,
                                              'learned_credit': 0., 'baseline_credit': 0., 'recordings': set()})
        direction = 1 if row['choice'] == 'a' else -1
        credit = lambda difference: 1. if direction * difference > 0 else .5 if difference == 0 else 0.
        bucket['comparisons'] += 1
        bucket['learned_credit'] += credit(a['selection_score'] - b['selection_score'])
        bucket['baseline_credit'] += credit(a['quality_score'] - b['quality_score'])
        bucket['recordings'].update((a['recording_url'], b['recording_url']))
    total = sum(b['comparisons'] for b in batches.values())
    if not total:
        return {'status': 'awaiting_feedback', 'comparisons': 0,
                'note': 'Review a fresh, non-overlapping gallery to compare frozen model predictions with quality-only selection.'}
    learned = sum(b['learned_credit'] for b in batches.values()) / total
    baseline = sum(b['baseline_credit'] for b in batches.values()) / total
    return {'status': 'measured' if total >= 10 else 'collecting', 'comparisons': total,
            'learned_accuracy': learned, 'quality_baseline_accuracy': baseline,
            'difference': learned - baseline,
            'unseen_recording_count': len(set().union(*(b['recordings'] for b in batches.values()))),
            'batches': [{'batch_id': key, 'model_id': b['model_id'], 'comparisons': b['comparisons'],
                        'recording_count': len(b['recordings']),
                        'learned_accuracy': b['learned_credit'] / b['comparisons'],
                        'quality_baseline_accuracy': b['baseline_credit'] / b['comparisons']}
                       for key, b in sorted(batches.items())],
            'note': 'Predictions were frozen before feedback. Pairs from the same camera can be correlated within and across recordings; small samples are provisional.'}
