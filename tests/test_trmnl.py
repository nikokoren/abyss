"""Render the real Liquid views, including data and retained-image edge cases."""
import copy
import importlib.util
import unittest
from html.parser import HTMLParser
from pathlib import Path

from liquid import Environment

LAYOUTS = ('full', 'half_horizontal', 'half_vertical', 'quadrant')
spec = importlib.util.spec_from_file_location('abyss_native_transform', 'trmnl/transform.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def catalog():
    camera = {
        'source_id': 'ooi-axial', 'source_name': 'Axial Seamount · hydrothermal vents',
        'location': 'Axial Seamount, ASHES vent field', 'location_label': 'Axial Seamount',
        'depth_m': 1543, 'depth_label': '~1,540 m', 'depth_status': 'preliminary',
        'source_type': 'periodic_recording', 'image_url': 'https://example.invalid/ocean.png',
        'captured_at': '2026-10-28T06:28:01+00:00', 'timestamp_basis': 'filename_assumed_utc',
        'attribution': ('Ocean Observatories Initiative / Woods Hole Oceanographic Institution OOI Program Office / '
                        'University of Washington; supported by the U.S. National Science Foundation, '
                        'Cooperative Agreement 2244833'),
        'available': True, 'stale': False, 'fixture': False,
        'display_credit': 'Data: OOI / WHOI OOI Program Office / UW | Supported by U.S. NSF 2244833',
    }
    return {'default_source': 'ooi-axial', 'default_image': camera, 'sources': {'ooi-axial': camera}}


def render(layout, data, selection=None, show_qr=False):
    context = copy.deepcopy(data)
    context['trmnl'] = {'plugin_settings': {'custom_fields_values': {
        'source_ids': selection if selection is not None else [], 'show_qr': show_qr},
        'refresh_interval_minutes': 15, 'data_fetched_utc': 1793167200},
        'device': {'friendly_id': 'TEST', 'refresh_interval_seconds': 900}, 'state': {}}
    transformed = native.run(context)
    transformed.pop('trmnl_state')
    context.update(transformed)
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
                self.assertIn('image-dither', images[0]['class'].split())
                text = render(layout, catalog())
                self.assertIn('<span class="title">Abyss</span>', text)
                self.assertIn('Axial Seamount', text)
                self.assertIn('~1,540 m', text)
                self.assertNotIn('Recorded ', text)
                self.assertIn('Data: OOI', text)
                self.assertIn('label label--small w--full shrink-0', text)
                self.assertNotIn('Periodic recording', text)

    def test_missing_selection_keeps_default_and_retained_image(self):
        data = catalog()
        data['default_image']['available'] = False
        data['default_image']['stale'] = True
        for layout in LAYOUTS:
            text = render(layout, data, 'ooi-axial')
            self.assertIn('https://example.invalid/ocean.png', text)
            self.assertIn('Last good image · update delayed', text)
            self.assertIn('~1,540 m', text)

    def test_empty_catalog_has_native_empty_state_without_an_image(self):
        for layout in LAYOUTS:
            text = render(layout, {'sources': {}, 'default_image': None})
            self.assertIn('No image is available for the selected feeds yet', text)
            self.assertNotIn('<img', text)
            self.assertNotIn('Periodic recording', text)

    def test_actual_selected_source_missing_time_and_untrusted_text(self):
        data = catalog()
        other = copy.deepcopy(data['default_image'])
        other.update(source_id='other', source_name='<script>bad()</script>',
                     location_label='Other observatory', depth_label=None,
                     source_type='archive', image_url='https://example.invalid/second.png',
                     captured_at=None, fixture=True)
        data['sources']['other'] = other
        for layout in LAYOUTS:
            text = render(layout, data, 'other')
            self.assertIn('https://example.invalid/second.png', text)
            self.assertNotIn('https://example.invalid/ocean.png', text)
            self.assertIn('Depth unknown', text)
            self.assertIn('Synthetic fixture', text)
            self.assertNotIn('Recorded ', text)
            self.assertNotIn('<script>', text)
            self.assertIn('&lt;script&gt;', text)


if __name__ == '__main__':
    unittest.main()
