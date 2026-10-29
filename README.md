# Abyss — Ambient Ocean for TRMNL

A window into the deep Pacific, quietly on your TRMNL. Explore hydrothermal
vents on Axial Seamount, a methane seep at Southern Hydrate Ridge, and the
Oregon Offshore seafloor.
U.S. public investment in NSF's Ocean Observatories Initiative makes these
extraordinary observations possible; open science lets the rest of us look in.

Abyss samples research recordings, ranks frames, preserves full-resolution color
stills, and serves attributed metadata for a source-selectable TRMNL recipe.
The recipe's About section includes the camera locations, approximate depths,
and official regional maps, site maps and array illustrations.

**Status: deployed with four real OOI cameras.** GitHub-hosted processing,
Pages delivery and live production checks have passed. The current recipe uses
native TRMNL Framework **3.4.4**, full-resolution colour images, a shared
owner-trained preference model and required OOI/WHOI/UW/NSF attribution.
Processing runs every three hours; TRMNL's separate 15-minute refresh rotates
saved camera views. Offline cameras retain their last good image.

Start with the [publication handoff](docs/publication.md),
[installation guide](trmnl/README.md) and [current validation status](docs/validation.md).
[Source access](docs/sources.md) and [imagery reuse rights](docs/ooi-rights-review.md)
are documented separately. A Codex proxy restriction does not establish an
OOI outage. Physical-device rendering remains unverified, and the project's
code license is still undecided.

## Develop

Requires Python 3.11+ and FFmpeg/ffprobe (tested with Python 3.12 and FFmpeg 7.1.5).

```sh
cd /workspace/abyss
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m abyss.cli sources
```

Tests include real H.264 decoding and HTTP range serving on loopback. A sandbox
that disables sockets must permit loopback for that test; it is not skipped.
No API keys, services, Docker, or computer left online are needed for processing.
GitHub's runners perform recurring work after deployment.

## Exercise the entire pipeline safely

```sh
python scripts/make_fixtures.py
python -m abyss.cli --registry output/fixtures/registry.json run \
  --local-video output/fixtures/pan.mp4 --interval 2 --candidates 4 \
  --recorded-at 2026-01-01T00:00:00Z --output output/demo \
  --base-url https://example.invalid/demo
python -m abyss.cli recipe --output output/demo \
  --base-url https://example.invalid/demo --destination output/demo/settings.yml
python -m abyss.cli inspect --source ooi-axial \
  --local-video output/fixtures/pan.mp4 --interval 2 --candidates 3 \
  --output output/comparison
```

`output/demo/public/` contains an immutable PNG, `latest.json`, `catalog.json`,
and `health.json`; `output/demo/state/` contains durable processing history.
Synthetic output is marked `fixture: true` and never validates a real camera.
Never deploy the fixture registry as a scientific feed.
`output/comparison/` contains grayscale, threshold, ordered, and Floyd–Steinberg
versions per candidate plus a measured inspection report.

## Connect a real source

```sh
python -m abyss.cli inspect --source ooi-axial --output output/ooi-inspection
```

Inspection does not publish or change registry eligibility. It discovers a
recording, extracts candidates using a capped range bridge, writes four image
variants, and records bytes, request count, duration, codec, timings, and scores.
Review the images and source terms. Record real validation evidence in
`sources.json` as explained in [adding sources](docs/adding-sources.md). Only
then set `status` to `validated` and run:

```sh
python -m abyss.cli run --base-url https://OWNER.github.io/abyss
python -m abyss.cli recipe --base-url https://OWNER.github.io/abyss
```

A real run requires a public HTTPS base URL. The published camera choices, in
About/rotation order, are ASHES: Mushroom vent, International District: Tiny Towers,
Southern Hydrate Ridge: Einstein's Grotto, and Oregon Offshore: seafloor.
Oregon Shelf and both water-column cameras remain on image-quality hold.
See [camera access and evidence](docs/additional-cameras.md).

## Native TRMNL views

The device UI uses **TRMNL Framework 3.4**, tested against the official 3.4.4
release. Full, half horizontal, half vertical and quadrant layouts use native
components, containment and typography, with no custom CSS or fixed view sizes.
See [the recipe update guide](trmnl/README.md). Import the whole `/abyss-trmnl.zip`,
including settings and the native Python transform, to install rotation. No
feeds are selected by default: the device cycles through all published cameras.
One selection pins a camera; several rotate through that subset. Offline feeds
keep their slot and last good image. The default plugin refresh is 15 minutes,
independently of the three-hour image-processing schedule.

**Show QR code** is optional and off by default. Scanning opens the exact image
or its original video at the selected timestamp, even after newer footage is
published. Full-resolution RGB PNGs preserve the source pixels (including
5344 × 4008 camera snapshots); TRMNL's native `image-dither` handles the device's
palette and scaling. Source credit uses native theme-aware text below the
photo; the downloadable version retains embedded credit. The QR overlays the
photo's bottom-right corner in full-screen view only.
See the guide for image sizes, native caching and storage considerations.

## Recent-recording search and cadence

Production samples up to six coarse frames per recent video recording, then
six refinement frames across three sessions, under one shared 96 MiB budget.
Each recording's winner is saved; current selection compares recent session
winners and reuses compatible cached scores. The maximum is 24 frames per search.
[Retention, session selection and fresh evaluation](docs/retention-and-sessions.md)
describes limits, preserved QR observations and model validation.

Published images are bounded to a 640 MiB site budget. Current and saved session
winners stay at source resolution; older QR pages retain compact previews and
original-footage links. The generated output branch is an exact-lease snapshot,
so retired PNG history does not remain reachable through branch ancestry.

The three still-camera feeds compare two recent JPEGs per camera under a 48 MiB
search cap, preserving the full frame and required credit. Their upstream
archives show half-hour bursts; Abyss's publication schedule runs every three hours.

## Train your preferences

A self-contained A/B review gallery supports neither/repetitive choices, browser
saving, backups and GitHub feedback submission. A CPU image encoder and small
ranking model learn from your choices and guide both refinement and selection.
Download the latest **Build preference review gallery** Actions artifact to start;
there are no invented preference labels in the initial model.
See [the preference guide](docs/preferences.md) for the complete workflow.

## Project map

- `abyss/network.py`: allowlisted HTTPS, capped byte ranges, FFmpeg loopback bridge.
- `abyss/adapters.py`: OOI UTC directory discovery and configurable direct-file adapter.
- `abyss/preferences.py`, `abyss/feedback.py`: pretrained appearance features and owner-authored preference learning.
- `abyss/review.py`, `web/review/`: downloadable review gallery and backup/submission flow.
- `abyss/search.py`: bounded multi-recording coarse/fine selection.
- `abyss/cadence.py`, `abyss/study.py`: hourly archive observations and runner benchmark.
- `abyss/imaging.py`: quality/novelty scoring and e-paper rendering.
- `abyss/pipeline.py`: processing history, backoff, timestamps, last-good retention.
- `abyss/publication.py`: atomic metadata and content-addressed image publication.
- `abyss/recipe.py`, `trmnl/`: TRMNL dropdown export and Liquid rendering.
- `.github/workflows/`: tests and three-hourly cloud processing/Pages delivery.
- `docs/viewer.html`: static source selector, still viewer, age and attribution.

[Architecture and budgets](docs/architecture.md) · [Deployment and troubleshooting](docs/deployment.md)

No license has been chosen for the project's code. Source imagery remains subject
to its own rights; a public download URL does not establish reuse permission.
