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
from concurrent.futures import ThreadPoolExecutor


HOSTS = {'oceanobservatories.org', 'www.oceanobservatories.org',
         'interactiveoceans.washington.edu', 'www.nsf.gov', 'nsf.gov',
         'www.washington.edu'}
SEEDS = [
    'https://oceanobservatories.org/how-to-use-acknowledge-and-cite-data/',
    'https://oceanobservatories.org/wp-content/uploads/2022/12/1102-00020_Data_User_Terms_Conditions_OOI_2019-01-02_Ver_2-00.pdf',
    'https://interactiveoceans.washington.edu/instruments/high-definition-video-camera/',
    'https://interactiveoceans.washington.edu/research-sites/axial-caldera/ashes/',
    'https://oceanobservatories.org/site-list/',
    'https://www.nsf.gov/policies/logos.jsp',
    'https://www.washington.edu/online/privacy/',
    'https://oceanobservatories.org/array/cabled-axial-seamount-array/',
    'https://oceanobservatories.org/array/cabled-continental-margin-array/',
    'https://oceanobservatories.org/regional-cabled-array/',
    'https://interactiveoceans.washington.edu/research-sites/axial-caldera/international-district/',
    'https://interactiveoceans.washington.edu/research-sites/southern-hydrate-ridge/',
]
RELEVANT = re.compile(r'polic|terms|copyright|\bcite\b|citation|licen[cs]|acknowledg', re.I)
LIMIT = 2 * 1024 * 1024
GRAPHICS = [
    ('Axial Seamount array illustration', 'https://oceanobservatories.org/wp-content/uploads/2020/10/CEV-OOI-CabledArray-Axialt-scaled.jpg'),
    ('Continental margin array illustration', 'https://oceanobservatories.org/wp-content/uploads/2020/10/CEV-OOI-CabledArray-ContinentalMargint-scaled.jpg'),
    ('Regional Cabled Array map', 'https://oceanobservatories.org/wp-content/uploads/2023/09/OOI_Map_Cabled_Array-OPTIMIZED.png'),
    ('ASHES site map', 'https://s3-us-west-2.amazonaws.com/media.ooica.net/wp-content/uploads/2020/08/06193730/ASHES-Map-2020.png'),
    ('Tiny Towers site map', 'https://s3-us-west-2.amazonaws.com/media.ooica.net/wp-content/uploads/2020/08/06193821/Tiny-Towers-Hydrothermal-Field-Map-2020.png'),
    ('Southern Hydrate Ridge site map', 'https://s3.us-west-2.amazonaws.com/media.ooica.net/wp-content/uploads/2021/01/28232704/Southern-Hydrate-Map.png'),
]


def check_graphic(item):
    """Verify a graphic link without copying website artwork into our release."""
    name, url = item
    record = {'name': name, 'url': url, 'checked_at': datetime.now(timezone.utc).isoformat()}
    try:
        request = Request(url, method='HEAD', headers={'User-Agent': 'Abyss-source-context/1.0'})
        with urlopen(request, timeout=15) as response:
            if response.url != url:
                raise ValueError('Graphic redirected; review the destination separately')
            record.update(status=response.status, content_type=response.headers.get_content_type(),
                          content_length=response.headers.get('Content-Length'))
            if not record['content_type'].startswith('image/'):
                raise ValueError('Graphic URL did not return an image')
    except Exception as exc:
        record['failure'] = f'{type(exc).__name__}: {exc}'
    return record


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.images = [], [], []
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
        if tag == 'img':
            self.images.append({'url': attrs.get('src', ''), 'alt': attrs.get('alt', '')})

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
                text = '\n'.join(line for line in (re.sub(r'\s+', ' ', line).strip()
                                 for line in ''.join(page.text).splitlines()) if line)
                (output / (stem + '.txt')).write_text(text, encoding='utf-8')
                links = [{'url': urldefrag(urljoin(record['final_url'], href))[0], 'label': label}
                         for href, label in page.links]
                record['links'] = links
                record['image_links'] = [dict(i, url=urljoin(record['final_url'], i['url']))
                                         for i in page.images]
                record['logo_images'] = [dict(i, url=urljoin(record['final_url'], i['url']))
                                         for i in page.images if 'logo' in str(i).lower()]
                for link in links:
                    if (allowed(link['url']) and 'cookie' not in link['url']
                            and RELEVANT.search(link['url'] + ' ' + link['label'])):
                        queue.append(link['url'])
            elif content_type == 'text/plain':
                (output / (stem + '.txt')).write_bytes(body)
            else:
                raise ValueError('Expected a policy document, received ' + content_type)
            record['text'] = stem + '.txt'
        except Exception as exc:
            record['failure'] = f'{type(exc).__name__}: {exc}'
        records.append(record)
    with ThreadPoolExecutor(max_workers=3) as pool:
        graphics = list(pool.map(check_graphic, GRAPHICS))
    report = {'schema_version': 1, 'purpose': 'Evidence capture only; human review required',
              'checked_at': datetime.now(timezone.utc).isoformat(), 'pages': records,
              'graphic_links': graphics, 'graphics_copied': False}
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
