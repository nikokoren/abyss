"""The fixed wildlife cohort is review input, never automatic preference feedback."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from abyss.preferences import FEATURE_SPACE
from abyss.network import RetrievalError
from abyss.registry import load
from scripts.review_offshore_cohort import build, cohort_records


class OffshorePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.source = next(s for s in load('sources.json') if s['id'] == 'ooi-oregon-offshore')
        self.evidence = json.loads(Path('docs/evidence/offshore-wildlife-review-20261028.json').read_text())

    def test_only_complete_reviewed_camera_cohort_is_accepted(self):
        self.assertEqual(len(cohort_records(self.evidence, self.source)), 42)
        for change in ('other_host', 'other_deployment', 'missing', 'duplicate'):
            evidence = copy.deepcopy(self.evidence)
            if change == 'other_host':
                evidence['samples'][0]['original_url'] = 'https://example.invalid/test.jpg'
            elif change == 'other_deployment':
                evidence['samples'][0]['original_url'] = 'https://rawdata.oceanobservatories.org/files/OTHER/test.jpg'
            elif change == 'missing':
                evidence['samples'].pop()
            else:
                evidence['samples'][0] = evidence['samples'][1]
            with self.assertRaises((ValueError, RetrievalError)):
                cohort_records(evidence, self.source)
        with self.assertRaises(ValueError):
            cohort_records(self.evidence, dict(self.source, validation={}))

    def test_original_pixels_supply_features_and_all_frames_remain_unlabelled(self):
        seen = []
        class Encoder:
            provenance = {'feature_space': FEATURE_SPACE}
            def encode(self, image, metrics):
                seen.append(image.size)
                return [1, metrics['brightness'], metrics['contrast'], metrics['sharpness'],
                        metrics['clipped'], metrics['base_score']] + [0.] * 512
        def download(record, source, directory, budget, index):
            path = Path(directory) / f'{index}.png'
            Image.new('RGB', (800, 600), (index, 60, 90)).save(path)
            return path, {}
        original = copy.deepcopy(self.source)
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.review_offshore_cohort.download_image', side_effect=download):
            manifest = build(self.evidence, self.source, tmp, 'nikokoren', 'nikokoren/abyss', None, Encoder())
            self.assertEqual(len(manifest['candidates']), 42)
            self.assertEqual(manifest['diversity']['policy'], 'unfiltered')
            self.assertFalse(manifest['evaluation_context']['eligible'])
            self.assertNotIn('comparisons', manifest)
            self.assertEqual(seen, [(800, 600)] * 42)
            for candidate in manifest['candidates'].values():
                self.assertNotIn('fish', candidate)
                self.assertNotIn('choice', candidate)
            html = (Path(tmp) / 'index.html').read_text()
            self.assertIn('data:image/jpeg;base64,', html)
            self.assertIn('Cooperative Agreement No. 2244833', html)
        self.assertEqual(self.source, original)
