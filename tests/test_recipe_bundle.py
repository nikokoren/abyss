"""The downloadable native recipe must include the executable transform."""
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


class RecipeBundleTests(unittest.TestCase):
    def test_bundle_contains_transform_and_current_settings_without_bytecode(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            shutil.copytree(root / 'trmnl', work / 'trmnl')
            (work / 'trmnl' / '__pycache__').mkdir(exist_ok=True)
            (work / 'trmnl' / '__pycache__' / 'transform.pyc').write_bytes(b'not a recipe asset')
            (work / 'docs').mkdir()
            (work / 'docs' / 'viewer.html').write_text('<title>Abyss</title>')
            public = work / 'output' / 'public'
            public.mkdir(parents=True)
            (public / 'settings.yml').write_text('serverless_language: python\n')
            # Stale output from an older bundle must not survive rebuilding.
            (public / 'trmnl').mkdir()
            (public / 'trmnl' / 'obsolete.pyc').write_bytes(b'old')
            subprocess.run([sys.executable, str(root / 'scripts' / 'build_site.py')], cwd=work, check=True)
            archive = public / 'abyss-trmnl.zip'
            with zipfile.ZipFile(archive) as bundle:
                expected = {'settings.yml', 'transform.py', 'shared.liquid', 'full.liquid',
                            'half_horizontal.liquid', 'half_vertical.liquid', 'quadrant.liquid',
                            'framework.json', 'README.md'}
                self.assertEqual(set(bundle.namelist()), expected)
                self.assertEqual(bundle.read('transform.py'), (root / 'trmnl' / 'transform.py').read_bytes())
                self.assertEqual(bundle.read('settings.yml'), b'serverless_language: python\n')
            self.assertEqual(archive.read_bytes(), (public / 'ambient-ocean-trmnl.zip').read_bytes())
            (public / 'settings.yml').unlink()
            subprocess.run([sys.executable, str(root / 'scripts' / 'build_site.py')], cwd=work, check=True)
            with zipfile.ZipFile(archive) as bundle:
                self.assertNotIn('settings.yml', bundle.namelist())
