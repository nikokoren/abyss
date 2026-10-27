"""Copy the static viewer into the public-only Pages artifact."""
from pathlib import Path
import shutil

public = Path('output/public')
public.mkdir(parents=True, exist_ok=True)
shutil.copyfile('docs/viewer.html', public/'index.html')
(public/'.nojekyll').touch()
