"""Still galleries cover multiple bursts under a separate, bounded budget."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path
from PIL import Image

from abyss.adapters import discover_many
from abyss.registry import load
from abyss.review import Gallery, distinct_candidates, near_duplicate, review_inputs
from abyss.preferences import FEATURE_COUNT, FEATURE_SPACE


class StillReviewTests(unittest.TestCase):
    def candidate(self, axis=6, quality=.8):
        features = [0.] * FEATURE_COUNT
        features[0] = 1; features[1] = .4; features[axis] = 1
        return {'features': features, 'quality_score': quality, 'fingerprint': '01' * 128}

    def test_duplicate_filter_keeps_best_and_preserves_visual_or_quality_changes(self):
        first = self.candidate(); better = self.candidate(quality=.82)
        self.assertTrue(near_duplicate(first, better))
        for different in (self.candidate(axis=7), self.candidate(quality=.9),
                          dict(first, fingerprint='10' * 128)):
            self.assertFalse(near_duplicate(first, different))
        brighter = copy.deepcopy(first); brighter['features'][1] = .5
        self.assertFalse(near_duplicate(first, brighter))
        self.assertEqual(list(distinct_candidates({'a': first, 'b': better, 'c': self.candidate(axis=7)})), ['b', 'c'])

    def test_small_texture_changes_do_not_force_another_same_view_comparison(self):
        first = self.candidate()
        def changed(bits):
            value = dict(first)
            value['fingerprint'] = ''.join('1' if c == '0' else '0' for c in first['fingerprint'][:bits]) + first['fingerprint'][bits:]
            return value
        self.assertTrue(near_duplicate(first, changed(26)))
        self.assertFalse(near_duplicate(first, changed(40)))

    def test_static_still_gallery_reports_no_review_and_can_be_manually_unfiltered(self):
        class Encoder:
            provenance = {'feature_space': FEATURE_SPACE, 'weights_sha256': 'test'}
        for include_similar in (False, True):
            gallery = Gallery(self.camera(), 'nikokoren', 'nikokoren/abyss', include_similar=include_similar)
            for i in range(3):
                candidate = self.candidate(quality=.8 + .01 * i)
                gallery.add({'recording': {'url': f'https://camera.example/{i}.jpg', 'recorded_at': None},
                             'seconds': 0, 'stage': 'snapshot', 'quality': {'score': candidate['quality_score'],
                             'fingerprint': candidate['fingerprint']}, 'selection_score': .8},
                            Image.new('RGB', (800, 448), 'gray'), candidate['features'])
            with tempfile.TemporaryDirectory() as tmp:
                manifest = gallery.save(tmp, Encoder(), {})
                report = json.loads(Path(tmp, 'gallery-report.json').read_text())
                self.assertEqual(report['sampled_candidate_count'], 3)
                self.assertEqual(report['candidate_count'], 3 if include_similar else 1)
                self.assertEqual(report['review_status'], 'ready' if include_similar else 'no_review_needed')
                self.assertEqual(manifest['review_status'], report['review_status'])
                self.assertNotIn('comparisons', manifest)

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
