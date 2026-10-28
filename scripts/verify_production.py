"""Verify the deployed Pages catalog and Offshore release from a GitHub runner."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from PIL import Image

from abyss.preferences import load_model
from abyss.registry import eligible, load


def verify(base_url, model):
    base_url = base_url.rstrip('/')
    parsed = urlsplit(base_url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Production verification requires a public HTTPS URL')

    def read(url, limit=64 * 1024 * 1024):
        if not url.startswith(base_url + '/'):
            raise ValueError('Expected a same-site published asset')
        with urlopen(url, timeout=45) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Published asset exceeds verification budget')
        return data

    nonce = str(time.time_ns())
    catalog = json.loads(read(base_url + '/catalog.json?verify=' + nonce))
    expected = {s['id'] for s in load('sources.json') if eligible(s)}
    assert set(catalog['sources']) == expected, 'Live camera set differs from the production registry'
    assert set(catalog['rotation_order']) == expected, 'Default rotation omits a camera'
    assert {o['value'] for o in catalog['options']} == expected, 'Recipe options omit a camera'
    offshore = catalog['sources']['ooi-oregon-offshore']
    assert offshore['preference']['status'] == 'active', 'Offshore preference model is inactive'
    assert offshore['preference']['model_id'] == model['model_id'], 'Offshore uses a different model'
    assert offshore['source_width'] == 5344 and offshore['source_height'] == 4008
    assert offshore['color_mode'] == 'RGB' and offshore['method'] == 'native'
    assert offshore['attribution_embedded'], 'Downloadable image lacks embedded credit'
    for name in ('Ocean Observatories Initiative', 'Woods Hole', 'University of Washington', 'National Science Foundation'):
        assert name in offshore['attribution']
    image = Image.open(io.BytesIO(read(offshore['display_image_url'])))
    image.load()
    assert image.size == (5344, 4008) and image.mode == 'RGB', 'Live image lost source resolution or colour'
    credited = Image.open(io.BytesIO(read(offshore['image_url'])))
    credited.load()
    assert credited.width == 5344 and credited.height > 4008 and credited.mode == 'RGB'
    about = read(base_url + '/about.html?verify=' + nonce).decode()
    settings = read(base_url + '/settings.yml?verify=' + nonce).decode()
    assert 'Four camera views, three research sites' in about and 'about 580 m' in about
    assert 'research-sites/oregon-offshore/' in about
    assert 'ooi-oregon-offshore' in settings and 'all four cameras' in settings
    assert 'framework_version: "3.4.4"' in settings and 'refresh_interval: 15' in settings
    return {'verified_at': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
            'base_url': base_url, 'camera_ids': sorted(expected), 'model_id': model['model_id'],
            'offshore_preference': offshore['preference'], 'original_url': offshore['original_url'],
            'image_url': offshore['image_url'], 'display_image_url': offshore['display_image_url'],
            'source_size': list(image.size), 'credited_size': list(credited.size),
            'color_mode': image.mode, 'about_and_recipe_verified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', default='output/production-verification.json')
    args = parser.parse_args()
    model = load_model(args.model)
    if not model:
        raise SystemExit('Expected preference model is unavailable')
    for attempt in range(8):
        try:
            report = verify(args.base_url, model)
            break
        except (AssertionError, OSError, ValueError, KeyError) as error:
            if attempt == 7:
                raise
            print(f'Waiting for deployed assets ({attempt + 1}/8): {error}', flush=True)
            time.sleep(15)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(path.read_text())


if __name__ == '__main__':
    main()
