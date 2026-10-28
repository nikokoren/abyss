"""Search every recent session, preserve its winner and reuse valid cached winners."""
import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from abyss.pipeline import run
from abyss.publication import read_json
from abyss.search import search
from test_abyss import args, source


def recording(hour):
    return {'url': f'https://camera.example/{hour}.mp4', 'recorded_at': f'2026-01-01T{hour:02}:00:00+00:00'}


class SessionTests(unittest.TestCase):
    def make_search(self, scores, model_id=None):
        def choose(camera, recordings, directory, arguments, history):
            choices = []
            for i, record in enumerate(recordings):
                hour = int(record['url'].rsplit('/', 1)[-1].split('.')[0])
                path = Path(directory) / f'{hour}.png'
                Image.new('RGB', (800, 448), (hour * 8, 100, 80)).save(path)
                choices.append({'recording': record, 'seconds': 30, 'path': path,
                    'quality': {'score': scores[hour], 'fingerprint': ('01' if hour % 2 else '10') * 128},
                    'selection_score': scores[hour]})
            best = dict(max(choices, key=lambda c: c['selection_score']))
            best['session_winners'] = choices
            return best, {'recordings': [], 'preference': {'model_id': model_id}}, [r['url'] for r in recordings]
        return choose

    def test_broader_search_refines_each_session_and_exports_a_winner_per_recording(self):
        calls = []
        class Video:
            error = None; bytes_read = 0; requests = 0; total = 1000
            def __init__(self, url, *unused, **kwargs): self.url = url
            def bridge(self): return nullcontext(self.url)
        def frames(url, directory, positions, **kwargs):
            calls.append((url, kwargs['prefix'], len(positions)))
            result = []
            for i, seconds in enumerate(positions):
                path = Path(directory) / f'{kwargs["prefix"]}-{i}.png'
                Image.new('L', (100, 80), 200 if 'fine' in kwargs['prefix'] else 150).save(path)
                result.append((seconds, path))
            return result, {'extraction_errors': []}
        with tempfile.TemporaryDirectory() as tmp:
            config = args(tmp); config.candidates = 10; config.coarse_candidates = 6
            config.refine_candidates = 6; config.refine_windows = 3; config.interval = 60
            with patch('abyss.search.RangeVideo', Video), patch('abyss.search.probe', return_value=(600, 'h264')), \
                 patch('abyss.search.extract_positions', side_effect=frames), \
                 patch('abyss.search.quality', side_effect=lambda image, *a: {'score': image.getpixel((0, 0))/255, 'fingerprint': '0'*256}):
                best, diagnostics, completed = search(source(), [recording(h) for h in (15, 12, 9)], tmp, config)
            self.assertEqual(diagnostics['coarse_extracted'], 18)
            self.assertEqual(diagnostics['fine_extracted'], 6)
            self.assertEqual(diagnostics['candidates_extracted'], 24)
            self.assertEqual(len(best['session_winners']), 3)
            self.assertEqual(len({url for url, prefix, count in calls if 'fine' in prefix}), 3)
            self.assertEqual(len(completed), 3)
            json.dumps(diagnostics)  # public reports contain no bridge/path objects

    def test_cached_session_can_beat_new_clip_and_later_new_winner_replaces_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = args(tmp); config.method = 'native'; camera = source()
            scores = {9: .7, 12: .8, 15: .9, 18: .85, 21: .95}
            with patch('abyss.pipeline.discover_many', return_value=[recording(h) for h in (15, 12, 9)]), \
                 patch('abyss.pipeline.search', side_effect=self.make_search(scores)):
                self.assertEqual(run([camera], config)[camera['id']], 'published')
            latest = Path(tmp) / 'public/sources/test-camera/latest.json'
            first = read_json(latest, {})
            with patch('abyss.pipeline.discover_many', return_value=[recording(h) for h in (18, 15, 12)]), \
                 patch('abyss.pipeline.search', side_effect=self.make_search(scores)) as searched:
                self.assertEqual(run([camera], config)[camera['id']], 'unchanged')
                self.assertEqual(searched.call_args.args[1], [recording(18)])
            self.assertEqual(read_json(latest, {})['published_at'], first['published_at'])
            self.assertEqual(read_json(latest, {})['original_url'], recording(15)['url'])
            with patch('abyss.pipeline.discover_many', return_value=[recording(h) for h in (21, 18, 15)]), \
                 patch('abyss.pipeline.search', side_effect=self.make_search(scores)):
                self.assertEqual(run([camera], config)[camera['id']], 'published')
            self.assertEqual(read_json(latest, {})['original_url'], recording(21)['url'])
            index = read_json(latest.parent / 'sessions.json', {})
            self.assertEqual(len(index['sessions']), 5)
            for session in index['sessions']:
                self.assertTrue((Path(tmp) / 'public' / session['image_url'].split('/abyss/')[1]).exists())

    def test_changed_model_reprocesses_all_recent_sessions_without_mixing_cached_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = args(tmp); camera = source(); records = [recording(h) for h in (15, 12, 9)]
            with patch('abyss.pipeline.discover_many', return_value=records), \
                 patch('abyss.pipeline.load_model', return_value={'model_id': 'first'}), \
                 patch('abyss.pipeline.search', side_effect=self.make_search({15: .9, 12: .7, 9: .6}, 'first')):
                run([camera], config)
            with patch('abyss.pipeline.discover_many', return_value=records), \
                 patch('abyss.pipeline.load_model', return_value={'model_id': 'second'}), \
                 patch('abyss.pipeline.search', side_effect=self.make_search({15: .2, 12: .4, 9: .3}, 'second')) as searched:
                run([camera], config)
            self.assertEqual(searched.call_args.args[1], records)
            latest = read_json(Path(tmp) / 'public/sources/test-camera/latest.json', {})
            self.assertEqual(latest['original_url'], recording(12)['url'])
            self.assertEqual(latest['selection_context']['model_id'], 'second')

    def test_publication_failure_cannot_replace_camera_with_half_finished_session_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = args(tmp); camera = source()
            with patch('abyss.pipeline.discover_many', return_value=[recording(9)]), \
                 patch('abyss.pipeline.search', side_effect=self.make_search({9: .8})):
                run([camera], config)
            latest = Path(tmp) / 'public/sources/test-camera/latest.json'; original = latest.read_bytes()
            from abyss.pipeline import publish_candidate
            def broken(source, args, candidate, diagnostics, context):
                if candidate['recording']['url'] == recording(15)['url']:
                    raise OSError('incomplete batch')
                return publish_candidate(source, args, candidate, diagnostics, context)
            with patch('abyss.pipeline.discover_many', return_value=[recording(12), recording(15)]), \
                 patch('abyss.pipeline.search', side_effect=self.make_search({12: .85, 15: .9})), \
                 patch('abyss.pipeline.publish_candidate', side_effect=broken):
                self.assertEqual(run([camera], config)[camera['id']], 'failed')
            self.assertEqual(latest.read_bytes(), original)
