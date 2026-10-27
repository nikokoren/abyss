# Architecture and cost model

```
source registry → adapter discovery → HTTPS range bridge → FFprobe / FFmpeg
  → candidate scoring + recent-image similarity → monochrome still
  → immutable PNG + atomic metadata → public catalog → TRMNL selection
                  ↘ durable state / backoff / measured resource use
```

The pipeline runs once per eligible source, shared across subscribers. Recipe
settings select the delivered source rather than starting a per-device video job.
This deliberately trades a small fixed amount of preprocessing for zero user
credentials and simple static delivery. Add only a small shortlist until measured
costs justify expansion. An invalid CLI source selection falls back to the first
eligible source. Missing recipe selection falls back to a retained default image.

Adapters normalize recording URL and optional start timestamp. The OOI adapter
searches up to 14 UTC days, parses only exact CAMHDA filenames on the expected
date, ignores incomplete recent recordings for an hour, and returns up to three newest
candidates for production search. Missing directory entries are tolerated. The direct adapter supports
approved HTTPS MP4 archives without a new extractor. Live HLS, snapshots, APIs
requiring credentials, and other containers need new small adapters; **not** all
registry candidates are implemented adapters.

Remote data goes through inherited proxies and TLS trust. FFmpeg connects only
to a local bridge. Each upstream byte range is verified as 206 with consistent
Content-Range/length/ETag, limited to 256 KiB, cached (32 MiB max), and charged
against a default 64 MiB/source-search budget shared across recordings. HTTP redirects remain within the
source's HTTPS hostname allowlist. A server ignoring ranges is refused before
reading its body. A budget failure preserves the last good still, not a full-file
fallback. OS/TLS buffering and HTTP headers are not included in measured payload
bytes; monitor runner-level transfer too. Multiple concurrent range requests are
serialized upstream. The bridge serves complete requested ranges so FFmpeg does
not confuse a cache block with end-of-file.

FFmpeg seeks before decoding and limits threads/candidate count. Production
search now compares three recent unseen recordings with four coarse samples each,
then four total fine samples around the strongest moments. Each recording has an
eight-frame cap, coarse density defaults to a 60-second minimum interval, each
subprocess times out after 60 seconds, and recordings are limited to 24 hours.
The 64 MiB source-search cap applies to all coarse/fine retrieval together.
The configuration does not promise that every GOP/codec fits the budget; partial
coverage is reported and valid candidates survive other recording failures.
See [search-and-cadence.md](search-and-cadence.md) for the hourly metadata observer.

Quality combines sharpness, contrast, exposure, clipping, regional detail and
composition. A recent 256-bit difference hash penalizes near duplicates, while
base-quality rejection avoids variety at the expense of unusable frames. Dark,
white and flat frames are rejected. Semantic vent/animal detection is not
implemented. Profiles can override acceptance and novelty weights by source.
Ordered 4×4 dithering is a provisional default; threshold, Floyd and grayscale
are configurable. Center-cropping cannot guarantee preservation of off-center
subjects; subject-aware crops remain future work.

Publication is content-addressed PNG first, atomic `latest.json` second, catalog
last. Failed extraction/quality checks do not replace the last-good image.
Recording time, frame offset, capture time, extraction/processing/publication
times remain distinct. A successful job does not imply fresh footage. Non-archive
captures over 48 hours old are marked stale by default. Unknown capture timestamps
remain unknown. Catalog health hides sources from new dropdown exports after
three failures, retaining old images and actual timestamps; exponential retries
(2–48 hours) automatically probe recovery. Successful discovery of an already
processed recording clears transient failure status. Rejected recordings are
remembered too. State retains 256 recording URLs and 24 recent hashes per source.

## GitHub suitability and verified documentation

On 2026-10-27, current files in `github/docs` were retrieved over HTTPS:

- [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions):
  standard hosted runners for public repositories are free; private repositories
  have plan-specific quotas with billable overage. No account plan, repository
  visibility, or remaining allowance was accessible/verified here.
- [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits):
  published site max 1 GB; soft bandwidth 100 GB/month; deployment timeout 10 min;
  custom Actions builds are exempt from the 10-builds/hour soft limit. Rate limits
  still apply and this is not a commercial SaaS hosting guarantee.
- [Pages availability](https://github.com/github/docs/blob/main/data/reusables/gated-features/pages.md):
  free plans support public repositories; private Pages requires an eligible paid
  plan. Public delivery must be independently checked for the chosen account.
- [Scheduled events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule):
  only default-branch schedules run, they can be delayed/dropped, and inactivity
  can disable schedules in public repos after 60 days.

Prototype: standard `ubuntu-24.04` runners, two runs/day (03:23 and 15:23 UTC),
20-minute job ceiling, GitHub Pages custom deployment. No paid API/model/storage
is required. A subsequent technical validation ran on GitHub-hosted Ubuntu and extracted
four real OOI frames within the byte budget; see the saved runner evidence.
No billing dashboard measurement or recurring Pages deployment has happened.
Before enabling recurring runs, confirm the repo's visibility/plan, organization
policies and billing budget; use spending controls appropriate to the account.

## Estimates — not measured live-source usage

For N sources at two runs/day over 30 days:

- Max attempted video payload per twice-daily production source search: N × 60 × 64 MiB = **3.75 GiB/month/source**,
  plus bounded discovery pages and protocol overhead. Identical/rejected known
  recordings are skipped before video transfer. Startup races or failed runs
  may still transfer data again.
- If a measured run takes 8 minutes: 480 runner-minutes/month. The 20-minute
  job ceiling is 1,200 minutes/month for the shared scheduled job, plus CI/manual
  jobs. This is not a private-plan free-tier entitlement.
- A 100 KiB output PNG at 60 new frames/month adds roughly 5.9 MiB/source/month
  of site files; Git history also grows. Immutable images are retained to keep
  cached metadata valid. No automatic pruning or repository-history compaction
  is supplied; monitor growth before the 1 GB Pages limit.
- Delivery bandwidth: devices × polls/day × average response bytes. For example,
  1,000 devices × 6 polls/day × 100 KiB × 30 ≈ **17.2 GiB/month** before catalog
  overhead. Caches may reduce this, but do not rely on undocumented cache TTLs.

`diagnostics` captures elapsed extraction seconds, payload bytes, requests,
recording size, codecs, candidates and seek errors. Workflow duration also
includes runner setup, dependency installation and deployment. A budget failure
backs off; it never purchases capacity or widens limits automatically. Revisit
schedule, candidate count, frame offsets, GOP structure and hosting if real
measurements exceed the envelope. Free-tier production suitability remains a
release gate until representative real runs and account quotas are confirmed.
