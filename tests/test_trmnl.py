"""Render the real Liquid views, including data and retained-image edge cases."""
import copy
import unittest
from html.parser import HTMLParser
from pathlib import Path

from liquid import Environment

LAYOUTS = ('full', 'half_horizontal', 'half_vertical', 'quadrant')


def catalog():
    camera = {
        'source_id': 'ooi-axial', 'source_name': 'Axial Seamount · hydrothermal vents',
        'source_type': 'periodic_recording', 'image_url': 'https://example.invalid/ocean.png',
        'captured_at': '2026-10-28T06:28:01+00:00', 'timestamp_basis': 'filename_assumed_utc',
        'attribution': ('Ocean Observatories Initiative / Woods Hole Oceanographic Institution OOI Program Office / '
                        'University of Washington; supported by the U.S. National Science Foundation, '
                        'Cooperative Agreement 2244833'),
        'available': True, 'stale': False, 'fixture': False,
    }
    return {'default_source': 'ooi-axial', 'default_image': camera, 'sources': {'ooi-axial': camera}}


def render(layout, data, selection=None):
    context = copy.deepcopy(data)
    context['trmnl'] = {'plugin_settings': {'custom_fields_values': {
        'source_id': selection if selection is not None else data.get('default_source')}}}
    return Environment().from_string(Path('trmnl', layout + '.liquid').read_text()).render(**context)


class Markup(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class TrmnlTests(unittest.TestCase):
    def test_all_layouts_use_native_framework_structure_and_image_containment(self):
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                markup = Markup(render(layout, catalog()))
                self.assertEqual(sum('layout' in attrs.get('class', '').split()
                                     for _, attrs in markup.elements), 1)
                self.assertEqual(sum('title_bar' in attrs.get('class', '').split()
                                     for _, attrs in markup.elements), 1)
                for tag, attrs in markup.elements:
                    self.assertNotIn(tag, {'style', 'script', 'link'})
                    self.assertNotIn('style', attrs)
                    # Device and view wrappers belong to the host platform.
                    self.assertFalse({'screen', 'view', 'mashup'} & set(attrs.get('class', '').split()))
                images = [attrs for tag, attrs in markup.elements if tag == 'img']
                self.assertEqual(len(images), 1)
                self.assertIn('image--contain', images[0]['class'].split())
                self.assertIn('UTC assumed', render(layout, catalog()))

    def test_missing_selection_keeps_default_and_retained_image(self):
        data = catalog()
        data['default_image']['available'] = False
        data['default_image']['stale'] = True
        for layout in LAYOUTS:
            text = render(layout, data, 'removed-source')
            self.assertIn('https://example.invalid/ocean.png', text)
            self.assertIn('Unavailable · last good image', text)
            self.assertIn('Stale recording · last good image', text)
            self.assertIn('WHOI OOI Program Office', text)
            self.assertIn('U.S. NSF, Award 2244833', text)

    def test_empty_catalog_has_native_empty_state_without_an_image(self):
        for layout in LAYOUTS:
            text = render(layout, {'sources': {}, 'default_image': None})
            self.assertIn('No ocean image is available yet', text)
            self.assertNotIn('<img', text)
            self.assertNotIn('Periodic recording', text)

    def test_actual_selected_source_missing_time_and_untrusted_text(self):
        data = catalog()
        other = copy.deepcopy(data['default_image'])
        other.update(source_id='other', source_name='<script>bad()</script>',
                     source_type='archive', image_url='https://example.invalid/second.png',
                     captured_at=None, fixture=True)
        data['sources']['other'] = other
        for layout in LAYOUTS:
            text = render(layout, data, 'other')
            self.assertIn('https://example.invalid/second.png', text)
            self.assertNotIn('https://example.invalid/ocean.png', text)
            self.assertIn('Recording time unknown', text)
            self.assertIn('Synthetic fixture', text)
            self.assertIn('Archive', text)
            self.assertNotIn('<script>', text)
            self.assertIn('&lt;script&gt;', text)


if __name__ == '__main__':
    unittest.main()
