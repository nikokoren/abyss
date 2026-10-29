# Native TRMNL Framework 3.4

Abyss uses native layout, image containment, typography and title-bar components
in all four views. There is no custom device CSS, browser JavaScript, fixed view
size or extra framework import. Settings select Framework **3.4.4**, the exact
release used by the browser checks and recorded in [framework.json](framework.json).

## Install or update

Download `/abyss-trmnl.zip` from the published site and import the **whole recipe**.
The archive includes `settings.yml`, `transform.py`, four layouts, Shared and this
guide, plus [settings.txt](settings.txt) with exact polling settings, the complete
Custom Fields YAML to paste into the editor, and the full recipe settings.yml. Updating only the Liquid markup is insufficient for rotation.

The export also includes the public recipe overview and an **About Abyss** field
with the introduction, camera locations and depths, official maps, full science
credits and a support link. Re-import settings to receive About updates; they
do not add text to the device layouts. The same introduction appears on the
public site's About section.

For a manual update, keep the polling URL (`/catalog.json`, GET) and playlist;
apply the generated settings, including the optional **multiple** select
`source_ids`, enable the native **Python serverless transform**, and install
[transform.py](transform.py). Replace each matching markup tab:

| Editor layout | File |
| --- | --- |
| Full | [full.liquid](full.liquid) |
| Half horizontal | [half_horizontal.liquid](half_horizontal.liquid) |
| Half vertical | [half_vertical.liquid](half_vertical.liquid) |
| Quadrant | [quadrant.liquid](quadrant.liquid) |
| Shared | [shared.liquid](shared.liquid) |

Remove the old Shared CSS. Shared now contains documentation only. The host
supplies the screen/view wrappers and Framework assets. Preview all layouts and
verify the physical device after importing; repository tests cannot update your
TRMNL account. Re-import settings when adding cameras: static dropdown options
do not automatically change when the catalog changes.

## Camera selection and refresh

| Selected feeds | Display behavior |
| --- | --- |
| None (default) | Cycle through every published feed. |
| One | Keep that camera on screen. |
| Several | Cycle through that subset in catalog order. |
| All | Same rotation as selecting none. |

Each turn uses the camera's latest published best image. An offline camera keeps
its slot and its last good image; it is not removed after repeated failures.
A camera with no published image cannot be shown yet. Withheld sources remain
excluded. A selection containing only deleted/unknown IDs shows an empty state
rather than an unrelated feed. Legacy single `source_id` settings are supported
only while the new `source_ids` field is absent; explicitly clearing the new
field always means all feeds.

The native plugin refresh defaults to **15 minutes**, independently of the
cloud processing schedule (every three hours, at 00:23, 03:23, 06:23, 09:23,
12:23, 15:23, 18:23 and 21:23 UTC). The transform stores a small
per-device cursor in TRMNL's native `trmnl_state` / `trmnl.state`. It advances once
when a new refresh slot is observed, and keeps the same camera across layouts
within that slot. Slots use the native data-fetch timestamp and the slower of
the plugin and device refresh intervals. Skipped slots advance once on return,
so missed refreshes do not systematically skip particular cameras. Changing the
selected subset applies immediately. Cursors are bounded to the 16 most recently
seen devices and remain below the native 8 KiB state limit.

A device wake can show a cached render if it occurs faster than plugin refresh.
Match the native plugin refresh to the intended device cadence; rotation cannot
force TRMNL to regenerate a cached screen. Polling/transform failures leave the
previous good native output in place. There are no transform network requests,
extra dependencies, external rotation service or per-device video jobs.

The normal view shows the picture and the native title bar: **Abyss** at bottom
left, current camera location and known depth at bottom right. The location can
clamp in small views; depth does not shrink away. A short delayed-update status
appears for retained/stale images. Recording times, source health, full
acknowledgment and reuse terms live on the product/settings pages. The required
compact source credit is a native `label label--small` below the photo, so it
follows the framework's light/dark text colors. No credit is rasterized into the
device photograph. A separate downloadable version retains embedded attribution.

