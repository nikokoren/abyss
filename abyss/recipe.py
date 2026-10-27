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
    text = ['---', 'name: Ambient Ocean', 'strategy: polling', 'polling_verb: get',
            'polling_url: ' + quote(base_url.rstrip('/') + '/catalog.json'),
            "no_screen_padding: 'yes'", "dark_mode: 'no'", 'refresh_interval: 240',
            'custom_fields:', '  - keyname: source_id', '    name: Underwater camera',
            '    field_type: select', '    description: ' + quote('Periodic footage and archives, never implied live. ' + ' '.join(o['description'] for o in options)),
            '    default: ' + quote(catalog['default_source']), '    options:']
    text.extend('      - ' + quote(o['label']) + ': ' + quote(o['value']) for o in options)
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text('\n'.join(text) + '\n')
