# Source discovery audit

**Current status, 28 October 2026:** OOI CAMHDA301 passed the
[reuse/attribution review](ooi-rights-review.md) using official documents
retrieved on GitHub runners. It is eligible for attributed derived-still
publication. Other candidates remain research-only. The initial audit and
follow-up measurements below preserve their historical conclusions.

Audit date: 2026-10-27. **Update:** OOI access, byte ranges and a visible
vent frame are user-verified on a Mac. GitHub-hosted retrieval and four FFmpeg
seeks also passed; the remaining release review is separate
from Codex network reachability. See [runner validation](runner-validation.md).

The initial audit below records what was observable in Codex before that evidence
was supplied. This is an evidence ledger, not a claim that all candidate
institutions have been investigated successfully. Original product requirements
are saved in [requirements.md](requirements.md).

## Access evidence

- The supplied OOI MP4 and archive directory were requested via the managed HTTPS
  proxy. Both returned `CONNECT tunnel failed, response 403` before origin access.
  This establishes an **environment policy restriction**, not an OOI outage,
  missing footage, range incompatibility, or a licensing conclusion. This remains
  true even after accepting the user's successful Mac checks.
- A draft network allowlist was saved for OOI, NOAA, MBARI, ONC, GitHub docs, and
  TRMNL docs. Saving the draft did not grant current runtime access.
- Public GitHub access worked. The public TRMNL plugin repository and a community
  recipe export were inspected to establish settings shape. This is not an
  end-to-end TRMNL cloud render test.

## Candidate comparison and initial shortlist

| Candidate | Location / subject | Access strategy to investigate | Cadence / latency | Reuse / attribution | Decision |
|---|---|---|---|---|---|
| OOI CAMHDA301, Regional Cabled Array | Axial Seamount, Ashes hydrothermal field; vents and seafloor | UTC directories, timestamped MP4, bounded HTTP range extraction | Observed three-hour filename gaps (23/23 across 24 files); publication delay and timezone interpretation remain separate checks | Institutional terms and required credit not yet verified | **Runner verified**; four seeks in 20.1 s / 10.26 MB; public release pending rights review |
| Other OOI cameras | Observatory/instrument-dependent | First identify camera instrument IDs and comparable archives | Unknown | Must verify per dataset/instrument | No second camera ID invented; discovery pending |
| Ocean Networks Canada | NE Pacific observatories; deep-seafloor habitat | Oceans 3.0 archive/API, direct media/snapshots if available | Unknown; do not imply live | Authentication, API terms and imagery reuse unverified | Research only; exclude until endpoint and terms confirmed |
| NOAA Ocean Exploration | Expedition-dependent; ROV marine life and geology | Expedition archives, direct recordings/streams | Expedition-dependent, no continuous-feed promise | Check individual clip authorship; NOAA affiliation does not establish rights to every clip | Research only; unsuitable as a continuous default until validated |
| MBARI | Monterey Bay and expeditions; ROV ecosystems | Institutional video catalog or sanctioned media access | Unknown; archives are not live | Permission/reuse terms unverified | Research only; no scraping or redistribution assumed |

Links: [OOI archive](https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/2026/),
[OOI](https://oceanobservatories.org/), [NOAA](https://oceanexplorer.noaa.gov/),
[ONC](https://www.oceannetworks.ca/), [MBARI](https://www.mbari.org/).
These are discovery leads, not citations asserting verified technical properties.

At the initial audit, all four registry candidates were excluded from public recipe release pending rights/retrieval requirements specific to each source. None is permanently
rejected as a scientific source. They are rejected from the **initial dropdown**
because rights review remains incomplete for OOI, and the other candidates lack both technical and rights validation. No suitable second or
third source has yet been established; the two-source behavior is fixture-tested.

## Required real-source measurements

Run `inspect` on several recordings from different days, including camera pans
and dark/low-activity views. Record origin HTTP status, byte-range behavior,
Content-Range, total recording size, codec, duration, resolution, candidate count,
bytes fetched, elapsed time and failed seeks from `inspection.json`. Compare a
budgeted run to file size; a range header alone does not establish efficiency.
Confirm whether MP4 metadata is at the head or tail and test both cases.
Measure recording/publication cadence by observing at least two directory updates.
Do not derive publication delay solely from a recording filename. Confirm the
filename timezone with source documentation. The adapter currently assumes UTC
and leaves discovery behind a validation gate until that is confirmed.

Read institutional terms and follow linked dataset licenses. Record the exact
rights text/link, review date, allowed derived-still use and required attribution.
A manual `terms_reviewed_at` is a record of a real review, not a toggle to bypass it.
If rights remain ambiguous, obtain permission or keep the source disabled.

Compare ordered, Floyd, threshold and grayscale on actual scenes and a physical
device before treating the rendering defaults as tuned. Actual ocean image
quality, bandwidth and pan coverage remain unknown.

## User-provided verification (accepted, separate provenance)

For `CAMHDA301-20261027T181500.mp4`, the user reported HTTP 200,
`Content-Type: video/mp4`, `Content-Length: 949254467`, and `Accept-Ranges: bytes`.
A GET for bytes 0–1023 returned HTTP 206 and exactly 1,024 bytes. FFmpeg
successfully decoded a frame that the user viewed and identified as a
hydrothermal vent. This is evidence of source usability, recorded as
`technical_status: user_verified` with Mac provenance preserved in the registry. This evidence remains
distinct from the subsequent agent-observed GitHub runner report.

A later Codex retry still returned proxy CONNECT 403 before origin access.
GitHub-hosted validation runs independently of that restriction. Its metadata
report on the `source-validation` branch is authoritative for that runner/run,
not an inference from either the Mac or Codex. OOI's release status is
`pending_rights_review`, rather than blocked solely by Codex infrastructure.

## GitHub-hosted result (observed)

[Run 40597267233](https://github.com/nikokoren/abyss/actions/runs/40597267233)
produced a technical **pass** for the supplied recording, on tested commit
`3de9e4b44bda650ac0cde9e94313a0fdb66475c1`. The immutable evidence commit
is `3f989f17256ce8a4c33ac0450b57beae2b1c8902` on `source-validation`.
A copy is retained at [evidence/ooi-20261027-github-actions.json](evidence/ooi-20261027-github-actions.json).

HEAD: 200, video/mp4, 949,254,467 bytes, Accept-Ranges bytes. The exact
0–1023 probe returned 206 / 1,024 bytes. H.264 duration was 893.359 seconds.
All four frame seeks decoded at 960×540 and rendered at 800×448 one-bit.
Payload transfer was 10,255,684 bytes in 42 requests (1.0804% of the recording);
measured validation time was 20.072 seconds, excluding runner setup.
The first low-detail frame scored zero; the others scored .887889, .897527
and .938558. No semantic subject claim is inferred from those quality scores.

No imagery was uploaded or published. Rights/attribution, filename timezone,
recurring directory discovery and cadence remain separate checks. Codex's
continued CONNECT denial does not override this deployment-environment success.

## Cadence and multi-recording follow-up

The [28 October runner study](search-and-cadence.md#first-observed-runner-result--28-october-2026-berlin)
observed 24 files across three UTC dates with uniformly three-hour filename
spacing. The shared adaptive search successfully compared three recent clips
and refined promising moments within 44.5 MB / 55 seconds. Publication delay
remains unmeasured from this baseline; hourly first-appearance collection is
independent of rights approval and of public image refresh frequency.
