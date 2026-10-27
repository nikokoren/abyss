"""Validate owner-authored feedback; browser-supplied feature vectors are never trusted."""
import json
import re
from .preferences import FEATURE_SPACE, digest, vector


def batch_id(manifest):
    return digest({k: v for k, v in manifest.items() if k != 'batch_id'})[:32]


def parse_body(body):
    if len(body.encode()) > 200_000:
        raise ValueError('Feedback body too large')
    blocks = re.findall(r'```abyss-feedback\s*\n(.*?)\n```', body, flags=re.S)
    if len(blocks) != 1:
        raise ValueError('Expected one abyss-feedback JSON block')
    data = json.loads(blocks[0])
    if data.get('schema_version') != 1 or not re.fullmatch('[0-9a-f]{32}', data.get('batch_id', '')):
        raise ValueError('Invalid feedback schema or batch identity')
    rows = data.get('comparisons')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        raise ValueError('Feedback needs 1..200 comparisons')
    return data


def normalize(payload, manifest, *, reviewer, issue_number, updated_at):
    if batch_id(manifest) != payload['batch_id'] or manifest.get('batch_id') != payload['batch_id']:
        raise ValueError('Manifest identity mismatch')
    if manifest.get('feature_space') != FEATURE_SPACE or manifest.get('reviewer') != reviewer:
        raise ValueError('Wrong feature space or reviewer')
    frames, rows, keys = {}, [], set()
    candidates = manifest['candidates']
    for row in payload['comparisons']:
        if set(row) - {'a', 'b', 'choice', 'repetitive'}:
            raise ValueError('Unknown feedback fields; features must come from the trusted manifest')
        a, b, choice = row['a'], row['b'], row['choice']
        if a == b or a not in candidates or b not in candidates or choice not in ('a', 'b', 'neither'):
            raise ValueError('Invalid image pair or choice')
        repeated = row.get('repetitive', [])
        if not isinstance(repeated, list) or any(i not in (a, b) for i in repeated):
            raise ValueError('Invalid repetitive flag')
        if b < a:
            a, b = b, a
            choice = {'a': 'b', 'b': 'a', 'neither': 'neither'}[choice]
        key = digest([FEATURE_SPACE, a, b])
        if key in keys:
            raise ValueError('Duplicate comparison in feedback batch')
        keys.add(key)
        rows.append({'key': key, 'a': a, 'b': b, 'choice': choice, 'repetitive': sorted(set(repeated))})
        for image_id in (a, b):
            candidate = candidates[image_id]
            vector(candidate['features'])
            frames[image_id] = {k: candidate[k] for k in ('features', 'recording_url', 'fingerprint', 'quality_score')}
    return {'schema_version': 1, 'feature_space': FEATURE_SPACE, 'reviewer': reviewer,
            'issue_number': int(issue_number), 'updated_at': updated_at,
            'batch_id': payload['batch_id'], 'frames': frames, 'comparisons': rows}
