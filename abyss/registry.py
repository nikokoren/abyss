import json
import re
from pathlib import Path


def load(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported source registry version')
    sources = data['sources']
    ids = [s['id'] for s in sources]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', i) for i in ids):
        raise ValueError('Source IDs must be unique safe slugs')
    return sources


def eligible(source: dict) -> bool:
    evidence = source.get('validation', {})
    return (source.get('status') == 'validated' and source.get('adapter') in {'ooi_directory', 'direct'}
            and all(evidence.get(k) for k in ('retrieval_at', 'terms_reviewed_at', 'evidence'))
            and all(source.get(k) for k in ('attribution', 'attribution_url', 'license', 'license_url', 'allowed_hosts')))
