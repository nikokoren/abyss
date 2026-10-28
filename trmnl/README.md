# Native TRMNL Framework 3.4

Abyss uses the native `layout`, `flex`, `image`, `label`, `description`, and
`title_bar` components. The markup contains no custom CSS, inline styles,
fixed view dimensions, browser scripts, or framework imports. The same flexible
markup is supplied for every layout; the platform's view controls sizing.

## Update an existing plugin

Keep the existing polling URL, source selection and playlist configuration.
In the plugin's markup editor, replace the contents of each matching layout tab:

| Editor layout | File |
| --- | --- |
| Full | [full.liquid](full.liquid) |
| Half horizontal | [half_horizontal.liquid](half_horizontal.liquid) |
| Half vertical | [half_vertical.liquid](half_vertical.liquid) |
| Quadrant | [quadrant.liquid](quadrant.liquid) |
| Shared | [shared.liquid](shared.liquid) |

Remove the previous Shared CSS as well. Each view is self-contained; Shared now
contains only documentation. The TRMNL platform supplies `screen`, `view`, mashup
containers, CSS and the framework runtime. Do not add a second set of wrappers or
load framework assets inside the plugin markup.

Use a TRMNL renderer running Framework **3.4**. Browser validation uses the exact
published **3.4.4** release, recorded in [framework.json](framework.json), without
changing its CSS or fonts. The manifest documents compatibility; it does not
change the framework version selected by the host.

After the next successful site deployment, all files are available under
`/trmnl/` and together in `/abyss-trmnl.zip`. The archive also includes
the generated `settings.yml` when a healthy catalog is available.

Preview each layout, then add it to a device or mashup. The framework sizes the
layout and title bar for the active view and applies device typography and scale.
The image uses native containment, preserving source notices and aspect ratio.
The normal screen contains the image and native title bar only: **Abyss** at
bottom left, camera location and depth at bottom right. The location uses the
framework's native clamp when space is tight; the depth does not shrink away.
A brief status label appears only when an update is delayed or a test fixture
is displayed. Recording times, freshness details, full attribution and reuse
terms are available in settings and on the product page. One compact source
credit remains in the PNG, without a duplicate markup credit block.

Current OOI depth is displayed as **~1,540 m**, rounded from the operator's
preliminary 1,543 m deployment record. See the
[depth evidence](../docs/evidence/ooi-camera-depth-20261028.json).

The 800×448 upstream image is still a raster; a larger device does not create
additional photographic detail.

## New installation and polling

Generate settings from a healthy published catalog:

```sh
python -m abyss.cli recipe --base-url https://OWNER.github.io/abyss
```

Use those settings and the five markup files to configure a private polling
plugin. The recipe polls `/catalog.json` with GET. Its native source select
persists as `trmnl.plugin_settings.custom_fields_values.source_id`; the views
select `sources[source_id]` and fall back to `default_image` when necessary.
Images are preprocessed by the scheduled cloud job, so switching source does
not trigger a new video job or expose credentials.

Re-import generated settings when adding sources or changing the available
options. Existing settings retain their old choices, but removed selections
still fall back to retained imagery. No healthy source means no settings export.

## Verification

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p test_trmnl.py -v
python -m playwright install chromium
python scripts/check_trmnl_browser.py --framework-root /path/to/trmnl-framework
```

The framework checkout must include the released `public/css/3.4.4`,
`public/js/3.4.4` and `public/fonts` assets. CI checks out the exact official
release commit. Use `--chromium /usr/bin/chromium` with an installed browser.
Optional `--catalog` and `--image` use a real published catalog and still;
otherwise the browser test uses a clearly labeled synthetic image.

The browser matrix covers full, both halves and quadrant on OG, v2 and Kindle
2024 profiles in portrait and landscape, plus retained/stale, unknown-time,
empty and long-name cases. It checks view bounds, title-bar separation, text
and image containment, neighboring mashup cells and browser errors. Screenshots
and a JSON report are saved under `output/validation/trmnl/` and uploaded by CI
as `native-trmnl-3.4-previews`. These checks do not substitute for a physical
screen test or access to your TRMNL account's preview renderer.

Framework reference: [official source](https://github.com/usetrmnl/trmnl-framework/tree/f366a9303bbce97adca73d5747da8e2212379bbc),
[3.4 structure](https://trmnl.com/framework/docs/3.4/structure),
[image containment](https://trmnl.com/framework/docs/3.4/image),
[title bar](https://trmnl.com/framework/docs/3.4/title_bar).
