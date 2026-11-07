"""Display-only tone mapping and per-depth device renditions."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from abyss.publication import publish
from abyss.retention import retain
from abyss.tone import DEPTHS, display_variants, tone_map
from test_trmnl import LAYOUTS, Markup, catalog, render

BASE = 'https://site.example/abyss'


def lamp_lit_seabed(width=400, height=300):
    """Bright hazy centre, dark top, faint seabed marks and a red anemone."""
    y, x = np.mgrid[0:height, 0:width]
    light = np.exp(-(((x - width / 2) / (width * .45)) ** 2 + ((y - height * .6) / (height * .4)) ** 2))
    base = 40 + 130 * light + 6 * np.sin(x / 3.0) * (y > height * .4)
    rgb = np.stack([base, base * .98, base * .92], axis=-1)
    rgb[200:215, 300:315] = (150, 60, 60)  # Red on sand: similar luminance, different hue.
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


class ToneTests(unittest.TestCase):
    def test_renditions_keep_size_and_flatten_lamp_falloff(self):
        image = lamp_lit_seabed()
        source = np.asarray(image.convert('L'), dtype=float)
        for depth in DEPTHS:
            with self.subTest(depth=depth):
                result = tone_map(image, depth)
                self.assertEqual((result.mode, result.size), ('L', image.size))
                toned = np.asarray(result, dtype=float)
                # The lamp's centre-to-edge falloff takes a smaller share of the tonal range.
                falloff = lambda a: ((a[150:200, 180:220].mean() - a[:, :40].mean())
                                     / (np.percentile(a, 99) - np.percentile(a, 1)))
                self.assertLess(falloff(toned), falloff(source) - .05)
                # Local seabed texture gains contrast.
                self.assertGreater(toned[150:250, 50:350].std(), source[150:250, 50:350].std())
                np.testing.assert_array_equal(toned, np.asarray(tone_map(image, depth)))

    def test_two_bit_is_firmer_than_four_bit_and_red_separates_from_sand(self):
        image = lamp_lit_seabed()
        two, four = (np.asarray(tone_map(image, d), dtype=float) for d in ('2bit', '4bit'))
        self.assertGreater(two[150:250, 50:350].std(), four[150:250, 50:350].std())
        plain = np.asarray(tone_map(image, '2bit', {'red_accent': 0}), dtype=float)
        sand, anemone = (slice(200, 215), slice(270, 285)), (slice(200, 215), slice(300, 315))
        self.assertGreater(two[sand].mean() - two[anemone].mean(), plain[sand].mean() - plain[anemone].mean())

    def test_opt_in_and_unknown_depth(self):
        self.assertEqual(display_variants(lamp_lit_seabed(), None), {})
        self.assertEqual(set(display_variants(lamp_lit_seabed(64, 48), True)), set(DEPTHS))
        with self.assertRaises(ValueError):
            tone_map(lamp_lit_seabed(), '8bit')

    def test_published_renditions_are_separate_and_protected_while_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = lamp_lit_seabed()
            metadata = {'source_id': 'camera', 'source_name': 'Camera', 'published_at': '2026-11-07T00:00:00+00:00',
                        'original_url': 'https://source.example/frame.jpg'}
            variants = display_variants(image, True)
            result = publish(root, {'id': 'camera'}, image, metadata, BASE, display_image=image,
                             display_variants=variants)
            files = {}
            for depth in DEPTHS:
                url = result[f'display_image_{depth}_url']
                path = root / 'public' / url.removeprefix(BASE + '/')
                files[depth] = path
                with Image.open(path) as saved:
                    self.assertEqual(saved.mode, 'L')
                    np.testing.assert_array_equal(np.asarray(saved), np.asarray(variants[depth]))
                self.assertEqual(result[f'display_image_{depth}_bytes'], path.stat().st_size)
                self.assertNotEqual(url, result['display_image_url'])
            # The clean colour photo and the QR page are unchanged by tone mapping.
            with Image.open(root / 'public' / result['display_image_url'].removeprefix(BASE + '/')) as clean:
                np.testing.assert_array_equal(np.asarray(clean), np.asarray(image))
            (root / 'public' / 'sources' / 'camera' / 'latest.json').write_text(__import__('json').dumps(result))
            retain(root, BASE)
            self.assertTrue(all(p.exists() for p in files.values()))


class ToneLayoutTests(unittest.TestCase):
    def test_layouts_show_one_rendition_per_screen_depth(self):
        data = catalog()
        toned = copy.deepcopy(data)
        toned['sources']['ooi-axial'].update(display_image_4bit_url='https://example.invalid/4.png',
                                             display_image_2bit_url='https://example.invalid/2.png')
        for layout in LAYOUTS:
            for fill in (False, True):
                with self.subTest(layout=layout, fill=fill):
                    images = [a for t, a in Markup(render(layout, toned, fill_photo=fill)).elements if t == 'img']
                    four, two = images[0], images[1]
                    self.assertEqual(four['src'], 'https://example.invalid/4.png')
                    self.assertEqual(two['src'], 'https://example.invalid/2.png')
                    fit = 'image--cover' if fill else 'image--contain'
                    for img in (four, two):
                        self.assertIn('image-dither', img['class'].split())
                        self.assertIn(fit, img['class'].split())
                    self.assertTrue({'1bit:hidden', '2bit:hidden'} <= set(four['class'].split()))
                    self.assertTrue({'hidden', '1bit:block', '2bit:block'} <= set(two['class'].split()))
                    # Sources without renditions keep the single native photo.
                    plain = [a for t, a in Markup(render(layout, data, fill_photo=fill)).elements if t == 'img']
                    self.assertEqual(len(plain), 1)
                    self.assertNotIn('hidden', plain[0]['class'].split())


if __name__ == '__main__':
    unittest.main()
