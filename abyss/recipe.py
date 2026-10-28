"""Generate a native multi-select recipe from reviewed feeds with retained images."""
import json
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from .publication import read_json
from .about import OVERVIEW, SUMMARY, about_html


def generate(output, base_url, destination):
    parsed = urlsplit(base_url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('Recipe requires a public HTTPS base URL without query, fragment or credentials')
    catalog = read_json(Path(output) / 'public' / 'catalog.json', {})
    options = catalog.get('options', [])
    if not options:
        raise ValueError('No validated published sources; recipe dropdown cannot be generated yet')
    # YAML accepts JSON Unicode escapes. Keep the import file ASCII-safe even
    # when an importer guesses a legacy encoding instead of UTF-8.
    quote = lambda value: json.dumps(value, ensure_ascii=True)
    entries = [catalog.get('sources', {}).get(o['value'], {}) for o in options]
    credits = ' '.join(dict.fromkeys(e.get('attribution', '') for e in entries if e.get('attribution')))
    acknowledgments = ' '.join(dict.fromkeys(e.get('acknowledgment', '') for e in entries if e.get('acknowledgment')))
    details = ('Leave all feeds deselected to cycle through every feed. Select one to pin it, or several to cycle through that subset. '
               'Offline cameras keep their last best image. Periodic recordings and archives, not a continuous live feed. ' +
               f' <a href="{escape(base_url.rstrip("/") + "/#about", quote=True)}">Meet the cameras, explore the maps and read the source credits</a>.')
    text = ['---', 'name: Abyss', 'strategy: polling', 'polling_verb: get',
            'description: ' + quote(SUMMARY), 'recipe_overview: ' + quote(OVERVIEW),
            'polling_url: ' + quote(base_url.rstrip('/') + '/catalog.json'),
            "no_screen_padding: 'no'", "dark_mode: 'no'", 'framework_version: "3.4.4"',
            'refresh_interval: 15', 'serverless_language: python',
            'custom_fields:', '  - keyname: source_ids', '    name: Underwater cameras',
            '    field_type: select', '    multiple: true', '    optional: true',
            '    description: ' + quote(details.strip()),
            '    default: []', '    options:']
    text.extend('      - ' + quote(o['label'].replace('·', '-')) + ': ' + quote(o['value']) for o in options)
    text.extend(['  - keyname: show_qr', '    name: Show QR code', '    field_type: boolean',
                 '    optional: true', '    default: false',
                 '    description: "Full-screen view only: scan the bottom-right overlay to open this exact image or video recording. Off by default."'])
    text.extend(['  - keyname: about_abyss', '    name: About Abyss', '    field_type: author_bio',
                 '    description: ' + quote(about_html(credits, acknowledgments)),
                 '    github_url: https://github.com/nikokoren/abyss',
                 '    learn_more_url: ' + quote(base_url.rstrip('/') + '/#about')])
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text('\n'.join(text) + '\n', encoding='utf-8')
