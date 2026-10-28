"""Bound the published snapshot without deleting current/last-good camera assets."""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote

from PIL import Image

from .media_page import https_url, save_preview, write_page
from .publication import atomic_json, read_json

DEFAULT_BUDGET = 640 * 1024 * 1024


def local_file(public, url, base_url):
    if not isinstance(url, str):
        return None
    base = urlsplit(base_url.rstrip('/') + '/')
    value = urlsplit(url)
    if (value.scheme, value.netloc) != (base.scheme, base.netloc) or not value.path.startswith(base.path):
        return None
    relative = Path(unquote(value.path[len(base.path):]))
    if relative.is_absolute() or '..' in relative.parts:
        return None
    candidate = public / relative
    if not candidate.resolve().is_relative_to(public.resolve()) or candidate.is_symlink():
        return None
    return candidate


def files_for(public, observation, base_url):
    return {p for key in ('image_url', 'display_image_url')
            if (p := local_file(public, observation.get(key), base_url)) is not None and p.is_file()}


def full_present(public, observation, base_url, retained):
    required = [local_file(public, observation[key], base_url)
                for key in ('image_url', 'display_image_url') if observation.get(key)]
    return bool(required) and all(p is not None and p.is_file() and p in retained for p in required)


def migrate_pages(public, base_url, latest):
    """Rescue already-issued QR pages before their old full PNGs are retired."""
    folder = public / 'i'
    for page in sorted(folder.glob('*.html')):
        if (folder / (page.stem + '.json')).exists() or not re.fullmatch('[0-9a-f]{20}', page.stem):
            continue
        content = page.read_text()
        refs = [html.unescape(u) for u in re.findall(r'(?:src|poster|href)="([^"]+)"', content)]
        photos = [u for u in refs if (p := local_file(public, u, base_url)) is not None
                  and p.parent.parent == public / 'sources' and p.suffix == '.png' and p.exists()]
        if not photos:
            raise ValueError(f'Cannot preserve legacy QR frame: {page.name}')
        credited = re.search(r'<a href="([^"]+)">Download attributed still</a>', content)
        raw_url = photos[0]
        credit_url = html.unescape(credited[1]) if credited else photos[-1]
        source_id = Path(urlsplit(raw_url).path).parent.name
        original = re.search(r'<video[^>]+src="([^"]+)"', content)
        if original:
            video = html.unescape(original[1]); original_url = video.split('#')[0]
            seconds = float(urlsplit(video).fragment.removeprefix('t=') or 0)
        else:
            link = re.search(r'<a href="([^"]+)">Open original snapshot</a>', content)
            original_url = html.unescape(link[1]) if link else None
            seconds = 0
        captured = re.search(r'Recorded (\d{4}-\d\d-\d\dT[^<\s]+)', content)
        name = re.search(r'<h1>(.*?)</h1>', content)
        record = {k: v for k, v in latest.get(source_id, {}).items()
                  if k in ('source_name', 'source_type', 'location', 'depth_label', 'attribution', 'acknowledgment', 'license', 'timestamp_basis')}
        record.update(source_id=source_id, source_name=html.unescape(name[1]) if name else source_id,
                      original_url=original_url, frame_seconds=seconds,
                      captured_at=captured[1] if captured else None,
                      published_at=captured[1] if captured else '',
                      image_url=credit_url, display_image_url=raw_url,
                      view_url=base_url.rstrip('/') + '/i/' + page.name,
                      qr_code_url=base_url.rstrip('/') + '/i/' + page.stem + '.png',
                      preview_url=base_url.rstrip('/') + '/i/' + page.stem + '-preview.jpg')
        with Image.open(local_file(public, credit_url, base_url)) as image:
            save_preview(image, folder / (page.stem + '-preview.jpg'))
        write_page(public, record, base_url)


