"""Capped retrieval and decoding of immutable camera snapshots."""
import io
from pathlib import Path
from urllib.request import Request

from PIL import Image, ImageOps, ImageFile

from .network import RangeVideo, RetrievalError, check_url, opener


def probe_image(recording, source):
    """Read at most 128 KiB to measure JPEG headers before choosing a budget."""
    video = RangeVideo(recording['url'], source['allowed_hosts'], 128 * 1024)
    header = video._fetch(0, min(video.total - 1, 65535))
    parser = ImageFile.Parser()
    parser.feed(header)
    return {'recording_bytes': video.total, 'header_bytes_downloaded': video.bytes_read,
            'format': parser.image.format if parser.image else None,
            'decoded_size': list(parser.image.size) if parser.image else None}


def download_image(recording, source, directory, budget, index):
    url = recording['url']
    check_url(url, source['allowed_hosts'])
    received = b''
    with budget.lock:
        image_limit = min(source.get('max_image_bytes', 4 * 1024 * 1024), 32 * 1024 * 1024)
        cap = min(image_limit, budget.remaining)
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
                raise RetrievalError(f'Image size {length} exceeds available {cap} bytes (image cap {image_limit})')
            received = response.read(cap)
            budget.used += len(received)
            if length is not None and len(received) != length:
                raise RetrievalError('Truncated image response')
            if length is None and len(received) == cap:
                raise RetrievalError('Image reached byte cap without a declared complete length')
    with Image.open(io.BytesIO(received)) as image:
        if (image.format not in {'JPEG', 'PNG'} or image.width < 64 or image.height < 64
                or image.width * image.height > min(source.get('max_image_pixels', 16_777_216), 32_000_000)
                or getattr(image, 'n_frames', 1) != 1):
            raise RetrievalError('Unsupported snapshot format, dimensions or animation')
        image.verify()
    with Image.open(io.BytesIO(received)) as image:
        original_size = list(image.size)
        # Native JPEG decoder scaling keeps the full frame and avoids allocating
        # a full-resolution RGB buffer for a 21 MP camera image destined for 800px.
        image.draft('RGB', (1200, 900))
        image.load()
        path = Path(directory) / f'r{index}-snapshot.png'
        ImageOps.exif_transpose(image).convert('RGB').save(path)
        return path, {'bytes_downloaded': len(received), 'codec': image.format,
                      'decoded_size': list(image.size), 'original_size': original_size,
                      'content_type': kind, 'status': 200}
