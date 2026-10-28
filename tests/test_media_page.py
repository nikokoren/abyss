"""Full-resolution publication and QR links retain the observation identity."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
import zxingcpp

from abyss.pipeline import run
from abyss.publication import publish, read_json
from test_abyss import source, args
from test_trmnl import catalog, native, render


class MediaPageTests(unittest.TestCase):
    def test_device_uses_clean_photo_and_native_credit_instead_of_attributed_raster(self):
        data = catalog()
        camera = data['sources']['ooi-axial']
        camera['display_image_url'] = 'https://site.example/clean-full-resolution.png'
        camera['display_credit'] = 'Data: OOI / WHOI / UW | U.S. NSF 2244833'
        for layout in ('full', 'half_horizontal', 'half_vertical', 'quadrant'):
            html = render(layout, data)
            self.assertIn(camera['display_image_url'], html)
            self.assertNotIn(camera['image_url'], html)
            self.assertIn('label label--small w--full shrink-0', html)
            self.assertIn(camera['display_credit'], html)

    def metadata(self):
        return {'source_id': 'camera', 'source_name': 'Vent <camera>', 'location': 'Ocean & sea',
                'depth_label': '~1,540 m', 'source_type': 'periodic_recording',
                'original_url': 'https://camera.example/2026/recording.mp4', 'frame_seconds': 124.5,
                'captured_at': '2026-10-28T10:02:04+00:00', 'attribution': 'Required credit',
                'acknowledgment': 'Acknowledgment', 'license': 'Test imagery'}

    def test_qr_opens_exact_video_frame_and_immutable_page_survives_new_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = publish(tmp, {'id': 'camera'}, Image.new('RGB', (1200, 900), 'cyan'),
                            self.metadata(), 'https://site.example/abyss')
            page = Path(tmp) / 'public' / first['view_url'].split('/abyss/')[1]
            original_page = page.read_bytes()
            text = original_page.decode()
            self.assertIn('recording.mp4#t=124.5', text)
            self.assertIn(first['image_url'], text)
            self.assertIn('Required credit', text)
            self.assertIn('Vent &lt;camera&gt;', text)
            qr = Path(tmp) / 'public' / first['qr_code_url'].split('/abyss/')[1]
            decoded = zxingcpp.read_barcode(Image.open(qr))
            self.assertEqual(decoded.text, first['view_url'])
            second = publish(tmp, {'id': 'camera'}, Image.new('RGB', (1200, 900), 'red'),
                             self.metadata(), 'https://site.example/abyss')
            self.assertNotEqual(first['view_url'], second['view_url'])
            self.assertEqual(page.read_bytes(), original_page)
            self.assertEqual(read_json(Path(tmp) / 'public/sources/camera/latest.json', {})['view_url'], second['view_url'])

    def test_snapshot_and_invalid_original_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            for original in ('https://camera.example/image.jpg', 'javascript:alert(1)', 'https://user:secret@camera.example/test.mp4'):
                data = self.metadata(); data['original_url'] = original
                result = publish(tmp, {'id': 'camera'}, Image.new('RGB', (64, 64)), data, 'https://site.example/abyss')
                page = Path(tmp) / 'public' / result['view_url'].split('/abyss/')[1]
                text = page.read_text()
                self.assertNotIn('<video', text)
                self.assertIn('exact displayed still', text)
                self.assertNotIn('javascript:', text)
                self.assertNotIn('secret@', text)
                if original.endswith('.jpg'):
                    self.assertIn('Open original snapshot', text)

    def test_qr_is_optional_and_tracks_rotated_camera_without_dithering_the_code(self):
        data = catalog()
        data['sources']['ooi-axial']['qr_code_url'] = 'https://site.example/first-qr.png'
        other = copy.deepcopy(data['sources']['ooi-axial'])
        other.update(source_id='other', qr_code_url='https://site.example/other-qr.png')
        data['sources']['other'] = other
        for layout in ('full', 'half_horizontal', 'half_vertical', 'quadrant'):
            self.assertNotIn('first-qr.png', render(layout, data))
            text = render(layout, data, 'other', show_qr='true')
            self.assertEqual('other-qr.png' in text, layout == 'full')
            self.assertNotIn('first-qr.png', text)
            from test_trmnl import Markup
            images = [a for tag, a in Markup(text).elements if tag == 'img']
            self.assertIn('image-dither', images[0]['class'])
            if layout == 'full':
                self.assertNotIn('image-dither', images[1]['class'])
                self.assertIn('absolute bottom--0 right--0', images[1]['class'])
            else:
                self.assertEqual(len(images), 1)
        for value, expected in [(False, False), ('false', False), (None, False), (True, True), ('true', True), ('1', True)]:
            context = copy.deepcopy(data)
            context['trmnl'] = {'plugin_settings': {'custom_fields_values': {'show_qr': value}}}
            self.assertEqual(native.run(context)['show_qr'], expected)

    def test_pipeline_publishes_full_resolution_color_and_reprocesses_old_render_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); camera = source(); config = args(root)
            config.method = 'native'
            frame = root / 'original.png'
            pixels = np.random.default_rng(17).integers(30, 220, (1080, 1920, 3), dtype='uint8')
            Image.fromarray(pixels).save(frame)
            record = {'url': camera['video_url'], 'recorded_at': '2026-01-01T10:00:00+00:00'}
            metrics = {'score': .8, 'fingerprint': '0' * 256}
            chosen = {'recording': record, 'seconds': 123.5, 'path': frame, 'quality': metrics}
            with patch('abyss.pipeline.discover_many', return_value=[record]), \
                 patch('abyss.pipeline.search', return_value=(chosen, {}, [record['url']])) as search:
                self.assertEqual(run([camera], config)[camera['id']], 'published')
                latest = read_json(root / 'public/sources/test-camera/latest.json', {})
                self.assertEqual((latest['width'], latest['height']), (1920, 1080))
                self.assertEqual((latest['source_width'], latest['source_height']), (1920, 1080))
                self.assertEqual(latest['color_mode'], 'RGB')
                with Image.open(root / 'public' / latest['image_url'].split('/abyss/')[1]) as image:
                    np.testing.assert_array_equal(np.asarray(image), pixels)
                self.assertIn('/i/', latest['qr_code_url'])
                with Image.open(root / 'public' / latest['display_image_url'].split('/abyss/')[1]) as image:
                    np.testing.assert_array_equal(np.asarray(image), pixels)
                self.assertFalse(latest['display_attribution_embedded'])
                self.assertEqual(run([camera], config)[camera['id']], 'unchanged')
                config.method = 'ordered'
                self.assertEqual(run([camera], config)[camera['id']], 'published')
                config.method = 'native'
                self.assertEqual(run([camera], config)[camera['id']], 'published')
                self.assertEqual(search.call_count, 3)
