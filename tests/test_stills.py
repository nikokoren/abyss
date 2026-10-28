import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from test_abyss import args, source
from abyss.adapters import discover_many
from abyss.network import RetrievalError, TransferBudget
from abyss.pipeline import run
from abyss.publication import read_json
from abyss.search import search
from abyss.stills import download_image


def camera():
    value = source()
    value.update(adapter='ooi_image_directory', base_url='https://camera.example/CAMDSB103/',
                 camera_code='CAMDSB103', type='periodic_snapshot', completion_delay_minutes=5,
                 images_per_search=3, depth_label='~780 m', location_label='Hydrate Ridge')
    return value


def picture(black=False):
    image = Image.new('L', (320, 240), 0) if black else Image.fromarray(
        np.random.default_rng(42).integers(20, 230, (240, 320), dtype='uint8'))
    stream = io.BytesIO(); image.save(stream, format='JPEG')
    return stream.getvalue()


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, **headers):
        super().__init__(data)
        self.bytes_read = 0
        self.headers = {'Content-Type': 'image/jpeg', 'Content-Length': str(len(data)), **headers}

    def read(self, amount=-1):
        data = super().read(amount)
        self.bytes_read += len(data)
        return data


class ImageOpener:
    def __init__(self, values):
        self.values, self.requests = values, []

    def open(self, request, timeout=25):
        self.requests.append(request.full_url)
        return Response(self.values[request.full_url])


class StillTests(unittest.TestCase):
    def test_discovery_requires_camera_id_same_path_utc_and_completed_age(self):
        listing = b'''<a href="CAMDSB103_10.33.7.5_20260101T110000_UTC.jpg">valid</a>
        <a href="CAMDSB103_10.33.7.5_20260101T115900_UTC.jpg">too recent</a>
        <a href="CAMDSB107_10.33.7.5_20260101T110100_UTC.jpg">wrong camera</a>
        <a href="CAMDSB103_10.33.7.5_20260102T110000_UTC.jpg">wrong day</a>
        <a href="https://evil.test/CAMDSB103_10.33.7.5_20260101T110000_UTC.jpg">wrong host</a>
        <a href="../CAMDSB103_10.33.7.5_20260101T110000_UTC.jpg">parent</a>'''
        value = camera(); value['lookback_days'] = 1
        with patch('abyss.adapters.read_small', return_value=listing):
            records = discover_many(value, datetime(2026, 1, 1, 12, tzinfo=timezone.utc))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['recorded_at'], '2026-01-01T11:00:00+00:00')
        self.assertEqual(records[0]['media_type'], 'image')

    def test_budget_is_shared_and_truncated_data_are_accounted(self):
        body = picture(); budget = TransferBudget(len(body) + 100)
        with tempfile.TemporaryDirectory() as tmp:
            response = Response(body)
            response.headers['Content-Length'] = str(len(body) + 5)
            with patch('abyss.stills.opener') as make:
                make.return_value.open.return_value = response
                with self.assertRaisesRegex(RetrievalError, 'Truncated'):
                    download_image({'url': 'https://camera.example/photo.jpg'}, camera(), tmp, budget, 0)
            self.assertEqual(budget.used, len(body))
            response = Response(body)
            with patch('abyss.stills.opener') as make:
                make.return_value.open.return_value = response
                with self.assertRaisesRegex(RetrievalError, 'budget'):
                    download_image({'url': 'https://camera.example/photo.jpg'}, camera(), tmp, budget, 1)
            self.assertEqual(response.bytes_read, 0)
            self.assertLessEqual(budget.used, budget.limit)

    def test_html_and_oversized_dimensions_are_refused(self):
        stream = io.BytesIO(); Image.new('L', (5000, 4000), 128).save(stream, format='PNG')
        for response in [Response(b'<html>login</html>', **{'Content-Type': 'text/html'}),
                         Response(stream.getvalue(), **{'Content-Type': 'image/png'})]:
            with self.subTest(headers=response.headers), tempfile.TemporaryDirectory() as tmp:
                with patch('abyss.stills.opener') as make:
                    make.return_value.open.return_value = response
                    with self.assertRaises(RetrievalError):
                        download_image({'url': 'https://camera.example/photo.jpg'}, camera(), tmp,
                                       TransferBudget(8 * 1024 * 1024), 0)

    def test_images_are_ranked_without_video_and_partial_failures_keep_good_frames(self):
        urls = ['https://camera.example/' + x + '.jpg' for x in ('dark', 'clear', 'broken')]
        fake = ImageOpener(dict(zip(urls, [picture(True), picture(), b'broken jpeg'])))
        records = [{'url': u, 'recorded_at': '2026-01-01T10:00:00+00:00', 'media_type': 'image'} for u in urls]
        with tempfile.TemporaryDirectory() as tmp, patch('abyss.stills.opener', return_value=fake), \
                patch('abyss.search.probe', side_effect=AssertionError('Snapshots must not invoke video probing')):
            best, diagnostics, completed = search(camera(), records, tmp, args(tmp))
            self.assertEqual(best['recording']['url'], urls[1])
            self.assertEqual(diagnostics['strategy'], 'recent_snapshots')
            self.assertEqual(diagnostics['images_extracted'], 2)
            self.assertEqual(diagnostics['fine_extracted'], 0)
            self.assertFalse(diagnostics['search_complete'])
            self.assertEqual(set(completed), set(urls[:2]))
            self.assertEqual(diagnostics['bytes_downloaded'], sum(len(v) for v in fake.values.values()))

    def test_snapshot_pipeline_publishes_then_skips_known_images(self):
        url = 'https://camera.example/CAMDSB103/2026/01/01/CAMDSB103_10.33.7.5_20260101T110000_UTC.jpg'
        fake = ImageOpener({url: picture()})
        records = [{'url': url, 'recorded_at': '2026-01-01T11:00:00+00:00', 'media_type': 'image'}]
        with tempfile.TemporaryDirectory() as tmp, patch('abyss.pipeline.discover_many', return_value=records), \
                patch('abyss.stills.opener', return_value=fake):
            value = camera(); value.update(preserve_frame=True, image_credit_lines=['OOI / WHOI / UW; NSF support'])
            options = args(tmp)
            self.assertEqual(run([value], options)[value['id']], 'published')
            metadata = read_json(Path(tmp) / 'public/sources/test-camera/latest.json', {})
            self.assertEqual(metadata['captured_at'], '2026-01-01T11:00:00+00:00')
            self.assertEqual(metadata['source_type'], 'periodic_snapshot')
            self.assertEqual(metadata['depth_label'], '~780 m')
            self.assertTrue(metadata['attribution_embedded'])
            self.assertEqual(run([value], options)[value['id']], 'unchanged')
            self.assertEqual(len(fake.requests), 1)


if __name__ == '__main__':
    unittest.main()
