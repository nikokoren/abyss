"""Display-only tone mapping for dim, unevenly lit cameras on low bit-depth screens.

The published download and QR pages keep the untouched photo. These renditions
only feed the TRMNL device image, which TRMNL still resizes and dithers itself.
Nothing here resizes, crops, denoises or sharpens the frame: each output pixel
is its input pixel through a smoothly varying, location-dependent tone curve.
"""
import numpy as np
from PIL import Image

# Tuned on Oregon Offshore frames: a bright, hazy centre falling off to a dark
# top edge, with grey animals and red anemones on grey sand. 2-bit screens (OG
# with current firmware, and 1-bit OG as a fallback) get four shades, so they
# need firmer midtone separation than 16-shade 4-bit screens such as TRMNL X.
PROFILES = {
    '4bit': {'flatten': .4, 'max_gain': 1.4, 'clahe_clip': 1.2, 'clahe_tiles': 6, 'black': .5,
             'white': 99.7, 'gamma': 1.0, 'red_accent': .35},
    '2bit': {'flatten': .7, 'max_gain': 1.4, 'clahe_clip': 2.0, 'clahe_tiles': 6, 'black': 4.0,
             'white': 99.5, 'gamma': 1.0, 'red_accent': .5},
}
DEPTHS = tuple(PROFILES)
TONE_REVISION = 2  # Bump when PROFILES or the algorithm change, to republish.
STATS_EDGE = 1024  # Long edge of the statistics copy; output stays full size.


def _luminance(rgb):
    r, g, b = (rgb[..., i] for i in range(3))
    return (.299 * r + .587 * g + .114 * b) / 255


def _stats_copy(gray, edge=STATS_EDGE):
    """Box-averaged copy for estimating illumination and histograms."""
    image = Image.fromarray(gray.astype(np.float32))
    scale = min(1.0, edge / max(image.size))
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.BOX)


def _upsample(small, size):
    return np.asarray(small.resize(size, Image.Resampling.BILINEAR), dtype=np.float32)


def _blur(values, sigma):
    """Separable Gaussian with mirrored edges."""
    radius = max(1, int(3 * sigma))
    kernel = np.exp(-.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (radius, radius)
        padded = np.pad(values, pad, mode='symmetric')
        values = np.apply_along_axis(np.convolve, axis, padded, kernel, mode='valid')
    return values


def _illumination(gray):
    """Smooth light-falloff field: the camera's lamp, not the scene."""
    # The field is very smooth, so a 128-pixel-wide copy describes it fully.
    small = np.asarray(_stats_copy(gray, 128), dtype=np.float64)
    field = Image.fromarray(_blur(small, max(small.shape) / 10).astype(np.float32))
    return np.maximum(_upsample(field, (gray.shape[1], gray.shape[0])), 1e-3)


def _clahe(values, clip, tiles):
    """Contrast-limited adaptive histogram equalization on [0, 1] floats.

    Tile histograms come from the statistics copy; the per-tile curves are then
    bilinearly blended and applied to every full-resolution pixel.
    """
    height, width = values.shape
    small = np.clip(np.asarray(_stats_copy(values), dtype=np.float32), 0, 1)
    sh, sw = small.shape
    ty, tx = min(tiles, sh), min(tiles, sw)
    bins = 256
    luts = np.empty((ty, tx, bins), dtype=np.float32)
    for j, rows in enumerate(np.array_split(np.arange(sh), ty)):
        for i, cols in enumerate(np.array_split(np.arange(sw), tx)):
            tile = small[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
            hist = np.bincount(np.minimum((tile * bins).astype(int), bins - 1).ravel(),
                               minlength=bins).astype(np.float64)
            limit = max(1.0, clip * tile.size / bins)
            excess = np.maximum(hist - limit, 0).sum()
            hist = np.minimum(hist, limit) + excess / bins
            cdf = np.cumsum(hist)
            luts[j, i] = (cdf - cdf[0]) / max(cdf[-1] - cdf[0], 1e-9)
    # Tile centres in full-resolution coordinates, clamped at the borders.
    gy = np.clip((np.arange(height) + .5) / height * ty - .5, 0, ty - 1)
    gx = np.clip((np.arange(width) + .5) / width * tx - .5, 0, tx - 1)
    y0 = np.minimum(gy.astype(int), ty - 1); y1 = np.minimum(y0 + 1, ty - 1); wy = (gy - y0)[:, None]
    x0 = np.minimum(gx.astype(int), tx - 1); x1 = np.minimum(x0 + 1, tx - 1); wx = (gx - x0)[None, :]
    result = np.empty_like(values, dtype=np.float32)
    band = 256  # Rows per pass keeps peak memory modest on 5344 x 4008 frames.
    for start in range(0, height, band):
        stop = min(start + band, height)
        index = np.minimum((np.clip(values[start:stop], 0, 1) * bins).astype(np.int32), bins - 1)
        rows0, rows1, fy = y0[start:stop, None], y1[start:stop, None], wy[start:stop]
        top = luts[rows0, x0[None, :], index] * (1 - wx) + luts[rows0, x1[None, :], index] * wx
        bottom = luts[rows1, x0[None, :], index] * (1 - wx) + luts[rows1, x1[None, :], index] * wx
        result[start:stop] = top * (1 - fy) + bottom * fy
    return result


def tone_map(image, depth, overrides=None):
    """Grayscale e-paper rendition of ``image`` for a ``'2bit'`` or ``'4bit'`` screen."""
    if depth not in PROFILES:
        raise ValueError(f'Unknown display depth: {depth}')
    p = {**PROFILES[depth], **(overrides or {})}
    rgb = np.asarray(image.convert('RGB'), dtype=np.float32)
    gray = _luminance(rgb)
    if p['red_accent']:
        # Red anemones and shrimp share the sand's luminance; darken warm
        # chroma so they separate in grey without shifting neutral tones.
        r, g, b = rgb[..., 0] / 255, rgb[..., 1] / 255, rgb[..., 2] / 255
        redness = np.clip(r - np.maximum(g, b) - .04, 0, None)
        gray = np.clip(gray - p['red_accent'] * redness, 0, 1)
    if p['flatten']:
        light = _illumination(gray)
        # Cap the lift: the dark water holds mostly drifting particles, and
        # boosting it fully turns them into dither speckle.
        gain = np.clip((float(light.mean()) / light) ** p['flatten'], 1 / p['max_gain'], p['max_gain'])
        gray = gray * gain
    if p['clahe_clip']:
        gray = _clahe(np.clip(gray, 0, 1), p['clahe_clip'], p['clahe_tiles'])
    sample = np.asarray(_stats_copy(gray), dtype=np.float32)
    low, high = np.percentile(sample, [p['black'], p['white']])
    gray = np.clip((gray - low) / max(float(high - low), 1e-3), 0, 1)
    if p['gamma'] != 1:
        gray = gray ** p['gamma']
    return Image.fromarray(np.round(gray * 255).astype(np.uint8))


def display_variants(image, settings):
    """Depth-keyed renditions when a source opts in with ``display_tone``."""
    if not settings:
        return {}
    overrides = settings if isinstance(settings, dict) else {}
    return {depth: tone_map(image, depth, overrides.get(depth)) for depth in DEPTHS}
