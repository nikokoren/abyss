"""Bounded public-source discovery on deployment runners; no imagery published."""
import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request

from capture_source_terms import Page
from abyss.network import opener, classify_failure


HOSTS = ['rawdata.oceanobservatories.org', 'oceanobservatories.org',
         'interactiveoceans.washington.edu', 'www.oceannetworks.ca',
         'oceannetworks.ca', 'data.oceannetworks.ca', 'www.mbari.org', 'mbari.org',
         'oceanexplorer.noaa.gov', 'oceanexploration.noaa.gov',
         'www.oceanexploration.noaa.gov']
LIMIT = 2 * 1024 * 1024
INTEREST = re.compile(r'camera|webcam|video|data.policy|terms|copyright|licen[cs]|reuse|acknowledg|data.access|live.stream', re.I)


def retrieve(url, output):
    name = hashlib.sha256(url.encode()).hexdigest()[:16]
    record = {'url': url, 'checked_at': datetime.now(timezone.utc).isoformat()}
    try:
        with opener(HOSTS).open(Request(url, headers={'User-Agent': 'Abyss-camera-research/1.0'}), timeout=25) as response:
            kind = response.headers.get_content_type()
            record.update(status=response.status, final_url=response.url, content_type=kind)
            if kind not in {'text/html', 'application/xhtml+xml', 'text/plain', 'application/json', 'application/pdf'}:
                raise ValueError('Expected metadata or policy, not ' + kind)
            body = response.read(LIMIT + 1)
            if len(body) > LIMIT:
                raise ValueError('Metadata exceeds 2 MiB cap')
        record.update(bytes_received=len(body), sha256=hashlib.sha256(body).hexdigest())
        if kind == 'application/pdf':
            pdf = output / (name + '.pdf')
            pdf.write_bytes(body)
            subprocess.run(['pdftotext', '-layout', str(pdf), str(output / (name + '.txt'))], check=True, timeout=30)
            record['document'] = pdf.name
        elif kind in {'text/html', 'application/xhtml+xml'}:
            page = Page()
            page.feed(body.decode('utf-8', errors='replace'))
            text = '\n'.join(line for line in (re.sub(r'\s+', ' ', l).strip()
                              for l in ''.join(page.text).splitlines()) if line)
            (output / (name + '.txt')).write_text(text)
            record['links'] = list({urldefrag(urljoin(record['final_url'], href))[0]: label
                                    for href, label in page.links}.items())
            record['image_links'] = [dict(i, url=urljoin(record['final_url'], i['url'])) for i in page.images]
            raw = body.decode('utf-8', errors='replace')
            record['embedded_media'] = sorted(set(re.findall(r'https?[^\s"<>]+\.(?:mp4|m3u8)(?:\?[^\s"<>]*)?', raw)))[:40]
        else:
            (output / (name + '.txt')).write_bytes(body)
        record['text'] = name + '.txt'
    except Exception as exc:
        record['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:1000]}
        if hasattr(exc, 'code'):
            record['failure']['http_status'] = exc.code
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path('docs/camera-research-targets.json').read_text())
    urls = list(config['pages'])
    now = datetime.now(timezone.utc)
    for camera in config['cameras']:
        base = camera['base_url']
        urls.append(base)
        urls.extend(urljoin(base, (now - timedelta(days=d)).strftime('%Y/%m/%d/')) for d in range(2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(lambda url: retrieve(url, args.output), dict.fromkeys(urls)))
        # One bounded follow-up for official camera and reuse-policy links.
        follow = []
        for page in pages:
            for url, label in page.get('links', []):
                parts = urlsplit(url)
                if (parts.scheme == 'https' and parts.hostname in HOSTS and
                        parts.hostname != 'rawdata.oceanobservatories.org' and
                        INTEREST.search(parts.path + ' ' + label) and
                        not re.search(r'\.(jpg|jpeg|png|gif|mp4|zip|tar)$', parts.path, re.I)):
                    follow.append(url)
        seen = {p['url'] for p in pages}
        follow = [u for u in dict.fromkeys(follow) if u not in seen][:20]
        pages.extend(pool.map(lambda url: retrieve(url, args.output), follow))
    report = {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'purpose': 'Camera discovery and rights evidence; no publication approval inferred',
              'run_url': None, 'targets': config, 'pages': pages, 'imagery_published': False}
    import os
    if os.environ.get('GITHUB_RUN_ID'):
        report['run_url'] = f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
    (args.output / 'index.json').write_text(json.dumps(report, indent=2) + '\n')
    for page in pages:
        print(page['url'], page.get('status', page.get('failure')))


if __name__ == '__main__':
    main()
