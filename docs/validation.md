# Validation evidence and remaining acceptance gates

## Native rotation, optional QR and source-resolution delivery — 28 October 2026

**80/80 Python tests passed**, plus the review JavaScript tests.
The native Python transform is exercised with empty/single/multiple/all
selections, persisted per-device cursors, repeated and missed refresh slots,
selection changes, legacy settings, latest-image updates and offline retention.
All four Liquid views display the rotated camera's location and depth. Bundle
checks verify the actual ZIP includes `transform.py` and current settings, with
no stale files or Python bytecode. Generated YAML was parsed to confirm an empty
optional multi-select, three feed options, QR off and native Python/3.4.4 settings.

Full-resolution color tests compare every source pixel with the published
display photo, verify a separate attributed download, preserve a 5344 × 4008 JPEG
without decoder scaling, and confirm real FFmpeg frames retain stream size.
Changing delivery mode reprocesses known footage once. Native delivery writes
lossless RGB PNGs without resizing, sharpening, grayscale conversion or Abyss
dithering. The clean device photo uses native attribution text that follows
light/dark mode; the downloadable image retains embedded credit. Metadata includes source/output dimensions
and actual file bytes; full-resolution storage growth must be monitored.

**88/88 Chromium cases passed** against unmodified Framework 3.4.4 assets:
all four views on OG, v2 and Kindle 2024 in landscape and portrait, with QR on
and off, plus dark-mode and retained/empty/long-name/no-padding cases. All 12 QR
overlays decoded successfully from their actual rendered sizes. The code appears
only in full-screen view, with native absolute bottom/right positioning on the
photo. The 24 dark-mode cases check native white credit text on a black canvas.
Screenshots of the
full and smallest portrait views were visually reviewed. See the
[metadata-only report](evidence/trmnl-native-rotation-qr-20261028.json).
Observation-page tests verify immutable frame-specific links, video timestamps,
snapshot links, HTML escaping, invalid-URL exclusion and QR identity after newer
publication. Codes are generated locally without an external QR provider.

Native contract references and import steps are in the
[recipe guide](../trmnl/README.md). Import the whole recipe, including its serverless
transform and settings. These checks do not establish that a user's TRMNL account
has imported it or that the hosted device renderer has applied `image-dither`.
The local framework preview deliberately leaves color photos in color; dithering
is documented as a hosted-platform behavior, not CSS or browser JavaScript.

## Additional still cameras — 28 October 2026

**63/63 Python tests passed** (18.922 seconds). Seven still-image tests cover
camera/path/UTC filtering, truncated and shared-byte accounting, HTML/oversized
image rejection, source-specific large-image limits, measured 21 MP JPEG decoder
scaling, quality ranking without video probing, partial-failure retention and
publication/known-image skips. Existing FFmpeg, preference and native Liquid
checks remain in the suite.

