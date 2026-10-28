"""Capped retrieval and decoding of immutable camera snapshots."""
import io
from pathlib import Path
from urllib.request import Request

from PIL import Image, ImageOps

from .network import RetrievalError, check_url, opener


def download_image(recording, source, directory, budget, index):
    url = recording['url']
    check_url(url, source['allowed_hosts'])
    received = b''
    with budget.lock:
        cap = min(4 * 1024 * 1024, budget.remaining)
        if cap < 1:
            raise RetrievalError('Image byte budget exhausted')
        request = Request(url, headers={'User-Agent': 'AbyssOcean/0.1', 'Accept-Encoding': 'identity'})
        with opener(source['allowed_hosts']).open(request, timeout=25) as response:
            budget.requests += 1
            if response.status != 200:
                raise RetrievalError('Image retrieval requires HTTP 200')
            kind = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            if kind not in {'image/jpeg', 'image/png', 'application/octet-stream'}:
                raise RetrievalError('Snapshot is not a supported image response')
            declared = response.headers.get('Content-Length')
            length = int(declared) if declared is not None else None
            if length is not None and (length < 1 or length > cap):
                raise RetrievalError('Image exceeds remaining byte budget or 4 MiB per-image cap')
            received = response.read(cap)
            budget.used += len(received)
            if length is not None and len(received) != length:
                raise RetrievalError('Truncated image response')
            if length is None and len(received) == cap:
                raise RetrievalError('Image reached byte cap without a declared complete length')
    with Image.open(io.BytesIO(received)) as image:
        if (image.format not in {'JPEG', 'PNG'} or image.width < 64 or image.height < 64
                or image.width * image.height > 16_777_216 or getattr(image, 'n_frames', 1) != 1):
            raise RetrievalError('Unsupported snapshot format, dimensions or animation')
        image.verify()
    with Image.open(io.BytesIO(received)) as image:
        image.load()
        path = Path(directory) / f'r{index}-snapshot.png'
        ImageOps.exif_transpose(image).convert('RGB').save(path)
        return path, {'bytes_downloaded': len(received), 'codec': image.format,
                      'decoded_size': list(image.size), 'content_type': kind, 'status': 200}
