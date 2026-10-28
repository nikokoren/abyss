"""Frequency review must sample by time, without choosing attractive frames."""
import importlib.util
import unittest
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location('offshore_wildlife', 'scripts/sample_offshore_wildlife.py')
sampling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampling)


class WildlifeSamplingTests(unittest.TestCase):
    def test_nearest_slot_is_not_highest_quality_and_burst_duplicates_are_not_extra_samples(self):
        day = datetime(2026, 10, 28, tzinfo=timezone.utc)
        records = [{'url': 'https://camera.example/' + str(i), 'recorded_at': stamp, 'quality': score}
                   for i, stamp, score in [(0, '2026-10-28T03:46:00+00:00', .1),
                                           (1, '2026-10-28T04:16:00+00:00', .99),
                                           (2, '2026-10-28T03:46:01+00:00', .01)]]
        slots = sampling.select_slots(records, day, day.replace(hour=23))
        self.assertEqual(len(slots), 6)
        selected = [s['recording'] for s in slots if s['recording']]
        self.assertEqual(selected, [records[2]])

    def test_unavailable_slots_remain_missing_and_future_captures_are_excluded(self):
        day = datetime(2026, 10, 28, tzinfo=timezone.utc)
        records = [{'url': 'https://camera.example/future', 'recorded_at': '2026-10-28T08:01:00+00:00'}]
        slots = sampling.select_slots(records, day, day.replace(hour=8))
        self.assertEqual(len(slots), 3)
        self.assertTrue(all(s['recording'] is None for s in slots))

    def test_too_distant_capture_does_not_fill_an_unrelated_slot(self):
        day = datetime(2026, 10, 28, tzinfo=timezone.utc)
        records = [{'url': 'https://camera.example/distant', 'recorded_at': '2026-10-28T02:00:00+00:00'}]
        self.assertTrue(all(s['recording'] is None for s in sampling.select_slots(records, day, day.replace(hour=23))))
