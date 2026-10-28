"""Retire derived history while current images and old QR destinations stay usable."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from abyss.publication import atomic_json, publish
from abyss.retention import local_file, retain

BASE = 'https://site.example/abyss'


class RetentionTests(unittest.TestCase):
    def observation(self, root, number, video=False):
        image = Image.fromarray(np.random.default_rng(number).integers(0, 256, (160, 240, 3), dtype='uint8'))
        metadata = {'source_id': 'camera', 'source_name': 'Camera', 'source_type': 'periodic_recording' if video else 'periodic_snapshot',
                    'captured_at': f'2026-10-{number + 1:02}T10:00:00+00:00',
                    'published_at': f'2026-10-{number + 1:02}T11:00:00+00:00', 'frame_seconds': 42,
                    'original_url': f'https://camera.example/{number}.' + ('mp4' if video else 'jpg'),
                    'attribution': 'Required credit', 'acknowledgment': 'Acknowledgment', 'license': 'Test'}
        return publish(root, {'id': 'camera'}, image, metadata, BASE, display_image=image)

    def test_current_and_previous_full_images_retained_and_old_qr_uses_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            observations = [self.observation(tmp, i) for i in range(4)]
            public = Path(tmp) / 'public'
            report = retain(tmp, BASE)
            self.assertTrue(report['budget_satisfied'])
            self.assertEqual(len(list((public / 'sources/camera').glob('*.png'))), 2)
            self.assertTrue(local_file(public, observations[-1]['image_url'], BASE).exists())
            old = observations[0]
            self.assertFalse(local_file(public, old['image_url'], BASE).exists())
            page = local_file(public, old['view_url'], BASE).read_text()
            self.assertIn(old['preview_url'], page)
            self.assertNotIn(old['image_url'], page)
            self.assertIn(old['original_url'], page)
            self.assertTrue(local_file(public, old['qr_code_url'], BASE).exists())
            self.assertIn('Required credit', page)

    def test_cached_session_winners_are_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            observations = [self.observation(tmp, i, True) for i in range(4)]
            public = Path(tmp) / 'public'
            atomic_json(public / 'sources/camera/sessions.json', {'sessions': [observations[0]]})
            retain(tmp, BASE)
            self.assertTrue(local_file(public, observations[0]['image_url'], BASE).exists())
            self.assertTrue(local_file(public, observations[-1]['image_url'], BASE).exists())
            self.assertFalse(local_file(public, observations[1]['image_url'], BASE).exists())

    def test_old_video_qr_survives_preview_retirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            observations = [self.observation(tmp, i, True) for i in range(4)]
            public = Path(tmp) / 'public'
            retain(tmp, BASE, previews_per_camera=1)
            page = local_file(public, observations[0]['view_url'], BASE).read_text()
            self.assertIn(observations[0]['original_url'] + '#t=42', page)
            self.assertNotIn(observations[0]['image_url'], page)
            self.assertNotIn('poster=', page)
            self.assertTrue(local_file(public, observations[0]['qr_code_url'], BASE).exists())

    def test_legacy_qr_is_migrated_before_full_photo_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = self.observation(tmp, 0)
            public = Path(tmp) / 'public'; page = local_file(public, old['view_url'], BASE)
            page.with_suffix('.json').unlink()
            local_file(public, old['preview_url'], BASE).unlink()
            page.write_text(f'<h1>Old camera</h1><p>Recorded {old["captured_at"]}</p>'
                            f'<img src="{old["image_url"]}"><a href="{old["original_url"]}">Open original snapshot</a>'
                            f'<a href="{old["image_url"]}">Download attributed still</a>')
            for i in (1, 2, 3): self.observation(tmp, i)
            retain(tmp, BASE)
            self.assertNotIn(old['image_url'], page.read_text())
            self.assertIn(old['original_url'], page.read_text())
            self.assertTrue(page.with_suffix('.json').exists())
            self.assertTrue(local_file(public, old['preview_url'], BASE).exists())

    def test_budget_never_deletes_last_good_and_rejects_foreign_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.observation(tmp, 0); public = Path(tmp) / 'public'
            image = local_file(public, metadata['image_url'], BASE); before = image.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Current camera'):
                retain(tmp, BASE, max_bytes=1)
            self.assertEqual(image.read_bytes(), before)
            image.unlink()
            with self.assertRaisesRegex(ValueError, 'image is missing'):
                retain(tmp, BASE)
            for bad in ('https://other.example/abyss/a', BASE + '/../outside', BASE + '/%2e%2e/outside'):
                self.assertIsNone(local_file(public, bad, BASE))

    def test_budget_can_retire_optional_full_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            observations = [self.observation(tmp, i) for i in range(4)]
            public = Path(tmp) / 'public'
            first = retain(tmp, BASE)
            previous = local_file(public, observations[-2]['image_url'], BASE)
            budget = first['after_bytes'] - previous.stat().st_size + 4096
            report = retain(tmp, BASE, max_bytes=budget)
            self.assertLessEqual(report['after_bytes'], budget)
            self.assertTrue(local_file(public, observations[-1]['image_url'], BASE).exists())

    def test_partial_missing_derivative_never_reappears_as_a_full_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = self.observation(tmp, 0); public = Path(tmp) / 'public'
            record_path = local_file(public, old['view_url'], BASE).with_suffix('.json')
            record = json.loads(record_path.read_text())
            record['image_url'] = BASE + '/sources/camera/' + 'f' * 20 + '.png'
            atomic_json(record_path, record)
            retain(tmp, BASE)
            page = local_file(public, old['view_url'], BASE).read_text()
            self.assertNotIn('Download attributed still', page)
            self.assertNotIn(record['image_url'], page)


class PersistenceTests(unittest.TestCase):
    def test_snapshot_history_is_bounded_and_lease_rejects_concurrent_output(self):
        spec = importlib.util.spec_from_file_location('persist_output', 'scripts/persist_output.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); remote = root / 'remote.git'; repo = root / 'repo'; output = repo / 'output'
            def call(*args, cwd=None):
                return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.PIPE).decode().strip()
            call('init', '--bare', str(remote)); call('init', '-b', 'main', str(repo))
            call('config', 'user.name', 'Test', cwd=repo); call('config', 'user.email', 'test@example.invalid', cwd=repo)
            (repo / 'source.txt').write_text('source stays untouched')
            call('add', 'source.txt', cwd=repo); call('commit', '-m', 'Source', cwd=repo)
            call('remote', 'add', 'origin', str(remote), cwd=repo)
            source_commit = call('rev-parse', 'HEAD', cwd=repo)
            (output / 'public').mkdir(parents=True); (output / 'state').mkdir()
            (output / 'public/old.png').write_bytes(b'old image')
            one = module.persist(repo, output)
            (output / 'public/old.png').unlink(); (output / 'public/new.png').write_bytes(b'new image')
            two = module.persist(repo, output, expected=one)
            self.assertEqual(call('--git-dir', str(remote), 'rev-list', '--count', 'ocean-output'), '1')
            self.assertNotIn('old.png', call('--git-dir', str(remote), 'ls-tree', '-r', '--name-only', 'ocean-output'))
            self.assertEqual(call('rev-parse', 'HEAD', cwd=repo), source_commit)
            self.assertEqual(call('diff', '--cached', '--name-only', cwd=repo), '')
            before_history = (output / 'state/publication-history.json').read_bytes()
            with self.assertRaises(subprocess.CalledProcessError):
                module.persist(repo, output, expected=one)
            self.assertEqual((output / 'state/publication-history.json').read_bytes(), before_history)
            self.assertEqual(call('--git-dir', str(remote), 'rev-parse', 'ocean-output'), two)
