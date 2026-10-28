"""Copy the static viewer into the public-only Pages artifact."""
from pathlib import Path
import shutil

public = Path('output/public')
public.mkdir(parents=True, exist_ok=True)
shutil.copyfile('docs/viewer.html', public/'index.html')
shutil.copytree('trmnl', public/'trmnl', dirs_exist_ok=True)
settings = public / 'trmnl' / 'settings.yml'
if (public / 'settings.yml').exists():
    shutil.copyfile(public / 'settings.yml', settings)
else:
    settings.unlink(missing_ok=True)
shutil.make_archive(str(public / 'ambient-ocean-trmnl'), 'zip', root_dir=public / 'trmnl')
(public/'.nojekyll').touch()
