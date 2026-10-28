"""Copy the static viewer into the public-only Pages artifact."""
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from abyss.about import HEADLINE, INTRO, about_html
from html import escape

public = Path('output/public')
public.mkdir(parents=True, exist_ok=True)
viewer = Path('docs/viewer.html').read_text(encoding='utf-8')
viewer = (viewer.replace('<!-- ABYSS_HEADLINE -->', escape(HEADLINE))
          .replace('<!-- ABYSS_INTRO -->', escape(INTRO))
          .replace('<!-- ABYSS_ABOUT -->', about_html()))
(public / 'index.html').write_text(viewer, encoding='utf-8')
(public / 'about.html').write_text(
    '<!doctype html><html lang="en"><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>About Abyss</title><body>' + about_html() + '</body></html>', encoding='utf-8')
shutil.rmtree(public/'trmnl', ignore_errors=True)
shutil.copytree('trmnl', public/'trmnl', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
settings = public / 'trmnl' / 'settings.yml'
if (public / 'settings.yml').exists():
    shutil.copyfile(public / 'settings.yml', settings)
else:
    settings.unlink(missing_ok=True)
archive = shutil.make_archive(str(public / 'abyss-trmnl'), 'zip', root_dir=public / 'trmnl')
shutil.copyfile(archive, public / 'ambient-ocean-trmnl.zip')
(public/'.nojekyll').touch()
