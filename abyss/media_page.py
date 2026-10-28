"""Stable, observation-specific QR pages with bounded full-resolution assets."""
import hashlib
import json
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import qrcode


RECORD_KEYS = ('source_id', 'source_name', 'source_type', 'location', 'depth_label',
               'original_url', 'frame_seconds', 'captured_at', 'recorded_at', 'published_at',
               'attribution', 'acknowledgment', 'license', 'timestamp_basis', 'image_url',
               'attribution_url', 'license_url', 'data_doi',
               'display_image_url', 'view_url', 'qr_code_url', 'preview_url')


def https_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme == 'https' and parsed.netloc and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def save_preview(image, path):
    preview = image.convert('RGB')
    preview.thumbnail((1200, 900))
    preview.save(path, format='JPEG', quality=88, optimize=True)


def render_page(metadata, base_url, *, full_available=True, preview_available=True):
    full = metadata.get('display_image_url') or metadata['image_url']
    preview = metadata.get('preview_url') if preview_available else None
    original = https_url(metadata.get('original_url'))
    is_video = bool(original and urlsplit(original).path.lower().endswith('.mp4'))
    image = preview or (full if full_available else (original if not is_video else None))
    title = escape(metadata.get('source_name') or 'Abyss')
    photo = escape(image, quote=True) if image else None
    if is_video:
        seconds = max(0, float(metadata.get('frame_seconds') or 0))
        video = escape(original.split('#')[0] + f'#t={seconds:g}', quote=True)
        poster = f' poster="{photo}"' if photo else ''
        media = f'<video controls playsinline preload="metadata"{poster} src="{video}"></video>'
        media += f'<p><a href="{video}">Open original video at {seconds:g} seconds</a></p>'
    else:
        media = f'<img src="{photo}" alt="{title}">' if photo else ''
        if original:
            media += f'<p><a href="{escape(original, quote=True)}">Open original snapshot at full resolution</a></p>'
    if full_available:
        links = (f'<a href="{escape(full, quote=True)}">Open the exact displayed still at full resolution</a> · '
                 f'<a href="{escape(metadata["image_url"], quote=True)}">Download attributed still</a>')
    elif preview:
        links = f'<a href="{escape(preview, quote=True)}">Open saved frame preview</a>'
    else:
        links = 'The original footage for this observation is linked above.'
    text = lambda key: escape(str(metadata.get(key) or ''))
    citations = ' · '.join(f'<a href="{escape(url, quote=True)}">{label}</a>'
                           for key, label in (('attribution_url', 'Source credit'), ('license_url', 'Reuse terms'), ('data_doi', 'Dataset DOI'))
                           if (url := https_url(metadata.get(key))))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Abyss · {title}</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:auto;padding:24px;background:#071b21;color:#e2ece5}}img,video{{display:block;width:100%;height:auto}}a{{color:#c0ded0}}p{{line-height:1.5}}</style>
<h1>{title}</h1><p>{text('location')} · {text('depth_label')}</p>
<p>Recorded {text('captured_at') or 'time unknown'}{(' (UTC assumed from filename)' if metadata.get('timestamp_basis') == 'filename_assumed_utc' else '')}</p>
{media}<p>{links}</p><p>{text('attribution')}</p><p>{text('acknowledgment')}</p><p>{text('license')}</p><p>{citations}</p>
<p><a href="{escape(base_url.rstrip('/') + '/', quote=True)}">Abyss · current cameras and source terms</a></p></html>'''


def write_page(public, metadata, base_url, *, full_available=True, preview_available=True):
    from .publication import atomic_json
    token = Path(urlsplit(metadata['view_url']).path).stem
    if len(token) != 20 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Invalid observation page identity')
    folder = Path(public) / 'i'
    folder.mkdir(parents=True, exist_ok=True)
    page = render_page(metadata, base_url, full_available=full_available, preview_available=preview_available)
    (folder / (token + '.html')).write_text(page, encoding='utf-8')
    record = {k: metadata[k] for k in RECORD_KEYS if k in metadata}
    record.update(schema_version=1, full_available=full_available, preview_available=preview_available)
    atomic_json(folder / (token + '.json'), record)
    # Refresh cached observations too: their QR destination stays unchanged.
    # One white module is the minimum verified against the native dark canvas.
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=1)
    code.add_data(metadata['view_url'])
    code.make(fit=True)
    code.make_image(fill_color='black', back_color='white').save(folder / (token + '.png'))


def publish_media_page(public, metadata, base_url, *, preview_image=None):
    identity = [metadata['image_url'], metadata.get('original_url'), metadata.get('frame_seconds'),
                metadata.get('source_id'), metadata.get('captured_at')]
    token = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20]
    folder = Path(public) / 'i'
    folder.mkdir(parents=True, exist_ok=True)
    view_url = base_url.rstrip('/') + '/i/' + token + '.html'
    metadata.update(view_url=view_url, qr_code_url=base_url.rstrip('/') + '/i/' + token + '.png')
    if preview_image is not None:
        save_preview(preview_image, folder / (token + '-preview.jpg'))
        metadata['preview_url'] = base_url.rstrip('/') + '/i/' + token + '-preview.jpg'
    write_page(public, metadata, base_url)
