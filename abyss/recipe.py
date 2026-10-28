"""Generate an importable TRMNL settings file only from healthy published sources."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from .publication import read_json


def generate(output, base_url, destination):
    parsed = urlsplit(base_url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('Recipe requires a public HTTPS base URL without query, fragment or credentials')
    catalog = read_json(Path(output) / 'public' / 'catalog.json', {})
    options = catalog.get('options', [])
    if not options:
        raise ValueError('No validated, healthy published sources; recipe dropdown cannot be generated yet')
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    entries = [catalog.get('sources', {}).get(o['value'], {}) for o in options]
    credits = ' '.join(dict.fromkeys(e.get('attribution', '') for e in entries if e.get('attribution')))
    acknowledgments = ' '.join(dict.fromkeys(e.get('acknowledgment', '') for e in entries if e.get('acknowledgment')))
    details = ('Periodic recordings and archives, not a continuous live feed. ' +
               ' '.join(o['description'] for o in options) +
               f' Recording times, current source health, attribution and reuse terms: {base_url.rstrip("/")}/. ' +
               credits + ' ' + acknowledgments)
    text = ['---', 'name: Abyss', 'strategy: polling', 'polling_verb: get',
            'polling_url: ' + quote(base_url.rstrip('/') + '/catalog.json'),
            "no_screen_padding: 'yes'", "dark_mode: 'no'", 'refresh_interval: 240',
            'custom_fields:', '  - keyname: source_id', '    name: Underwater camera',
            '    field_type: select', '    description: ' + quote(details.strip()),
            '    default: ' + quote(catalog['default_source']), '    options:']
    text.extend('      - ' + quote(o['label']) + ': ' + quote(o['value']) for o in options)
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text('\n'.join(text) + '\n')
