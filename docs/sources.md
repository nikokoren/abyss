# Source discovery audit

**Current production, 29 October 2026:** four OOI cameras are enabled in this
order: ASHES: Mushroom vent, International District: Tiny Towers, Southern
Hydrate Ridge: Einstein's Grotto, and Oregon Offshore: seafloor. Technical access,
full-resolution decoding and attributed derived-still reuse were reviewed on
GitHub runners. Oregon Shelf and both water-column cameras remain on quality
hold. See [camera evidence](additional-cameras.md), [rights review](ooi-rights-review.md)
and [current validation](validation.md).

ONC, NOAA and MBARI remain research leads without enabled production feeds.
Codex network restrictions are separate from upstream availability and rights.
Original requirements are retained in [requirements.md](requirements.md).
The initial audit and dated measurements below preserve their original scope;
early pending-rights/discovery decisions have been superseded for the four
published OOI cameras.

## Initial Codex access evidence — 27 October 2026

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

## Initial shortlist — historical

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

At the initial audit, no scientific source was eligible for release. The later
OOI rights review and four-camera deployment supersede that decision. Other
institutions still need independent technical and reuse validation.

## Required real-source measurements

Run `inspect` on several recordings from different days, including camera pans
and dark/low-activity views. Record origin HTTP status, byte-range behavior,
Content-Range, total recording size, codec, duration, resolution, candidate count,
bytes fetched, elapsed time and failed seeks from `inspection.json`. Compare a
budgeted run to file size; a range header alone does not establish efficiency.
Confirm whether MP4 metadata is at the head or tail and test both cases.
Measure recording/publication cadence by observing at least two directory updates.
Do not derive publication delay solely from a recording filename. Confirm the
filename timezone with source documentation. Production ASHES timestamps are explicitly marked as assumed UTC; still-camera
filenames declare UTC. Do not describe the ASHES interpretation as confirmed.

Read institutional terms and follow linked dataset licenses. Record the exact
rights text/link, review date, allowed derived-still use and required attribution.
A manual `terms_reviewed_at` is a record of a real review, not a toggle to bypass it.
If rights remain ambiguous, obtain permission or keep the source disabled.

Production preserves full-resolution colour and lets TRMNL scale and dither it.
Alternative rendering modes are inspection tools. Use the recorded runner
measurements for bandwidth and search coverage; physical-device readability
still needs confirmation.

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
not an inference from either the Mac or Codex. OOI's release status was `pending_rights_review` at this technical checkpoint;
the subsequent attributed-still rights review approved production use.

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

No imagery was uploaded or published by that validation workflow. Rights/attribution, filename timezone,
recurring directory discovery and cadence remain separate checks. Codex's
continued CONNECT denial does not override this deployment-environment success.

## Cadence and multi-recording follow-up

The [28 October runner study](search-and-cadence.md#first-observed-runner-result--28-october-2026-berlin)
observed 24 files across three UTC dates with uniformly three-hour filename
spacing. The shared adaptive search successfully compared three recent clips
and refined promising moments within 44.5 MB / 55 seconds. Publication delay
remains unmeasured from this baseline; hourly first-appearance collection is
independent of rights approval and of public image refresh frequency.
