"""Reproducible synthetic scenes, explicitly not scientific source validation."""
import json
import math
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

root = Path('output/fixtures')
root.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)
for i, name in enumerate(('chimneys', 'plume', 'terrain')):
    a = np.zeros((480, 800), dtype=np.float32)
    for y in range(480):
        a[y, :] = 25 + y * .12
    a += rng.normal(0, 3, a.shape)
    image = Image.fromarray(np.clip(a, 0, 255).astype('uint8')).convert('RGB')
    draw = ImageDraw.Draw(image)
    for x, h, w in [(220 + i*20, 280, 95), (460 - i*30, 210, 130), (620, 140, 65)]:
        draw.polygon([(x-w,480),(x-w//3,480-h),(x+w//3,470-h),(x+w,480)], fill=(130,135,120))
        for j in range(14):
            xx = x + int(math.sin(j)*w/3)
            draw.line([(xx,480-h+j*10),(xx+12,480-h+j*10+30)],fill=(210,215,190),width=4)
    if name == 'plume':
        layer = Image.new('RGB', image.size)
        ld = ImageDraw.Draw(layer)
        for j in range(12):
            ld.ellipse((190-j*4,220-j*14,260+j*8,260-j*10),fill=(100+j*9,)*3)
        image = __import__('PIL.ImageChops', fromlist=['ImageChops']).lighter(image, layer.filter(ImageFilter.GaussianBlur(12)))
    image.save(root / f'{name}.png')
    image.save(root / f'frame-{i:02}.png')
subprocess.run(['ffmpeg','-v','error','-framerate','1/3','-i',str(root/'frame-%02d.png'),
                '-c:v','libx264','-pix_fmt','yuv420p','-r','10','-y',str(root/'pan.mp4')], check=True)
source = {'id':'fixture-ocean','name':'SYNTHETIC TEST · not ocean footage','description':'Generated pipeline fixture',
          'operator':'Test generator','location':'Synthetic','category':'test','type':'archive','adapter':'direct',
          'fixture':True,'video_url':'https://example.invalid/fixture.mp4','allowed_hosts':['example.invalid'],
          'attribution':'Synthetic test fixture — no research camera imagery','attribution_url':'https://example.invalid/',
          'license':'Generated test data','license_url':'https://example.invalid/', 'status':'validated',
          'validation':{'retrieval_at':'2026-10-27T00:00:00+00:00','terms_reviewed_at':'2026-10-27T00:00:00+00:00','evidence':'Local integration fixture only'},
          'scoring':{'min_score':.10}}
(root/'registry.json').write_text(json.dumps({'schema_version':1,'sources':[source]},indent=2))
print(root/'pan.mp4')