The [real runner validation](https://github.com/nikokoren/abyss/actions/runs/40689383752)
retrieved and decoded twelve 21 MP JPEGs from six camera archives. Southern
Hydrate Ridge and International District passed technical, rights and rendered
preview review and are enabled. Shelf and water-column cameras remain on
quality hold with separate reasons. [Exact results and byte counts](additional-cameras.md)
include immutable evidence; these decisions were not inferred from Codex access.

Native layouts are also checked with long camera locations, preserving the depth
field when the location needs clamping in a small view.

## Native TRMNL Framework 3.4 views — 28 October 2026

Full, half horizontal, half vertical and quadrant now use native Framework 3.4
components, with no custom CSS, fixed dimensions or device scripts. The title
bar is a sibling of the layout, allowing the host framework to size both.
Native image containment keeps the complete picture. The normal view shows
only the image and a native title bar: Abyss on the left, location and depth
on the right. A compact credit remains in the image; full acknowledgment,
recording time and freshness details are on the product/settings pages.
A delayed-update label appears only when the retained image needs that context.

**56/56 Python tests passed**, including actual Liquid rendering
for each view, source selection, removed-source fallback, missing capture time,
empty catalogs and HTML escaping. Review JavaScript tests also passed.

A local layout preview derived from the published OOI still (old generated
credit band removed and the new compact band rendered) and published catalog
with the verified location/depth fields passed **40 Chromium cases** using the
unmodified official 3.4.4 CSS, fonts and runtime: OG, v2 and Kindle 2024 profiles,
landscape/portrait, all four views, and extra quadrant cases for retained/stale,
unknown-time, empty and long-name states, plus all OG views without screen
padding. Production re-extracts source footage for the new credit; it does not
reuse this local preview image. Checks include view bounds, title-bar
separation, text/image containment, neighboring mashup cells and JavaScript
errors. Selected screenshots were visually inspected. See the
[metadata-only report](evidence/trmnl-3.4.4-layouts-20261028.json), which includes
the exact upstream release commit and asset hashes. Screenshots remain under
`output/validation/trmnl/`; CI also uploads synthetic-image previews.

Site packaging was exercised with and without settings: the ZIP includes all
four layouts, Shared, the guide and version manifest; current settings are
included when available and stale settings are removed otherwise. Retained
imagery remains unchanged. Device template changes now trigger site deployment. Render-profile changes
refresh known footage once so an updated image credit does not wait for a new
recording; subsequent unchanged runs still skip the processed recording.

Use [the markup update guide](../trmnl/README.md) for the existing plugin.
Browser checks do not establish that a user's TRMNL account has imported the
new markup or that a physical screen has rendered it.

## Earlier build and source-rights evidence

**Current update, 28 October 2026:** OOI derived-still reuse is approved and the
source is enabled. Required credits are embedded outside the complete footage,
and the viewer includes the official acknowledgment, terms, original recording
and platform DOI. See [the rights review](ooi-rights-review.md) for immutable
runner evidence. Earlier ledger entries below describe their original stage;
Pages deployment and actual TRMNL rendering still remain to be verified.

The rights/rendering update passed **51/51 Python tests** (10.133 seconds),
JavaScript review-core tests and viewer syntax checks. The new image test uses
an unusually wide frame with notices at both edges to detect cropping, checks
that credit pixels occupy a separate band, and verifies refusal of a target
too small for attribution. Actual FFmpeg pipeline tests verify that embedded
credit, acknowledgment, DOI and the UTC-assumption marker reach published
metadata. A synthetic 800×448 preview was visually inspected; this is not a
physical e-paper test. Official source terms were retrieved in successful
[GitHub run 40651933247](https://github.com/nikokoren/abyss/actions/runs/40651933247).

Build session: 2026-10-27. Python 3.12.14, FFmpeg 7.1.5, Pillow 11.3.0,
NumPy 2.2.6. Dependencies installed in `.venv`; no API keys used.

## Executed

- **21/21 automated tests passed** (latest suite: 9.515 seconds).
- The saved installation script was executed twice successfully. Dependency
  integrity (`pip check`), viewer JavaScript syntax, local HTTP delivery and a
  two-job output-branch restore/persist simulation also passed.
- In a synthetic padded MP4, three frames were extracted from a 10,406,714-byte
  file using 786,433 payload bytes (7.56%), four upstream range requests and
  0.989 seconds. This proves bounded seeking mechanics, not real OOI efficiency.

- Real H.264 MP4 fixture generation, ffprobe metadata, FFmpeg seeking and PNG
  extraction through the loopback byte-range bridge backed by mocked upstream
  HTTPS responses. This exercises FFmpeg's actual HTTP client, not just a stub
  subprocess. A padded larger MP4 checks that extraction uses a fraction of file
  bytes within a hard budget. Upstream origin/TLS for OOI remains untested.
- CLI fixture run produced an 800×448 1-bit PNG, content-addressed image URL,
  recording/frame/capture/extraction/processing/publication timestamps,
  attribution, quality metrics, catalog, durable state, health, and settings YAML.
- CLI inspection created 12 rendered variants across three synthetic scenes.
  Ordered, Floyd and threshold contact sheet was visually inspected. It is
  clearly marked synthetic and is not a proxy for scientific-image quality.
- Tests cover source eligibility/rights gating, discovery timestamp parsing,
  incomplete-recording exclusion, missing timestamps, bad exposure/blank frames,
  sharpness, similarity penalties, output modes/dimensions, host/protocol
  restrictions, range rejection/caching/budgets/truncation, repeat-run skips,
  publication errors, two-source delivery, invalid selection fallback,
  no-candidate retention, repeated failures/cooldown/recovery, and empty-recipe
  refusal. The suite outcome is recorded above.

## Acceptance ledger

| Requirement | Implementation evidence | Remaining gate |
|---|---|---|
| Cloud-only recurring processing | Scheduled Actions and Pages workflow | Execute in actual repository/account |
| At least one good real source | OOI adapter + inspection command | Origin access, actual footage and reuse validation |
| Efficient partial retrieval | Metered range bridge, cache, bounded requests and integration test | Measure real MP4/GOP transfer costs |
| Quality selection, moving camera | Uniform pan sampling + quality/composition/novelty ranking | Tune on actual scenes and device |
| Validated source dropdown | Gated settings generator and Liquid selection | No real source eligible yet; actual TRMNL import/render |
| Source switching | Two fixture sources in catalog and separate image paths | Two additional real sources if suitable; device selection test |
| Extensible sources | Registry + normalized adapters + shared extractor | Additional live/snapshot adapters not implemented |
| Honest metadata and rights | Separate timestamps, credits, unknown-time handling | Confirm OOI filename timezone and clip rights |
| Failure retention | Last-good immutable PNG/atomic JSON and durable output branch workflow | Test hosted persistence/deployment on Actions |
| Live/periodic/archive distinction | Registry, setup labels, template and viewer | Actual endpoint classification per source |
| Quotas and free tiers | Current public GitHub docs checked; cost model/caps | Account plan and real recurring run measurements |
| Source rights | Release eligibility requires real reviewed evidence | All scientific candidates still pending |

The initial build did not verify a hosted run, working ocean dropdown, source licensing clearance, physical
e-paper quality, or zero-cost production operation. Source discovery
beyond initial candidates is incomplete due environment access restrictions.
Subject recognition and automatic subject-following crops are optional future
extensions. GitHub publication and TRMNL import require account-level actions;
local development and fixture tests are ready for continued implementation.

## Follow-up: accepted external proof and deployment checks

The user has independently verified the exact OOI recording on a Mac: full
HTTP response headers, successful 1,024-byte range response, and a decoded and
viewed hydrothermal vent frame. That technical evidence is accepted in the
registry. It does not by itself establish runner bandwidth or grant reuse rights.
The `Validate OOI on GitHub runner` workflow tests the deployment network and
extractor directly. Consult its exact run/report for the latest result; Codex's
proxy restriction is not a source availability or release-rights determination.

### Observed GitHub runner pass

The exact-recording validation workflow passed on GitHub-hosted Ubuntu: HTTP
200 headers, HTTP 206 / 1,024-byte range probe, four of four FFmpeg seeks and
800×448 one-bit renders. It fetched 10,255,684 bytes out of 949,254,467
(1.0804%), over 42 requests in 20.072 seconds.
[Full evidence](evidence/ooi-20261027-github-actions.json) includes the run URL
and tested code commit. The Mac proof and runner proof are recorded separately
in the registry; technical status is now `runner_verified`. Public release
remains gated by rights review, not Codex connectivity.

The follow-up local suite passed **25/25 tests** (10.968 seconds), including
infrastructure-versus-origin error classification, technical/rights separation,
and metadata-only validation with actual FFmpeg decoding. The first pushed
commit's 21-test CI run also passed on GitHub-hosted runners. Public Pages
deployment and TRMNL cloud/device rendering have not been executed.

## Adaptive search and cadence follow-up — 28 October 2026 (Berlin)

The expanded suite passed **35/35 tests** (10.257 seconds). New coverage includes
shared transfer limits across recordings, cross-midnight discovery, fine-stage
improvement, older-recording selection, partial recording failures, processed
URL skips, and baseline versus repeated publication observations. Two successive
observer restore/save/summary jobs were also simulated against a temporary Git
remote; history and prior benchmark reports survived metadata-only runs.
The metadata-only CLI imports with Python `-S`, verifying that hourly observations
need no Pillow/NumPy installation.

The [real GitHub study](https://github.com/nikokoren/abyss/actions/runs/40600427507)
passed: 24 archive recordings, 23/23 filename gaps of three hours; 12 coarse + 4
fine frames across three recordings, 44,501,800 bytes in 55.044 seconds, complete
search under a shared 64 MiB budget. It selected the older 18:15 clip instead of
the newest 21:15 clip. Baseline publication-delay samples remain zero; hourly
metadata observation is configured to collect subsequent first appearances.
See [search-and-cadence.md](search-and-cadence.md) and its linked evidence.

## Personal preference gallery and ranker — 28 October 2026

- **50/50 Python tests passed** (10.714 seconds), plus the JavaScript review-core
  tests. Tests exercise preference-driven refinement and final ranking, hard
  image-quality gates, owner/event authorization, trusted-manifest validation,
  duplicate/reversed-pair handling, issue edits, neither/repetitive labels,
  model checksums/fallbacks, changed-model reprocessing, and recording-group
  hold-out evaluation without shared-recording leakage.
- The real CPU encoder produced 518-value features using checksum-verified
  ImageNet-pretrained ResNet18 weights. CPU dependency installation and the
  complete reusable setup were executed successfully.
- Chromium checks passed: A/B/neither/repetition, undo, persistent reload,
  backup export/import, editing, chunked GitHub draft links, responsive layout
  and interaction after networking was disabled. Local-file navigation was
  denied by managed-browser policy; file-URL opening is explicitly unverified
  here. Standalone HTML has all images/scripts embedded and no API-key calls.
- A local temporary-Git simulation exercised gallery persistence → owner issue
  ingestion → ready-model persistence. Its synthetic test choices stayed in
  that temporary repository; they were never written into the user's model.
- [GitHub gallery run 40603578617](https://github.com/nikokoren/abyss/actions/runs/40603578617)
  completed successfully with 16 real OOI candidates, 45,026,088 video bytes,
  59.087-second extraction/encoding search and 62.533-second gallery generation.
  The persisted cloud model correctly has **zero human comparisons**.

[Full preference guide and live evidence](preferences.md). Actual preference
generalization awaits real owner choices and enough independent recordings;
model readiness alone is not a measured quality improvement. Public scientific
recipe distribution remains a separate source-rights/deployment step.
