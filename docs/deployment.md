# Deploy and operate

## Release gates

Do not enable a scientific feed with the fixture registry or by simply flipping
OOI's status. First complete source access, timestamp, actual-frame, partial
retrieval, and rights checks in [sources.md](sources.md). Cloud publication and TRMNL installation require the account-level steps below.
Local tests do not establish hosted deployment readiness.

The four production cameras have passed technical and attributed-still reuse
review. Pages is deployed at https://nikokoren.github.io/abyss, and hosted live
verification has passed. ASHES video filenames retain an explicit UTC assumption;
the still-camera filenames explicitly declare UTC. Physical-device checks remain
unrecorded. See [current validation](validation.md) and the
[publication handoff](publication.md).

For a new Codex environment, use its network settings if local source inspection
is required. Saving a draft does not apply network access. Environment snapshot
publication is separate from GitHub Pages deployment and TRMNL recipe submission.
Never paste credentials into chat or source files.

## Configure a new GitHub deployment

1. Code and the OOI approval are pushed to this repository's default `main`
   branch. Review the source registry and linked evidence before deployment.
2. Use a public repository for GitHub Free Pages. For a private repository,
   verify an eligible Pages plan and remaining Actions allowance. Confirm
   organization policy permits Actions, Pages and bot writes. Check billing
   controls before scheduling; no account-specific cost guarantee has been made.
3. In repository **Settings → Pages**, select **GitHub Actions** as the source.
   Set repository Actions variable `PUBLIC_BASE_URL` to the actual public HTTPS
   site root: `https://nikokoren.github.io/abyss` for this repository (or the
   configured custom domain). This is a non-secret variable. Public URLs must not require login.
4. Validate and enable one real source in the registry. Use workflow_dispatch to
   run **Process and publish ocean stills**. The pipeline retains source state
   and last-good images on the dedicated `ocean-output` branch. Do not apply
   protections preventing this branch's updates unless using a compatible bot
   permission policy. GitHub's automatic `GITHUB_TOKEN` is used; no personal token
   or camera API key is required for the implemented adapters.
5. Confirm Pages deployment succeeds and fetch `catalog.json`, the referenced
   immutable PNG, `sources/ID/latest.json`, and `health.json` over HTTPS. Check
   image dimensions, source credit, recording age and `fixture: false`.
   Measure workflow duration and `diagnostics.bytes_downloaded`. Compare current
   billing/Pages usage to [architecture.md](architecture.md).
6. Download `/abyss-trmnl.zip` from the public site, which contains
   settings, the Python serverless transform and all four native Framework 3.4
   layouts plus Shared. Import the whole recipe; updating just the five markup
   tabs does not install rotation. See [the update guide](../trmnl/README.md).
   Preview and test the actual device, including source
   changes, absent selections, outages and stale capture timestamps. No
   credentials or user-supplied arbitrary media URLs belong in recipe settings.

Schedule: every three hours at 00:23, 03:23, 06:23, 09:23, 12:23, 15:23,
18:23 and 21:23 UTC, away from the top of the hour. In Europe/Berlin on
29 October 2026 this is 01:23, 04:23, 07:23, 10:23, 13:23, 16:23, 19:23 and
22:23 CET; daylight-saving changes affect local time.
Native template, recipe and site-builder pushes also trigger deployment.
Scheduled jobs may run late or be dropped; a manual run is the recovery path.
Monitor default-branch schedule activation and public-repository inactivity
rules; do not treat scheduled output as a live camera.

## Cadence observations and adaptive search

The separate `observe-ooi.yml` workflow collects hourly directory metadata and
runs a three-recording coarse/fine benchmark on relevant code pushes or manual
request. Its `source-observations` branch is separate from image delivery and
rights approval. See [search-and-cadence.md](search-and-cadence.md). The observer
does not generate new public images every hour. Disable/reduce its frequency
when enough recording/publication observations are available; include its runner
startup costs if using a private repository.

## Personal preference learning

`review-gallery.yml` generates daily/manual review downloads and trusted feature
manifests. `train-preferences.yml` learns from owner-authored GitHub feedback
issues. Both persist to `preference-data`; the production workflow restores its
ready model and CPU encoder when needed. This does not publish the gallery on
Pages or bypass scientific source-rights approval. See [preferences.md](preferences.md).

## Last-good and restart behavior

`ocean-output` contains only generated `public/` and `state/` directories. Each
job restores them before processing. Publication writes a bounded root snapshot
with an exact force-with-lease on `ocean-output`, rejecting concurrent updates.
Source and preference branches are not rewritten; a metadata audit log keeps 32 runs.
The Pages artifact includes only `public/`, never source registry or internal
state. An unsuccessful processing step still publishes retained imagery and
updated health, then reports the workflow as failed. If persistence fails,
deployment is blocked so the current site remains unchanged.

