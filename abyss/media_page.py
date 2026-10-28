"""Immutable, first-party QR destinations for the exact published observation."""
import hashlib
import json
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import qrcode


def https_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme == 'https' and parsed.netloc and not parsed.username and not parsed.password else None


def publish_media_page(public, metadata, base_url):
    # A source's latest.json moves; this URL must keep opening the frame that
    # the device displayed, even after a newer best image is published.
    identity = [metadata['image_url'], metadata.get('original_url'), metadata.get('frame_seconds'),
                metadata.get('source_id'), metadata.get('captured_at')]
    token = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20]
    folder = Path(public) / 'i'
    folder.mkdir(parents=True, exist_ok=True)
    view_url = base_url.rstrip('/') + '/i/' + token + '.html'
    image = escape(metadata.get('display_image_url') or metadata['image_url'], quote=True)
    credited = escape(metadata['image_url'], quote=True)
    title = escape(metadata.get('source_name') or 'Abyss')
    original = https_url(metadata.get('original_url'))
    if original and metadata.get('source_type') != 'snapshot' and urlsplit(original).path.lower().endswith('.mp4'):
        seconds = max(0, float(metadata.get('frame_seconds') or 0))
        video = escape(original.split('#')[0] + f'#t={seconds:g}', quote=True)
        media = f'<video controls playsinline preload="metadata" poster="{image}" src="{video}"></video>'
        media += f'<p><a href="{video}">Open original video at {seconds:g} seconds</a></p>'
    else:
        media = f'<a href="{image}"><img src="{image}" alt="{title}"></a>'
        if original:
            media += f'<p><a href="{escape(original, quote=True)}">Open original snapshot</a></p>'
    text = lambda key: escape(str(metadata.get(key) or ''))
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Abyss · {title}</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:auto;padding:24px;background:#071b21;color:#e2ece5}}img,video{{display:block;width:100%;height:auto}}a{{color:#c0ded0}}p{{line-height:1.5}}</style>
<h1>{title}</h1><p>{text('location')} · {text('depth_label')}</p>
<p>Recorded {text('captured_at') or 'time unknown'}{(' (UTC assumed from filename)' if metadata.get('timestamp_basis') == 'filename_assumed_utc' else '')}</p>
{media}<p><a href="{image}">Open the exact displayed still at full resolution</a> · <a href="{credited}">Download attributed still</a></p>
<p>{text('attribution')}</p><p>{text('acknowledgment')}</p><p>{text('license')}</p>
<p><a href="{escape(base_url.rstrip('/') + '/', quote=True)}">Abyss · current cameras and source terms</a></p></html>'''
    (folder / (token + '.html')).write_text(page)
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=4)
    code.add_data(view_url)
    code.make(fit=True)
    code.make_image(fill_color='black', back_color='white').save(folder / (token + '.png'))
    metadata.update(view_url=view_url, qr_code_url=base_url.rstrip('/') + '/i/' + token + '.png')
