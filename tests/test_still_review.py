"""Still galleries cover multiple bursts under a separate, bounded budget."""
import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from abyss.adapters import discover_many
from abyss.registry import load
from abyss.review import review_inputs


class StillReviewTests(unittest.TestCase):
    def camera(self):
        return next(s for s in load('sources.json') if s['id'] == 'ooi-hydrate-ridge')

    def record(self, stamp):
        return {'url': f'https://camera.example/{stamp}.jpg', 'recorded_at': stamp, 'media_type': 'image'}

    def test_spaced_discovery_covers_bursts_and_crosses_midnight(self):
        camera = self.camera()
        now = datetime(2026, 1, 2, 1, tzinfo=timezone.utc)
        days = {2: [self.record(f'2026-01-02T00:{minute}:{second}+00:00')
                    for minute in ('46', '16') for second in ('21', '16', '11')],
                1: [self.record(f'2026-01-01T23:46:{second}+00:00') for second in ('21', '16', '11')]}
        def listing(source, day):
            return days.get(day.day, [])
        with patch('abyss.adapters.directory_recordings', side_effect=listing):
            adjacent = discover_many(camera, now, limit=3)
            spaced = discover_many(camera, now, limit=3, min_spacing_seconds=1200)
        self.assertEqual([r['recorded_at'] for r in adjacent], [r['recorded_at'] for r in days[2][:3]])
        self.assertEqual([r['recorded_at'] for r in spaced], [days[2][0]['recorded_at'],
                         days[2][3]['recorded_at'], days[1][0]['recorded_at']])

    def test_review_budget_and_discovery_do_not_change_production_profile(self):
        camera = self.camera(); original = copy.deepcopy(camera)
        with patch('abyss.review.discover_many', return_value=['selected']) as discover:
            reviewed, records, budget = review_inputs(camera)
        discover.assert_called_once_with(camera, limit=9, min_spacing_seconds=1200)
        self.assertEqual(budget, 216 * 1024 * 1024)
        self.assertEqual(reviewed['max_search_bytes'], budget)
        self.assertEqual(records, ['selected'])
        self.assertEqual(camera, original)
        self.assertEqual(camera['images_per_search'], 2)
        self.assertEqual(camera['max_search_bytes'], 48 * 1024 * 1024)

    def test_explicit_smaller_budget_and_absolute_review_ceiling(self):
        camera = self.camera()
        with patch('abyss.review.discover_many', return_value=[]):
            self.assertEqual(review_inputs(camera, max_bytes=10_000_000)[2], 10_000_000)
            self.assertEqual(review_inputs(camera, max_bytes=1024**3, snapshot_count=12)[2], 256 * 1024 * 1024)
            for changes in ({'max_bytes': 0}, {'snapshot_count': 1}, {'snapshot_count': 13},
                            {'snapshot_spacing_minutes': 0}, {'snapshot_spacing_minutes': 1441}):
                with self.assertRaises(ValueError):
                    review_inputs(camera, **changes)

    def test_video_review_keeps_three_recordings_and_64_mib_default(self):
        source = next(s for s in load('sources.json') if s['id'] == 'ooi-axial')
        with patch('abyss.review.discover_many', return_value=['video']) as discover:
            reviewed, records, budget = review_inputs(source)
        self.assertIs(reviewed, source)
        self.assertEqual(records, ['video'])
        self.assertEqual(budget, 64 * 1024 * 1024)
        discover.assert_called_once_with(source, limit=3)