This workflow intentionally makes no media downloads for an empty eligible
registry. It generates an empty catalog/health report and reports failure so
missing validation cannot be mistaken for successful ocean processing.
Regenerating settings retains offline feeds that have a published image, along
with their rotation slots and last-good metadata. Existing TRMNL installations
must re-import settings to receive new dropdown options. QR observation pages remain stable when older full PNGs retire; use those
pages for lasting references instead of bookmarking a PNG. `published_at` is the time the pipeline committed the image to its local
public bundle; actual Pages/CDN deployment occurs later and is visible in the
Actions deployment log.

The recipe defaults to an empty multi-select (cycle through all feeds) and a
15-minute native plugin refresh. One selection pins a camera; several cycle
through that subset. Device wakes faster than the plugin cadence may repeat
cached renders. The optional QR code is off by default and opens an immutable
observation page for the displayed image/recording. The QR is a bottom-right
photo overlay in full-screen view only. Attribution below the photo uses native
text that follows light/dark mode; the downloadable PNG retains an embedded
credit. Native `image-dither` lets
TRMNL render full-resolution RGB photographs for its device; Abyss no longer
pre-dithers or downsizes production exports. Inspect the actual `image_bytes`
and `display_image_bytes` and total site size because full-resolution lossless PNGs are much larger than
the old 800 × 448 bitonal output. The 640 MiB retention step protects current
images and session winners, retires older full PNGs, and preserves useful QR
observation destinations. See [the full policy](retention-and-sessions.md).

The output branch is durable state. Do not delete it casually: doing so loses
processing history and retained images, and may cause old recordings to be
processed again. Private local runs may use another `--output` directory.
The cloud environment snapshot preserves files and dependencies, not running
processes; no persistent server is needed by the CLI processing workflow.

## Troubleshooting

| Symptom | Check / action |
|---|---|
| Proxy CONNECT 403 | Inspect effective environment network policy. Review/save required domain settings; retry after application. Do not disable proxy/TLS or classify source as down. |
| Socket Operation not permitted | Permit loopback for the range bridge and test suite through the execution permission mechanism. No external server is needed. |
| Zero eligible sources / no settings export | Technical retrieval and rights evidence are missing, or no good frame has been published. Run `sources`, inspect source evidence and health. |
| Range ignored / inconsistent size or ETag | Keep source disabled or await a completed immutable recording. Full downloads are intentionally refused. |
| Byte budget exhausted | Compare size/GOP/seek metrics; reduce candidates or choose source-specific offsets only after measurements. Do not just remove the cap. |
| Extraction timeout / no PNG / unsupported codec | Inspect codec, duration and extraction errors. MP4 is the only currently permitted demuxer. The workflow does not implement HLS. |
| No acceptable frame | Review variants and score diagnostics. Last good frame is retained and the rejected recording is remembered. Tune source profile with real evidence. |
| Source cooling down | Inspect `retry_after`; backoff grows to 48 hours. `--force` bypasses it for explicit diagnosis and also reprocesses known recordings. |
| Metadata old despite successful run | Compare recording/capture versus publish/check timestamps. No new footage is an honest unchanged result. |
| Persisting outputs fails | Check contents:write, branch policy and concurrent edits. Do not force-push; preserve state and retry after resolving the conflict. |
| Pages deployment fails / 404 / login | Check Pages source, plan, environment approval, PUBLIC_BASE_URL and Actions deployment logs. Source extraction success does not prove public delivery. |
| No schedule runs | Workflow must be on default branch. Check disabled workflows, Actions policy and inactivity. Trigger a manual run. |
| Dropdown not updated | Regenerate settings from a published catalog and re-import. Static TRMNL fields do not update just because JSON changed. |
| Setup incomplete / rotation missing | Import the whole ZIP including transform.py and multi-select settings. Match native plugin refresh to device cadence. |
| Corrupt local state JSON | Preserve the damaged file for diagnosis and restore a known-good state from output branch history. Do not silently reset duplicate history. |

Never expose full source recordings or credentials. No user-tracking or camera
account management is part of the public site. If commercial/SaaS distribution
is intended, reassess hosting terms and scale before relying on Pages.

## Live production verification

`Verify deployed production` runs on GitHub after successful image publication
and can also be dispatched manually. It reads the current trusted shared model,
checks all production cameras and default rotation in the live Pages catalog,
then verifies Offshore uses that model with full-resolution RGB images and
required credit. It also checks the published About and Framework 3.4.4 recipe.
The job summary and `production-verification` artifact retain the exact image
URLs, model ID, dimensions and verification time. CDN propagation is retried
for up to eight attempts; an unresolved mismatch fails the check.