**Show QR code** is optional and off by default, and applies **only to full-screen
view**. It overlays the bottom-right corner of the content area using native
`relative`, `absolute bottom--0 right--0` and sizing utilities. It takes no space
away from the photo or title bar and never appears in halves or quadrant.
The recipe uses the framework's standard screen padding so its gap above the
title bar matches the right screen inset; the native credit
row reserves its width. The QR raster has a one-module white scan margin,
reduced from four; removing it entirely fails decoding on the dark canvas.
Cached observation codes are refreshed during
publication without changing their destinations.
It opens an immutable first-party observation page, rather
than a changing camera homepage. That page includes the exact displayed still
and either the original snapshot or the original MP4 positioned at the selected
frame's timestamp. The phone browser controls video playback; the source must
still serve the recording. QR pixels are not dithered and no external QR service
receives the link. Outages retain the image's existing QR destination too.

## Image resolution

Production now preserves the **highest resolution supplied by each selected
source**. The OOI still cameras provide **5344 × 4008** JPEGs, decoded without
draft scaling; video frames keep their stream dimensions without the previous
960 × 600 extraction scale. The device photograph is a lossless RGB PNG with
every original photo pixel preserved, accompanied by native theme-aware credit.
The separate downloadable image appends a credit band below the complete frame.
Metadata records
both source and published dimensions plus the actual PNG byte size. Native
`image-dither` delegates resizing, palette conversion and dithering to TRMNL's
renderer for its active device. The QR image has no such flag.

There is no Abyss grayscale conversion, contrast adjustment, sharpening or
dithering in the default `native` delivery mode. Low-resolution scoring/encoder
work does not change the published pixels. Explicit CLI preview methods still
support the old 800 × 448 comparison variants; production no longer uses them.
Full-resolution lossless photographs consume more delivery bandwidth and retained
storage. The published snapshot has a 640 MiB budget: current camera images and
saved session winners are protected; older full-size history retires while QR
observation pages retain previews or original-footage links. See
[retention policy](../docs/retention-and-sessions.md).
The display image uses `display_image_url`; `image_url` remains the attributed
download. `display_image_bytes` and `image_bytes` expose both asset sizes.

## Generate settings and verify

```sh
python -m abyss.cli recipe --base-url https://OWNER.github.io/abyss
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m playwright install chromium
python scripts/check_trmnl_browser.py --framework-root /path/to/trmnl-framework
```

Settings require at least one reviewed source with a published image, including
retained offline images. The framework checkout must contain the released
`public/css/3.4.4`, `public/js/3.4.4` and `public/fonts` assets. CI pins the official
release commit. Use `--chromium /usr/bin/chromium` for an installed browser.
Optional `--catalog` and `--image` test a real published still; otherwise the test
uses a clearly labeled synthetic image.

The 88-case browser matrix covers four views on OG, v2 and Kindle 2024 profiles
in both orientations, retained/empty/long-name states, and no-padding mashups.
It checks bounds, image/text containment, title-bar separation, neighboring
cells and browser errors, verifies full-screen-only bottom-right QR overlays,
decodes each QR from its actual rendered size, and checks white native credit
on a black canvas in dark mode.
CI uploads `native-trmnl-3.4-previews`; local reports
live under `output/validation/trmnl/`. Rotation tests exercise the actual native
transform, persisted state and Liquid templates, including all selection modes,
missed cycles, separate devices, outages and updated image URLs.

Contract references: [official transform guide](https://github.com/usetrmnl/trmnlp/blob/30e770ba7da3f2a195aa70cd1571a35c6013947f/README.md#serverless-transforms),
[native state](https://github.com/usetrmnl/trmnlp/blob/30e770ba7da3f2a195aa70cd1571a35c6013947f/lib/trmnlp/transform_state.rb),
[native input context](https://github.com/usetrmnl/trmnlp/blob/30e770ba7da3f2a195aa70cd1571a35c6013947f/lib/trmnlp/user_data_assembler.rb),
[Framework 3.4.4 source](https://github.com/usetrmnl/trmnl-framework/tree/f366a9303bbce97adca73d5747da8e2212379bbc).
