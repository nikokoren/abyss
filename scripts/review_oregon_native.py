"""Recheck held Oregon cameras using fresh RGB frames and native-layout previews."""
import argparse
import functools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from html import escape

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from abyss.adapters import discover_many
from abyss.about import OOI_ACKNOWLEDGMENT
from abyss.imaging import quality, render_for_source
from abyss.network import TransferBudget, classify_failure
from abyss.pipeline import utcnow
from abyss.registry import load
from abyss.stills import download_image
from check_trmnl_browser import document, CHECK
from test_trmnl import render

IDS = ('ooi-oregon-shelf', 'ooi-oregon-offshore')
COUNT, SPACING, BUDGET = 6, 3600, 144 * 1024 * 1024


def quantize(source, destination, depth):
    # Match TRMNLP ImageQuantizer's image-dither path, without Abyss tone mapping.
    command = ['magick'] if shutil.which('magick') else ['convert']
    options = (['-dither', 'FloydSteinberg', '-remap', 'pattern:gray50'] if depth == 1 else
               ['-colorspace', 'Gray', '-dither', 'FloydSteinberg', '-posterize', str(2 ** depth)])
    subprocess.run(command + [str(source), *options, '-alpha', 'off', '-depth', str(depth),
                              '-type', 'Palette', '-define', 'png:compression-level=9',
                              '-strip', str(destination)], check=True, timeout=40)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--framework-root', type=Path, required=True)
    parser.add_argument('--chromium')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'schema_version': 1, 'checked_at': utcnow(), 'commit': os.environ.get('GITHUB_SHA'),
              'run_url': f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
                         if os.environ.get('GITHUB_RUN_ID') else None,
              'scope': 'Fresh-frame and native-layout preview review; does not enable cameras',
              'sampling': {'snapshots_per_camera': COUNT, 'minimum_spacing_seconds': SPACING,
                           'max_bytes_per_camera': BUDGET, 'production_limits_unchanged': True},
              'rendering': 'Official TRMNL 3.4.4 assets plus TRMNLP ImageQuantizer steps. Preview only; not an account or physical-device render.',
              'quantizer_reference': 'https://github.com/usetrmnl/trmnlp/blob/30e770ba7da3f2a195aa70cd1571a35c6013947f/lib/trmnlp/image_quantizer.rb',
              'sources': []}
    fragments = ['<!doctype html><html lang="en"><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<title>Oregon camera native-preview recheck</title>'
                 '<style>body{font:16px system-ui;max-width:1200px;margin:auto;padding:24px}img{display:block;max-width:100%;height:auto}figure{margin:24px 0}p{line-height:1.5}</style>'
                 '<h1>Oregon camera recheck</h1><p>Six snapshots per camera, at least an hour apart. '
                 'Colour thumbnails and native-layout 1-bit / 4-bit previews. Production feeds remain unchanged.</p>']
    sources = {s['id']: s for s in load('sources.json')}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ('css', 'js', 'fonts'):
            (root / name).symlink_to((args.framework_root / 'public' / name).resolve(), target_is_directory=True)

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(root)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                launch = {'args': ['--no-sandbox']}
                if args.chromium:
                    launch['executable_path'] = args.chromium
                browser = playwright.chromium.launch(**launch)
                page = browser.new_page(viewport={'width': 1900, 'height': 1500})
                for source_id in IDS:
                    source = sources[source_id]
                    validation = source['validation']
                    if (source['adapter'] != 'ooi_image_directory' or not validation.get('terms_reviewed_at')
                            or validation.get('rights_status') != 'approved_attributed_derived_stills'):
                        raise ValueError('Recheck requires an explicitly rights-reviewed OOI snapshot source')
                    result = {'source_id': source_id, 'camera': source['name'], 'depth': source['depth_label'],
                              'previous_status': source['status'], 'snapshots': [], 'previews': [],
                              **{k: source[k] for k in ('attribution', 'acknowledgment', 'license_url', 'data_doi')}}
                    report['sources'].append(result)
                    fragments.append(f'<h2>{source["name"]} / {source["depth_label"]}</h2>')
                    budget = TransferBudget(BUDGET)
                    winner = None
                    try:
                        records = discover_many(source, limit=COUNT, min_spacing_seconds=SPACING)
                        for index, recording in enumerate(records):
                            item = {'recording': recording}
                            result['snapshots'].append(item)
                            try:
                                path, details = download_image(recording, source, root, budget, index)
                                with Image.open(path) as image:
                                    metrics = quality(image)
                                    item.update(details, quality=metrics)
                                    preview = render_for_source(image, source, method='native')
                                    preview.thumbnail((1280, 1000))
                                    name = f'{source_id}-{index:02d}-colour.jpg'
                                    preview.save(args.output / name, quality=88, optimize=True)
                                    item['colour_preview'] = name
                                    fragments.append(f'<figure><img src="{name}" alt="{source["name"]} snapshot {index + 1}">'
                                                     f'<figcaption>{recording["recorded_at"]} / quality {metrics["score"]:.3f}</figcaption></figure>')
                                    if winner is None or metrics['score'] > winner['quality']['score']:
                                        winner = {'recording': recording, 'quality': metrics}
                                        image.save(root / (source_id + '.png'))
                            except Exception as exc:
                                item['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:1000]}
                        result.update(bytes_downloaded=budget.used, requests=budget.requests,
                                      decoded_count=sum('quality' in x for x in result['snapshots']),
                                      best=winner)
                        if winner is None:
                            raise RuntimeError('No snapshots decoded')
                        camera = dict(source, source_id=source_id, source_name=source['name'],
                                      image_url='/' + source_id + '.png', display_image_url='/' + source_id + '.png',
                                      display_credit=' | '.join(source.get('image_credit_lines', [])),
                                      available=True, stale=False, fixture=False)
                        data = {'sources': {source_id: camera}, 'default_source': source_id, 'default_image': camera}
                        for device, depth in [('og', 1), ('v2', 4)]:
                            for dark in (False, True):
                                stem = f'{source_id}-{device}-{"dark" if dark else "light"}'
                                (root / (stem + '.html')).write_text(document(render('full', data, source_id), device,
                                                                             'landscape', 'full', dark=dark))
                                page.goto(f'http://127.0.0.1:{server.server_port}/{stem}.html', wait_until='networkidle')
                                page.evaluate('document.fonts.ready')
                                checks = page.evaluate(CHECK)
                                if checks['errors']:
                                    raise RuntimeError(str(checks['errors']))
                                raw = root / (stem + '-raw.png')
                                page.locator('.screen').screenshot(path=str(raw))
                                name = stem + '.png'
                                quantize(raw, args.output / name, depth)
                                result['previews'].append({'image': name, 'device': device, 'depth': depth,
                                                           'dark': dark, 'layout_checks': checks})
                                fragments.append(f'<h3>{device} / {depth}-bit / {"dark" if dark else "light"}</h3>'
                                                 f'<img src="{name}" alt="{source["name"]} native-layout preview">')
                        print(source_id, result['decoded_count'], budget.used, winner['quality']['score'], flush=True)
                    except Exception as exc:
                        result['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:1000]}
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    fragments.append('<footer><p>Data: Ocean Observatories Initiative / WHOI OOI Program Office / '
                     'University of Washington; supported by U.S. NSF 2244833.</p><p>' +
                     escape(OOI_ACKNOWLEDGMENT) + '</p><p>'
                     '<a href="https://oceanobservatories.org/how-to-use-acknowledge-and-cite-data/">'
                     'OOI credit and reuse terms</a>. Source credit implies no endorsement. '
                     'For ambient viewing; not for operational or decision-making use.</p></footer>')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'index.html').write_text('\n'.join(fragments) + '</html>', encoding='utf-8')
    if any(s.get('failure') or s['decoded_count'] < 2 for s in report['sources']):
        raise SystemExit('One or more cameras did not complete the preview recheck; inspect report.json')


if __name__ == '__main__':
    main()
