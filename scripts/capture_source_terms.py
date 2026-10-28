"""Capture official OOI policy evidence; never approve a source automatically."""
import argparse
import hashlib
import json
import re
import subprocess
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen


HOSTS = {'oceanobservatories.org', 'www.oceanobservatories.org',
         'interactiveoceans.washington.edu'}
SEEDS = [
    'https://oceanobservatories.org/',
    'https://oceanobservatories.org/data/',
    'https://oceanobservatories.org/data/data-policy/',
    'https://oceanobservatories.org/how-to-cite-ooi-data/',
    'https://interactiveoceans.washington.edu/instruments/hd-video-camera/',
    'https://interactiveoceans.washington.edu/',
]
RELEVANT = re.compile(r'polic|terms|copyright|\bcite\b|citation|licen[cs]|acknowledg', re.I)
LIMIT = 2 * 1024 * 1024


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links = [], []
        self.hidden = 0
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'script', 'style', 'noscript'}:
            self.hidden += 1
        if tag in {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'section', 'footer'}:
            self.text.append('\n')
        if tag == 'a':
            self.anchor = [attrs.get('href', ''), []]

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript'}:
            self.hidden = max(0, self.hidden - 1)
        if tag == 'a' and self.anchor:
            self.links.append((self.anchor[0], ' '.join(self.anchor[1])))
            self.anchor = None

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)
            if self.anchor:
                self.anchor[1].append(data.strip())


def allowed(url):
    parts = urlsplit(url)
    return (parts.scheme == 'https' and parts.hostname in HOSTS
            and not parts.username and not parts.password and parts.port in {None, 443})


def capture(output, seeds, max_pages):
    output.mkdir(parents=True, exist_ok=True)
    queue, seen, records = deque(seeds), set(), []
    while queue and len(seen) < max_pages:
        url = urldefrag(queue.popleft())[0]
        if url in seen or not allowed(url):
            continue
        seen.add(url)
        record = {'url': url, 'checked_at': datetime.now(timezone.utc).isoformat()}
        try:
            request = Request(url, headers={'User-Agent': 'Abyss-source-terms-review/1.0'})
            with urlopen(request, timeout=30) as response:
                if not allowed(response.url):
                    raise ValueError('Policy redirected outside the official evidence hosts')
                body = response.read(LIMIT + 1)
                if len(body) > LIMIT:
                    raise ValueError('Policy response exceeds 2 MiB cap')
                content_type = response.headers.get_content_type()
                record.update(status=response.status, final_url=response.url,
                              content_type=content_type, sha256=hashlib.sha256(body).hexdigest())
            stem = f'{len(records) + 1:02d}-' + hashlib.sha256(url.encode()).hexdigest()[:12]
            if content_type == 'application/pdf':
                pdf = output / (stem + '.pdf')
                pdf.write_bytes(body)
                subprocess.run(['pdftotext', '-layout', str(pdf), str(output / (stem + '.txt'))],
                               check=True, timeout=30)
                record['document'] = pdf.name
            elif content_type in {'text/html', 'application/xhtml+xml'}:
                page = Page()
                page.feed(body.decode('utf-8', errors='replace'))
                text = '\n'.join(re.sub(r'\s+', ' ', line).strip()
                                 for line in ''.join(page.text).splitlines())
                (output / (stem + '.txt')).write_text(text, encoding='utf-8')
                links = [{'url': urldefrag(urljoin(record['final_url'], href))[0], 'label': label}
                         for href, label in page.links]
                record['links'] = links
                for link in links:
                    if allowed(link['url']) and RELEVANT.search(link['url'] + ' ' + link['label']):
                        queue.append(link['url'])
            elif content_type == 'text/plain':
                (output / (stem + '.txt')).write_bytes(body)
            else:
                raise ValueError('Expected a policy document, received ' + content_type)
            record['text'] = stem + '.txt'
        except Exception as exc:
            record['failure'] = f'{type(exc).__name__}: {exc}'
        records.append(record)
    report = {'schema_version': 1, 'purpose': 'Evidence capture only; human review required',
              'checked_at': datetime.now(timezone.utc).isoformat(), 'pages': records}
    (output / 'index.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{k: p[k] for k in ('url', 'status', 'text', 'failure') if k in p}
                      for p in records], indent=2))
    if not any(p.get('text') for p in records):
        raise SystemExit('No policy evidence retrieved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--url', action='append')
    parser.add_argument('--max-pages', type=int, default=18, choices=range(1, 31))
    args = parser.parse_args()
    capture(args.output, args.url or SEEDS, args.max_pages)
