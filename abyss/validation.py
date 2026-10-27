"""Technical source validation independent of release rights and Codex access.

Only metadata is retained. Frames live in a temporary directory, so this check
can run before permission to redistribute derived imagery has been established.
"""
import argparse
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from .imaging import quality, render
from .network import RangeVideo, RetrievalError, check_url, opener
from .pipeline import utcnow
from .publication import atomic_json
from .registry import load
from .video import extract


def classify_failure(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return 'upstream_http_error'
    if isinstance(exc, urllib.error.URLError):
        if 'tunnel connection failed' in str(exc.reason).lower():
            return 'infrastructure_proxy_tunnel'
        return 'network_path_error'
    if isinstance(exc, RetrievalError):
        return 'retrieval_constraint'
    return 'processing_error'


def validate(source, recording_url, *, max_bytes=64 * 1024 * 1024,
             maximum=4, interval=60):
    started = time.monotonic()
    github = os.environ.get('GITHUB_ACTIONS') == 'true'
    report = {
        'schema_version': 1, 'source_id': source['id'],
        'recording_url': recording_url, 'checked_at': utcnow(),
        'environment': 'github_actions' if github else 'local',
        'commit': os.environ.get('GITHUB_SHA') if github else None,
        'run_url': (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                    f"{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/"
                    f"{os.environ.get('GITHUB_RUN_ID')}") if github else None,
        'technical_status': 'failed', 'byte_budget': max_bytes,
        'rights_status': 'not_assessed', 'imagery_published': False,
        'scope': 'Exact recording access and extraction; not cadence, discovery or rights approval',
    }
    video = None
    try:
        check_url(recording_url, source['allowed_hosts'])
        if max_bytes < 1025 or not 1 <= maximum <= 48 or interval < 1:
            raise ValueError('Invalid byte budget, candidate count or interval')
        request = urllib.request.Request(recording_url, method='HEAD', headers={
            'User-Agent': 'AbyssOcean/0.1', 'Accept-Encoding': 'identity'})
        try:
            with opener(source['allowed_hosts']).open(request, timeout=25) as response:
                report['head'] = {
                    'status': response.status,
                    'content_type': response.headers.get('Content-Type'),
                    'content_length': response.headers.get('Content-Length'),
                    'accept_ranges': response.headers.get('Accept-Ranges'),
                }
        except urllib.error.HTTPError as exc:
            if exc.code not in (405, 501):
                raise
            report['head'] = {'status': exc.code, 'note': 'HEAD unsupported; test actual ranges'}
        video = RangeVideo(recording_url, source['allowed_hosts'], max_bytes)
        sample = video._fetch(0, 1023)
        if len(sample) != 1024:
            raise RetrievalError('Recording too short for the 1024-byte range probe')
        report['range'] = {'status': 206, 'requested': 'bytes=0-1023',
                           'bytes_received': len(sample), 'recording_bytes': video.total}
        head_size = report['head'].get('content_length')
        if head_size is not None and int(head_size) != video.total:
            raise RetrievalError('Recording length changed between HEAD and range probe')
        with tempfile.TemporaryDirectory(prefix='abyss-validate-') as tmp:
            with video.bridge() as url:
                frames, diagnostics = extract(url, tmp, interval=interval, maximum=maximum)
            report['extraction'] = diagnostics
            if video.error:
                raise RetrievalError(video.error)
            if diagnostics['candidates_extracted'] != diagnostics['candidates_requested']:
                raise RuntimeError('Not all requested frame seeks completed')
            report['frames'] = []
            for seconds, path in frames:
                with Image.open(path) as image:
                    metrics = quality(image)
                    rendered = render(image)
                    rendered.save(Path(tmp) / 'rendered.png')
                    with Image.open(Path(tmp) / 'rendered.png') as check:
                        check.verify()
                    report['frames'].append({
                        'frame_seconds': seconds, 'decoded_size': list(image.size),
                        'rendered_size': list(rendered.size), 'rendered_mode': rendered.mode,
                        'quality': metrics,
                    })
        report['technical_status'] = 'passed'
    except Exception as exc:
        report['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:2000]}
        if isinstance(exc, urllib.error.HTTPError):
            report['failure']['http_status'] = exc.code
        # Do not infer upstream downtime from a failed local/proxy/network path.
        report['upstream_availability'] = 'not_established_by_this_failure'
    finally:
        if video:
            report['transfer'] = {'bytes_downloaded': video.bytes_read,
                                  'upstream_requests': video.requests,
                                  'recording_bytes': video.total,
                                  'payload_fraction': video.bytes_read / video.total}
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', default='sources.json')
    parser.add_argument('--source', default='ooi-axial')
    parser.add_argument('--recording-url', required=True)
    parser.add_argument('--output', default='output/source-validation.json')
    parser.add_argument('--max-bytes', type=int, default=64 * 1024 * 1024)
    parser.add_argument('--candidates', type=int, default=4)
    parser.add_argument('--interval', type=float, default=60)
    args = parser.parse_args()
    matching = [s for s in load(args.registry) if s['id'] == args.source]
    if not matching:
        parser.error('Unknown source ID')
    report = validate(matching[0], args.recording_url, max_bytes=args.max_bytes,
                      maximum=args.candidates, interval=args.interval)
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['technical_status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
