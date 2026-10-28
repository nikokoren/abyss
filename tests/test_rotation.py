"""Native transform contract: selections, refresh cycles and retained images."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from test_trmnl import native


IDS = ['ooi-axial', 'ooi-hydrate-ridge', 'ooi-international-district']


def payload(selected=None, state=None, stamp=1793167200, device='DEVICE-A', interval=900):
    from test_trmnl import catalog
    data = catalog()
    first = data['sources']['ooi-axial']
    for index, key in enumerate(IDS):
        camera = copy.deepcopy(first)
        camera.update(source_id=key, source_name=f'Camera {index}', location_label=f'Location {index}',
                      depth_label=f'{100 + index * 100} m', image_url=f'https://example.invalid/{key}/latest-1.png')
        data['sources'][key] = camera
    data['rotation_order'] = IDS[:]
    data['default_image'] = data['sources'][IDS[0]]
    data['trmnl'] = {'plugin_settings': {'refresh_interval_minutes': 15,
        'data_fetched_utc': stamp, 'custom_fields_values': {'source_ids': selected}},
        'device': {'friendly_id': device, 'refresh_interval_seconds': interval}, 'state': state or {}}
    return data


class RotationTests(unittest.TestCase):
    def sequence(self, selected, count=5):
        state = {}; seen = []
        for step in range(count):
            output = native.run(payload(selected, state, stamp=1793167200 + step * 900))
            state = output['trmnl_state']
            seen.append(output['current_camera']['source_id'])
        return seen

    def test_empty_and_all_selected_cycle_the_same_full_pool(self):
        expected = IDS + IDS[:2]
        for selected in [None, '', [], '[]', IDS, list(reversed(IDS))]:
            with self.subTest(selected=selected):
                self.assertEqual(self.sequence(selected), expected)

    def test_single_and_multi_select_array_csv_and_json_forms(self):
        for selected in [IDS[1], [IDS[1]], json.dumps([IDS[1]])]:
            self.assertEqual(self.sequence(selected), [IDS[1]] * 5)
        for selected in [[IDS[2], IDS[0]], ', '.join([IDS[0], IDS[2]]), json.dumps([IDS[0], IDS[2]])]:
            self.assertEqual(self.sequence(selected), [IDS[0], IDS[2], IDS[0], IDS[2], IDS[0]])

    def test_same_cycle_all_layouts_do_not_advance_and_later_cycles_do(self):
        state = {}
        for _ in range(4):
            result = native.run(payload([], state))
            state = result['trmnl_state']
            self.assertEqual(result['current_camera']['source_id'], IDS[0])
        result = native.run(payload([], state, stamp=1793168100))
        self.assertEqual(result['current_camera']['source_id'], IDS[1])
        # A skipped day advances once, rather than starving feeds via time % count.
        result = native.run(payload([], result['trmnl_state'], stamp=1793254500))
        self.assertEqual(result['current_camera']['source_id'], IDS[2])

    def test_each_device_keeps_its_own_position_and_slower_cadence(self):
        state = native.run(payload([], interval=1800))['trmnl_state']
        second = native.run(payload([], state, stamp=1793168100, interval=1800))
        self.assertEqual(second['current_camera']['source_id'], IDS[0])
        third = native.run(payload([], second['trmnl_state'], stamp=1793169000, interval=1800))
        self.assertEqual(third['current_camera']['source_id'], IDS[1])
        other = native.run(payload([], third['trmnl_state'], stamp=1793169000, device='DEVICE-B'))
        self.assertEqual(other['current_camera']['source_id'], IDS[0])

    def test_latest_catalog_version_is_used_and_offline_feed_keeps_its_turn(self):
        first = native.run(payload([]))
        data = payload([], first['trmnl_state'], stamp=1793168100)
        data['sources'][IDS[1]].update(available=False, stale=True)
        original = data['sources'][IDS[1]]['image_url']
        second = native.run(data)
        self.assertEqual(second['current_camera']['image_url'], original)
        self.assertFalse(second['current_camera']['available'])
        data = payload([IDS[1]], second['trmnl_state'], stamp=1793169000)
        data['sources'][IDS[1]]['image_url'] = 'https://example.invalid/new-best.png'
        self.assertEqual(native.run(data)['current_camera']['image_url'], 'https://example.invalid/new-best.png')

    def test_selection_changes_are_immediate_and_exact_not_substring_matches(self):
        first = native.run(payload([]))
        data = payload([IDS[2]], first['trmnl_state'])
        self.assertEqual(native.run(data)['current_camera']['source_id'], IDS[2])
        data = payload(['ooi-ax'])
        self.assertIsNone(native.run(data)['current_camera'])
        self.assertEqual(native.run(payload([IDS[0], 'deleted-feed']))['rotation']['feed_ids'], [IDS[0]])

    def test_legacy_single_selection_but_explicit_empty_new_field_wins(self):
        data = payload([])
        fields = data['trmnl']['plugin_settings']['custom_fields_values']
        fields['source_id'] = IDS[2]
        self.assertEqual(native.run(data)['rotation']['feed_ids'], IDS)
        del fields['source_ids']
        self.assertEqual(native.run(data)['rotation']['feed_ids'], [IDS[2]])

    def test_no_feed_or_catalog_failure_and_missing_clock_contract(self):
        data = payload([]); data['sources'] = {}; data['rotation_order'] = []
        self.assertIsNone(native.run(data)['current_camera'])
        with self.assertRaisesRegex(ValueError, 'catalog'):
            native.run({'trmnl': {}})
        data = payload([]); del data['trmnl']['plugin_settings']['data_fetched_utc']
        with patch.object(native.time, 'time', return_value=1793167200):
            first = native.run(data)
        data['trmnl']['state'] = first['trmnl_state']
        with patch.object(native.time, 'time', return_value=1793168100):
            self.assertEqual(native.run(data)['current_camera']['source_id'], IDS[1])

    def test_state_stays_small_and_does_not_echo_input_or_history(self):
        state = {}
        for n in range(40):
            data = payload([], state, stamp=1793167200 + n * 900, device=f'DEVICE-{n}')
            data['trmnl']['previous_merge_variables'] = {'old_large_history': 'x' * 50_000}
            result = native.run(data); state = result['trmnl_state']
            self.assertNotIn('trmnl', result)
        self.assertLess(len(json.dumps(state)), 8 * 1024)
        self.assertLessEqual(len(state['abyss']['devices']), 16)

    def test_current_view_title_bar_has_the_rotated_feed_location_and_depth(self):
        from liquid import Environment
        state = {}
        for index, key in enumerate(IDS):
            data = payload([], state, stamp=1793167200 + index * 900)
            transformed = native.run(data)
            state = transformed.pop('trmnl_state')
            for layout in ('full', 'half_horizontal', 'half_vertical', 'quadrant'):
                template = Path('trmnl', layout + '.liquid').read_text()
                html = Environment().from_string(template).render(**transformed, trmnl=data['trmnl'])
                self.assertIn(f'Location {index}', html)
                self.assertIn(f'{100 + index * 100} m', html)
                self.assertIn(f'/{key}/latest-1.png', html)
                self.assertIn('<span class="title">Abyss</span>', html)


if __name__ == '__main__':
    unittest.main()
