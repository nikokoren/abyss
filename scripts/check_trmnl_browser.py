"""Check real Liquid output with the unmodified, released TRMNL 3.4.4 assets."""
import argparse
import copy
import functools
import hashlib
import json
import shutil
import sys
import tempfile
import threading
import io
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw
import qrcode
import zxingcpp
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_trmnl import LAYOUTS, catalog, render


def document(markup, device, orientation, layout, *, no_bleed=False, dark=False):
    view = f'<div class="view view--{layout}">{markup}</div>'
    if layout != 'full':
        mashup = {'half_vertical': '1Lx1R', 'half_horizontal': '1Tx1B', 'quadrant': '2x2'}[layout]
        # Real mashups have neighboring cells; they must not overlap ours.
        cells = 4 if layout == 'quadrant' else 2
        view = f'<div class="mashup mashup--{mashup}">{view * cells}</div>'
    mode = '1bit' if device == 'og' else '4bit'
    size = {'og': 'md', 'v2': 'lg', 'amazon_kindle_2024': 'sm'}[device]
    portrait = 'screen--portrait' if orientation == 'portrait' else ''
    padding = 'screen--no-bleed' if no_bleed else ''
    scheme = 'screen--dark-mode' if dark else ''
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Abyss native TRMNL preview</title>
<link rel="stylesheet" href="/css/3.4.4/plugins.css">
<script src="/js/3.4.4/plugins.js" defer></script>
<body class="trmnl"><div class="screen screen--{device} screen--{size} screen--{mode} {portrait} {padding} {scheme}">
{view}</div></body></html>'''


CHECK = '''() => {
  const rect = e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}; };
  const within = (a,b) => a.x>=b.x-1 && a.y>=b.y-1 && a.right<=b.right+1 && a.bottom<=b.bottom+1;
  const views = [...document.querySelectorAll('.view')];
  const errors=[];
  for (const view of views) {
    const v=rect(view), layout=view.querySelector('.layout'), bar=view.querySelector('.title_bar');
    if (!within(rect(layout),v)) errors.push('Layout exceeds view');
    if (!within(rect(bar),v)) errors.push('Title bar exceeds view');
    if (rect(layout).bottom>rect(bar).y+1) errors.push('Title bar overlaps layout');
    for (const el of view.querySelectorAll('img,span')) {
      if (!within(rect(el),v)) errors.push('Content exceeds view: '+el.textContent.trim().slice(0,80));
      if (el.tagName==='SPAN') {
        const range=document.createRange(); range.selectNodeContents(el);
        const r=range.getBoundingClientRect();
        if (r.width && !within({x:r.x,y:r.y,right:r.right,bottom:r.bottom},v)) errors.push('Text outside view: '+el.textContent.trim());
        // Bitmap font glyphs can exceed line-height without being clipped.
        if (['hidden','clip'].includes(getComputedStyle(el).overflowY) && el.scrollHeight>el.clientHeight+2 && !el.hasAttribute('data-clamp')) errors.push('Text clipped: '+el.textContent.trim());
      }
    }
    for (const el of view.querySelectorAll('img')) {
      if (!el.complete || el.naturalWidth===0) errors.push('Image failed');
      if (getComputedStyle(el).objectFit!=='contain') errors.push('Image would crop source notices');
      if (rect(el).h<40 || rect(el).w<40) errors.push('Image collapsed');
      if (!within(rect(el),rect(layout))) errors.push('Image outside layout');
    }
    for (const el of view.querySelectorAll('.label')) {
      if (getComputedStyle(el).fontFamily.includes('Times')) errors.push('Native typeface missing');
    }
  }
  for (let i=0;i<views.length;i++) for(let j=i+1;j<views.length;j++) {
    const a=rect(views[i]),b=rect(views[j]);
    if(Math.min(a.right,b.right)-Math.max(a.x,b.x)>1 && Math.min(a.bottom,b.bottom)-Math.max(a.y,b.y)>1) errors.push('Mashup cells overlap');
  }
  const view=views[0], image=view.querySelector('img');
  const qr=view.querySelector('img[alt^="Scan"]');
  if(qr) {
    const q=rect(qr), box=rect(qr.parentElement);
    if(getComputedStyle(qr).position!=='absolute') errors.push('QR is not an overlay');
    if(Math.abs(q.right-box.right)>1 || Math.abs(q.bottom-box.bottom)>1) errors.push('QR is not at bottom right');
  }
  const credit=view.querySelector('.label.w--full');
  return {errors,view:rect(view),image:image?rect(image):null,
    credit_color:credit?getComputedStyle(credit).color:null,
    canvas_color:getComputedStyle(document.querySelector('.screen')).backgroundColor,
    label_font:getComputedStyle(view.querySelector('.label')||view.querySelector('.description')||view.querySelector('.title_bar .title')).fontSize};
}'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework-root', type=Path, required=True)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--chromium', help='Use an installed Chromium instead of Playwright download')
    parser.add_argument('--output', type=Path, default=Path('output/validation/trmnl'))
    args = parser.parse_args()
    config = json.loads(Path('trmnl/framework.json').read_text())
    assets = args.framework_root.resolve() / 'public'
    css = assets / 'css' / config['tested_release'] / 'plugins.css'
    if not css.is_file():
        parser.error('Framework checkout must contain the published 3.4.4 assets')
    data = json.loads(args.catalog.read_text()) if args.catalog else catalog()
    data = copy.deepcopy(data)
    for camera in data['sources'].values():
        camera['image_url'] = '/ocean.png'
        camera['display_image_url'] = '/ocean.png'
        camera['qr_code_url'] = '/qr.png'
    if data.get('default_image'):
        data['default_image']['image_url'] = '/ocean.png'
        data['default_image']['display_image_url'] = '/ocean.png'
    args.output.mkdir(parents=True, exist_ok=True)
    cases = []
    for device in ('og', 'v2', 'amazon_kindle_2024'):
        for orientation in ('landscape', 'portrait'):
            for layout in LAYOUTS:
                cases.append((device, orientation, layout, 'available', data, None))
                cases.append((device, orientation, layout, 'qr', data, None))
                cases.append((device, orientation, layout, 'dark', data, None))
    for state in ('retained', 'unknown_time', 'empty', 'long_name'):
        changed = copy.deepcopy(data)
        if state == 'retained':
            for camera in changed['sources'].values():
                camera.update(available=False, stale=True)
            changed['default_image'].update(available=False, stale=True)
        elif state == 'unknown_time':
            for camera in changed['sources'].values():
                camera.update(captured_at=None, fixture=True)
        elif state == 'empty':
            changed = {'sources': {}, 'default_image': None}
        else:
            for camera in changed['sources'].values():
                camera['source_name'] = 'A much longer observatory name with a remote hydrothermal vent field'
                camera['location_label'] = 'International District with a much longer hydrothermal camera location'
        for orientation in ('landscape', 'portrait'):
            cases.append(('og', orientation, 'quadrant', state, changed,
                          changed.get('default_source') if state == 'retained' else None))
    # settings.yml requests no_screen_padding; exercise the corresponding host modifier.
    for orientation in ('landscape', 'portrait'):
        for layout in LAYOUTS:
            cases.append(('og', orientation, layout, 'no_bleed', data, None))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        qr_target = 'https://nikokoren.github.io/abyss/i/0123456789abcdef0123.html'
        qrcode.make(qr_target, error_correction=qrcode.constants.ERROR_CORRECT_M, border=4).save(root / 'qr.png')
        for name in ('css', 'js', 'fonts', 'images'):
            # Served locally for exact release testing, never copied into app source.
            if (assets / name).is_dir():
                (root / name).symlink_to(assets / name, target_is_directory=True)
        if args.image:
            shutil.copyfile(args.image, root / 'ocean.png')
        else:
            image = Image.new('RGB', (1920, 1080), (45, 140, 170))
            ImageDraw.Draw(image).text((20, 20), 'SYNTHETIC LAYOUT TEST', fill=0)
            image.save(root / 'ocean.png')
        for device, orientation, layout, state, context, selection in cases:
            name = f'{device}-{orientation}-{layout}-{state}'
            (root / (name + '.html')).write_text(document(render(layout, context, selection, show_qr=state in ('qr', 'dark')), device,
                                                       orientation, layout, no_bleed=state == 'no_bleed', dark=state == 'dark'))

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(root)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        reports = []
        try:
            with sync_playwright() as p:
                options = {'args': ['--no-sandbox']}
                if args.chromium:
                    options['executable_path'] = args.chromium
                browser = p.chromium.launch(**options)
                page = browser.new_page(viewport={'width': 1800, 'height': 1800})
                browser_errors = []
                page.on('pageerror', lambda e: browser_errors.append(str(e)))
                for device, orientation, layout, state, _, _ in cases:
                    name = f'{device}-{orientation}-{layout}-{state}'
                    browser_errors.clear()
                    page.goto(f'http://127.0.0.1:{server.server_port}/{name}.html', wait_until='networkidle')
                    page.evaluate('document.fonts.ready')
                    result = page.evaluate(CHECK)
                    qr_count = page.locator('img[alt^="Scan"]').count()
                    if qr_count and layout != 'full':
                        result['errors'].append('QR shown outside full-screen view')
                    if state in ('qr', 'dark') and layout == 'full':
                        crop = page.locator('img[alt^="Scan"]').first.screenshot()
                        decoded = zxingcpp.read_barcode(Image.open(io.BytesIO(crop)))
                        result['qr_decoded'] = decoded.text if decoded else None
                        if result['qr_decoded'] != qr_target:
                            result['errors'].append('QR code cannot be decoded at native display size')
                    if state == 'dark' and result['credit_color'] != 'rgb(255, 255, 255)':
                        result['errors'].append('Native credit text did not switch to white in dark mode')
                    if state == 'dark' and result['canvas_color'] != 'rgb(0, 0, 0)':
                        result['errors'].append('Native canvas did not switch to black in dark mode')
                    result.update(name=name, browser_errors=list(browser_errors))
                    reports.append(result)
                    page.locator('.screen').screenshot(path=str(args.output / (name + '.png')))
                    if result['errors'] or browser_errors:
                        raise AssertionError(name + ': ' + json.dumps(result))
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            (args.output / 'report.json').write_text(json.dumps({
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'framework': config, 'image': 'published ocean still' if args.image else 'synthetic test image',
                'framework_css_sha256': hashlib.sha256(css.read_bytes()).hexdigest(),
                'framework_js_sha256': hashlib.sha256((assets / 'js/3.4.4/plugins.js').read_bytes()).hexdigest(),
                'cases': reports}, indent=2) + '\n')
    print(f'Native Framework {config["tested_release"]}: {len(reports)} browser cases passed')


if __name__ == '__main__':
    main()
