# Abyss — Ambient Ocean for TRMNL

A cloud-run underwater camera discovery and image-selection pipeline. It samples
research recordings, ranks frames, produces monochrome e-paper stills, and serves
attributed metadata for a source-selectable TRMNL recipe.

**Status: implemented; OOI access, range support and visible vent footage were
verified by the user on a Mac.** GitHub-hosted validation also passed: four frame seeks, 10.26 MB of video
payload (1.08% of the 949 MB recording), in 20.1 seconds. See the
[runner report](docs/evidence/ooi-20261027-github-actions.json).
Codex's proxy restriction is an infrastructure limitation, not an upstream OOI
failure. **OOI derived-still reuse is now reviewed and enabled**, with required
NSF/WHOI/UW credit embedded in exported images; see the
[rights review](docs/ooi-rights-review.md). Public Pages delivery and TRMNL
device rendering remain unverified. See [runner validation](docs/runner-validation.md),
[source audit](docs/sources.md), and [acceptance status](docs/validation.md).

## Develop

Requires Python 3.11+ and FFmpeg/ffprobe (tested with Python 3.12 and FFmpeg 7.1.5).

```sh
cd /workspace/abyss
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
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

A real run requires a public HTTPS base URL. OOI is the currently eligible real
source. Other candidates remain excluded until their own reviews are complete.

## Recent-recording search and cadence

Production selection compares the three newest unseen recordings: four coarse
samples each, then up to four extra samples around the strongest moments, under
one shared 64 MiB video budget. The live runner benchmark extracted 16 frames
across three recordings using 44.5 MB in 55 seconds and selected an older clip
over the newest. The independent hourly metadata observer measures
filename intervals and first appearances without repeatedly downloading video.
See [search and cadence](docs/search-and-cadence.md) for exact limits, reporting,
and how publication-delay observations differ from a baseline archive listing.

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
- `.github/workflows/`: tests and twice-daily cloud processing/Pages delivery.
- `docs/viewer.html`: static source selector, still viewer, age and attribution.

[Architecture and budgets](docs/architecture.md) · [Deployment and troubleshooting](docs/deployment.md)

No license has been chosen for the project's code. Source imagery remains subject
to its own rights; a public download URL does not establish reuse permission.
