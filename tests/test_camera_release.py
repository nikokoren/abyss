"""Production camera choices and shared public geography stay in sync."""
import unittest

from abyss.about import CAMERAS, OVERVIEW, REGIONAL_MAP, about_html, about_trmnl_html
from abyss.registry import eligible, load


class CameraReleaseTests(unittest.TestCase):
    def test_every_production_camera_has_public_geography_and_credit(self):
        sources = {s['id']: s for s in load('sources.json') if eligible(s)}
        self.assertEqual(set(sources), {
            'ooi-axial', 'ooi-hydrate-ridge',
            'ooi-international-district', 'ooi-oregon-offshore',
        })
        self.assertEqual({c['id'] for c in CAMERAS}, set(sources))
        html = about_html()
        self.assertIn('all four cameras', OVERVIEW)
        self.assertIn('Four camera views, three research sites', html)
        self.assertIn(REGIONAL_MAP, html)
        for camera in CAMERAS:
            with self.subTest(camera=camera['id']):
                self.assertIn('about-' + camera['id'], html)
                for key in ('site_url', 'map_url', 'array_graphic_url'):
                    self.assertIn(camera[key], html)
                if camera.get('site_map_url'):
                    self.assertIn(camera['site_map_url'], html)
                self.assertTrue(sources[camera['id']]['preserve_frame'])
                for name in ('Ocean Observatories Initiative', 'Woods Hole', 'University of Washington', 'National Science Foundation'):
                    self.assertIn(name, sources[camera['id']]['attribution'])
        self.assertIn('about 580 m', html)
        self.assertIn('CAMDSB106', html)

    def test_trmnl_about_uses_breaks_without_relying_on_block_tags(self):
        html = about_trmnl_html()
        self.assertNotRegex(html, r'</?(?:p|h[1-6]|ul|li)\b')
        self.assertIn('<strong>Choose your view</strong><br>', html)
        for camera in CAMERAS:
            self.assertIn('<strong>' + camera['name'].replace("'", '&#x27;') + '</strong><br>', html)
            self.assertIn(camera['site_url'], html)
        self.assertIn('2244833', html)
        self.assertIn('<br><br>', html)
