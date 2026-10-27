"""Bounded HTTPS access and a byte-metered HTTP-range bridge for FFmpeg.

FFmpeg only connects to loopback; upstream traffic uses urllib's inherited
HTTPS proxy and CA trust. Never disable TLS checks or fetch an entire MP4.
"""
import contextlib
import re
import socket
import threading
import urllib.request
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class RetrievalError(RuntimeError):
    pass


def check_url(url, hosts):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in hosts or p.username or p.password or p.port not in (None, 443):
        raise RetrievalError('URL outside source HTTPS allowlist')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def opener(hosts):
    return urllib.request.build_opener(SafeRedirect(hosts))


def read_small(url, hosts, limit=2_000_000):
    check_url(url, hosts)
    req = urllib.request.Request(url, headers={'User-Agent': 'AbyssOcean/0.1', 'Accept-Encoding': 'identity'})
    with opener(hosts).open(req, timeout=25) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise RetrievalError('Discovery page exceeds size limit')
        return data


class RangeVideo:
    block_size = 256 * 1024

    def __init__(self, url, hosts, max_bytes=64 * 1024 * 1024):
        check_url(url, hosts)
        self.url, self.hosts, self.max_bytes = url, hosts, max_bytes
        self.bytes_read = self.requests = 0
        self.total = None
        self.etag = None
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.error = None
        self._fetch(0, 0)

    def _fetch(self, start, end):
        if self.bytes_read + end - start + 1 > self.max_bytes:
            raise RetrievalError('Video byte budget exhausted')
        headers = {'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity', 'User-Agent': 'AbyssOcean/0.1'}
        if self.etag:
            headers['If-Range'] = self.etag
        req = urllib.request.Request(self.url, headers=headers)
        with opener(self.hosts).open(req, timeout=25) as response:
            self.requests += 1
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
            if response.status != 206 or not match:
                raise RetrievalError('Source must honor byte ranges; full download refused')
            lo, hi, total = map(int, match.groups())
            if lo != start or hi != min(end, total - 1) or total <= hi:
                raise RetrievalError('Invalid upstream Content-Range')
            if self.total is not None and total != self.total:
                raise RetrievalError('Recording changed during retrieval')
            etag = response.headers.get('ETag')
            if self.etag and etag != self.etag:
                raise RetrievalError('Recording ETag changed')
            self.etag, self.total = etag, total
            data = response.read(min(hi - lo + 2, self.max_bytes - self.bytes_read))
            self.bytes_read += len(data)
            if len(data) != hi - lo + 1:
                raise RetrievalError('Incomplete or oversized range response')
            return data

    def block(self, start):
        with self.lock:
            index = start // self.block_size
            if index not in self.cache:
                lo = index * self.block_size
                self.cache[index] = self._fetch(lo, min(lo + self.block_size - 1, self.total - 1))
                if len(self.cache) > 128:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(index)
            return self.cache[index][start % self.block_size:]

    @contextlib.contextmanager
    def bridge(self):
        video = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_HEAD(self):
                self.send_response(200)
                self.send_header('Content-Length', str(video.total))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()

            def do_GET(self):
                if self.path != '/video.mp4':
                    self.send_error(404)
                    return
                try:
                    match = re.fullmatch(r'bytes=(\d+)-(\d*)', self.headers.get('Range', 'bytes=0-'))
                    if not match:
                        self.send_error(416)
                        return
                    start = int(match[1])
                    if start >= video.total:
                        self.send_error(416)
                        return
                    end = min(int(match[2]), video.total - 1) if match[2] else video.total - 1
                    if end < start:
                        self.send_error(416)
                        return
                    # Fulfill the requested range. A short range advertised as a
                    # complete response makes FFmpeg mistake a block for EOF.
                    self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                    self.send_response(206)
                    self.send_header('Content-Type', 'video/mp4')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Content-Length', str(end - start + 1))
                    self.send_header('Content-Range', f'bytes {start}-{end}/{video.total}')
                    self.end_headers()
                    while start <= end:
                        data = video.block(start)[:end - start + 1]
                        self.wfile.write(data)
                        start += len(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as exc:
                    video.error = str(exc)
                    self.send_error(502, 'Upstream range retrieval failed')

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = False
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/video.mp4'
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