def retain(root, base_url, *, max_bytes=DEFAULT_BUDGET, versions_per_camera=2, previews_per_camera=12):
    if not https_url(base_url) or max_bytes < 1 or versions_per_camera < 1 or previews_per_camera < 1:
        raise ValueError('Retention needs an HTTPS base URL and positive limits')
    root = Path(root); public = root / 'public'
    protected = set(); protected_views = set(); latest = {}
    def protect(record):
        required = [local_file(public, record[key], base_url)
                    for key in ('image_url', 'display_image_url') if record.get(key)]
        if not required or any(p is None or not p.is_file() for p in required):
            raise ValueError('Current camera/session image is missing; deployment must preserve the previous site')
        return set(required)
    for path in sorted((public / 'sources').glob('*/latest.json')):
        data = read_json(path, {})
        latest[path.parent.name] = data
        protected |= protect(data)
        if data.get('view_url'):
            protected_views.add(data['view_url'])
        for session in read_json(path.parent / 'sessions.json', {}).get('sessions', []):
            protected |= protect(session)
            if session.get('view_url'):
                protected_views.add(session['view_url'])
    if sum(p.stat().st_size for p in protected) > max_bytes:
        raise ValueError('Current camera/session assets exceed retention budget; last-good images were not deleted')
    migrate_pages(public, base_url, latest)
    records = [(path, read_json(path, {})) for path in sorted((public / 'i').glob('*.json'))]
    records.sort(key=lambda item: item[1].get('published_at') or item[1].get('captured_at') or '', reverse=True)
    retained = set(protected); optional = []; previews = set(); counts = {}; preview_counts = {}
    for path, record in records:
        source = record.get('source_id', '')
        full = files_for(public, record, base_url)
        current = record.get('view_url') in protected_views
        if current:
            counts[source] = counts.get(source, 0) + 1
    for path, record in records:
        source = record.get('source_id', '')
        full = files_for(public, record, base_url)
        current = record.get('view_url') in protected_views
        if not current and full and counts.get(source, 0) < versions_per_camera:
            retained |= full; optional.append((record, full)); counts[source] = counts.get(source, 0) + 1
        preview = local_file(public, record.get('preview_url'), base_url)
        # Observations without retrievable original footage keep their preview.
        mandatory_preview = current or not https_url(record.get('original_url'))
        if preview and preview.exists() and (mandatory_preview or preview_counts.get(source, 0) < previews_per_camera):
            previews.add(preview); preview_counts[source] = preview_counts.get(source, 0) + 1
    photo_files = {p for p in (public / 'sources').glob('*/*.png')
                   if re.fullmatch('[0-9a-f]{20}\.png', p.name) and not p.is_symlink()}
    preview_files = set((public / 'i').glob('*-preview.jpg'))
    before = sum(p.stat().st_size for p in public.rglob('*') if p.is_file())
    other = before - sum(p.stat().st_size for p in photo_files | preview_files)
    def projected():
        return other + sum(p.stat().st_size for p in retained | previews)
    for record, photos in reversed(optional):
        if projected() <= max_bytes:
            break
        retained -= photos - protected
    for path, record in reversed(records):
        if projected() <= max_bytes:
            break
        preview = local_file(public, record.get('preview_url'), base_url)
        if preview in previews and record.get('view_url') not in protected_views and https_url(record.get('original_url')):
            previews.remove(preview)
    if projected() > max_bytes:
        raise ValueError('Protected assets and QR records exceed retention budget; no current image was deleted')
    deleted = photo_files - retained | preview_files - previews
    # Rewrite all destinations first, so no QR points at assets about to disappear.
    for path, record in records:
        full = files_for(public, record, base_url)
        full_available = full_present(public, record, base_url, retained)
        preview = local_file(public, record.get('preview_url'), base_url)
        write_page(public, record, base_url, full_available=full_available, preview_available=preview in previews)
    removed_bytes = sum(p.stat().st_size for p in deleted)
    for path in deleted:
        path.unlink()
    after = sum(p.stat().st_size for p in public.rglob('*') if p.is_file())
    report = {'schema_version': 1, 'budget_bytes': max_bytes, 'before_bytes': before, 'after_bytes': after,
              'deleted_files': len(deleted), 'deleted_bytes': removed_bytes,
              'protected_image_files': len(protected), 'observation_pages': len(records),
              'versions_per_camera': versions_per_camera, 'previews_per_camera': previews_per_camera,
              'budget_satisfied': after <= max_bytes}
    atomic_json(root / 'state' / 'retention.json', report)
    if after > max_bytes:
        raise ValueError('Final public bundle exceeds retention budget; deployment must not proceed')
    return report
