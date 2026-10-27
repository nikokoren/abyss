# Validation evidence and remaining acceptance gates

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

No hosted run, working ocean dropdown, source licensing clearance, physical
e-paper quality, or zero-cost production operation is claimed. Source discovery
beyond initial candidates is incomplete due environment access restrictions.
Subject recognition and automatic subject-following crops are optional future
extensions. GitHub publication and TRMNL import require account-level actions;
local development and fixture tests are ready for continued implementation.
