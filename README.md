# Abyss — Ambient Ocean for TRMNL

A cloud-run underwater camera discovery and image-selection pipeline. It samples
research recordings, ranks frames, produces monochrome e-paper stills, and serves
attributed metadata for a source-selectable TRMNL recipe.

**Status: implemented and fixture-tested; not yet a validated ocean feed.**
OOI access was denied by this build environment's outbound policy. No scientific
source has been promoted to the dropdown, no imagery rights have been assumed,
and no scientific feed has been deployed. See [source audit](docs/sources.md) and
[acceptance status](docs/validation.md).

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

A real run requires a public HTTPS base URL. The registry defaults to no eligible
sources and intentionally fails a processing run until validation is complete.

## Project map

- `abyss/network.py`: allowlisted HTTPS, capped byte ranges, FFmpeg loopback bridge.
- `abyss/adapters.py`: OOI UTC directory discovery and configurable direct-file adapter.
- `abyss/imaging.py`: quality/novelty scoring and e-paper rendering.
- `abyss/pipeline.py`: processing history, backoff, timestamps, last-good retention.
- `abyss/publication.py`: atomic metadata and content-addressed image publication.
- `abyss/recipe.py`, `trmnl/`: TRMNL dropdown export and Liquid rendering.
- `.github/workflows/`: tests and twice-daily cloud processing/Pages delivery.
- `docs/viewer.html`: static source selector, still viewer, age and attribution.

[Architecture and budgets](docs/architecture.md) · [Deployment and troubleshooting](docs/deployment.md)

No license has been chosen for the project's code. Source imagery remains subject
to its own rights; a public download URL does not establish reuse permission.
