import math
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


def fingerprint(image):
    a = np.asarray(image.convert('L').resize((17, 16)), dtype=float)
    return ''.join('1' if x else '0' for x in (a[:, 1:] > a[:, :-1]).ravel())


def similarity(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a) if a and len(a) == len(b) else 0.0


def quality(image, history=(), novelty_weight=0.12):
    a = np.asarray(image.convert('L').resize((256, 160)), dtype=float) / 255
    brightness = float(a.mean())
    clipped = float(((a < .025) | (a > .975)).mean())
    contrast = min(float(a.std()) / .25, 1)
    edges = np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean()
    lap = -4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    sharpness = min(float(lap.var()) / .025, 1)
    exposure = max(0, 1 - abs(brightness - .48) / .48)
    # Balance detail across regions rather than rewarding a single noisy corner.
    regions = [float(c.std()) for row in np.array_split(a, 3) for c in np.array_split(row, 3, axis=1)]
    composition = min(sum(v > .06 for v in regions) / 6, 1)
    detail = min(float(edges) / .12, 1)
    score = (.22 * sharpness + .23 * contrast + .20 * exposure + .15 * detail + .20 * composition) * (1 - clipped)
    if brightness < .06 or brightness > .94 or clipped > .80 or float(a.std()) < .015:
        score = 0
    fp = fingerprint(image)
    duplicate = max((similarity(fp, h) for h in history), default=0)
    # Novelty only adjusts usable frames; never rescues a bad exposure.
    adjusted = max(0, score - novelty_weight * max(0, (duplicate - .85) / .15))
    return {'score': round(adjusted, 6), 'base_score': round(score, 6), 'brightness': brightness,
            'clipped': clipped, 'sharpness': sharpness, 'contrast': contrast,
            'similarity': duplicate, 'fingerprint': fp}


def render(image, width=800, height=448, method='ordered', contrast=1.25, brightness=1.03,
           *, preserve_frame=False):
    if not (64 <= width <= 4096 and 64 <= height <= 4096):
        raise ValueError('Target dimensions must be between 64 and 4096')
    resize = ImageOps.pad if preserve_frame else ImageOps.fit
    gray = resize(image.convert('L'), (width, height), method=Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    gray = ImageEnhance.Brightness(gray).enhance(brightness)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=4))
    if method == 'grayscale':
        return gray
    if method == 'floyd':
        return gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    if method == 'threshold':
        return gray.point(lambda p: 255 if p >= 128 else 0).convert('1')
    if method != 'ordered':
        raise ValueError('Unknown processing method')
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
    thresholds = (np.tile(bayer, (math.ceil(height / 4), math.ceil(width / 4)))[:height, :width] + .5) * 16
    return Image.fromarray(np.where(np.asarray(gray) >= thresholds, 255, 0).astype('uint8')).convert('1')


def render_for_source(image, source, width=800, height=448, method='ordered',
                      contrast=1.25, brightness=1.03):
    """Keep source notices in-frame and put required credits outside the footage."""
    lines = source.get('image_credit_lines', [])
    if not lines:
        return render(image, width, height, method, contrast, brightness,
                      preserve_frame=source.get('preserve_frame', False))
    font = ImageFont.load_default(size=max(10, round(width * 12 / 800)))
    spacing = max(14, round(width * 16 / 800))
    footer = spacing * len(lines) + 6
    if any(font.getlength(line) > width - 16 for line in lines) or height - footer < 64:
        raise ValueError('Target dimensions cannot fit required source attribution')
    footage = render(image, width, height - footer, method, contrast, brightness,
                     preserve_frame=True)
    result = Image.new(footage.mode, (width, height), 255)
    result.paste(footage, (0, 0))
    draw = ImageDraw.Draw(result)
    for i, line in enumerate(lines):
        draw.text((8, height - footer + 3 + spacing * i), line, font=font, fill=0)
    return result
