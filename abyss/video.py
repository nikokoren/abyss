import json
import subprocess
from pathlib import Path
from PIL import Image


def command(args, timeout=60):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr.decode(errors="replace")[-1200:]}')
    return result.stdout


def probe(url):
    data = json.loads(command(['ffprobe', '-v', 'error', '-rw_timeout', '25000000',
                              '-format_whitelist', 'mov', '-show_format', '-show_streams', '-of', 'json', url]))
    duration = float(data.get('format', {}).get('duration', 0))
    if not 1 <= duration <= 86400:
        raise ValueError('Missing or unsupported recording duration')
    streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
    if not streams or max(s.get('width', 0) * s.get('height', 0) for s in streams) > 33_177_600:
        raise ValueError('Missing or excessively large video stream')
    return duration, streams[0].get('codec_name')


def extract(url, directory, interval=60, maximum=12):
    if not 1 <= maximum <= 48 or interval < 1:
        raise ValueError('Candidate count must be 1..48 and interval >= 1 second')
    duration, codec = probe(url)
    # Uniformly cover the pan; interval sets an upper bound on sampling density.
    count = min(maximum, max(1, int(duration // interval)))
    positions = [duration * (i + .5) / count for i in range(count)]
    return extract_positions(url, directory, positions, duration=duration, codec=codec)


def extract_positions(url, directory, positions, *, duration, codec, prefix='candidate'):
    if not positions or len(positions) > 48 or any(not 0 <= p < duration for p in positions):
        raise ValueError('Invalid frame positions')
    frames = []
    errors = []
    for index, seconds in enumerate(positions):
        path = Path(directory) / f'{prefix}-{index:02}.png'
        try:
            command(['ffmpeg', '-v', 'error', '-nostdin', '-threads', '2', '-rw_timeout', '25000000',
                     '-ss', str(seconds), '-format_whitelist', 'mov', '-i', url, '-map', '0:v:0', '-frames:v', '1',
                     '-vf', 'scale=960:600:force_original_aspect_ratio=decrease', '-threads', '2', '-y', str(path)])
            with Image.open(path) as image:
                image.load()
                if min(image.size) < 64:
                    raise ValueError('Extracted frame too small')
            frames.append((seconds, path))
        except Exception as exc:
            errors.append(str(exc))
    if not frames:
        raise RuntimeError('No candidate frames extracted: ' + '; '.join(errors)[:1500])
    return frames, {'duration_seconds': duration, 'codec': codec, 'candidates_requested': len(positions),
                    'candidates_extracted': len(frames), 'extraction_errors': errors}
