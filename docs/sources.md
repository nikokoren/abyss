# Source discovery audit

Audit date: 2026-10-27. This is an evidence ledger, not a claim that all candidate
institutions have been investigated successfully. Original product requirements
are saved in [requirements.md](requirements.md).

## Access evidence

- The supplied OOI MP4 and archive directory were requested via the managed HTTPS
  proxy. Both returned `CONNECT tunnel failed, response 403` before origin access.
  This establishes an **environment policy restriction**, not an OOI outage,
  missing footage, range incompatibility, or a licensing conclusion.
- A draft network allowlist was saved for OOI, NOAA, MBARI, ONC, GitHub docs, and
  TRMNL docs. Saving the draft did not grant current runtime access.
- Public GitHub access worked. The public TRMNL plugin repository and a community
  recipe export were inspected to establish settings shape. This is not an
  end-to-end TRMNL cloud render test.

## Candidate comparison and initial shortlist

| Candidate | Location / subject | Access strategy to investigate | Cadence / latency | Reuse / attribution | Decision |
|---|---|---|---|---|---|
| OOI CAMHDA301, Regional Cabled Array | Axial Seamount, Ashes hydrothermal field; vents and seafloor | UTC directories, timestamped MP4, bounded HTTP range extraction | Unmeasured; timestamps in filenames need confirmation as UTC recording start | Institutional terms and required credit not yet verified | **First technical candidate**; implemented adapter, blocked before origin retrieval; excluded from dropdown |
| Other OOI cameras | Observatory/instrument-dependent | First identify camera instrument IDs and comparable archives | Unknown | Must verify per dataset/instrument | No second camera ID invented; discovery pending |
| Ocean Networks Canada | NE Pacific observatories; deep-seafloor habitat | Oceans 3.0 archive/API, direct media/snapshots if available | Unknown; do not imply live | Authentication, API terms and imagery reuse unverified | Research only; exclude until endpoint and terms confirmed |
| NOAA Ocean Exploration | Expedition-dependent; ROV marine life and geology | Expedition archives, direct recordings/streams | Expedition-dependent, no continuous-feed promise | Check individual clip authorship; NOAA affiliation does not establish rights to every clip | Research only; unsuitable as a continuous default until validated |
| MBARI | Monterey Bay and expeditions; ROV ecosystems | Institutional video catalog or sanctioned media access | Unknown; archives are not live | Permission/reuse terms unverified | Research only; no scraping or redistribution assumed |

Links: [OOI archive](https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/2026/),
[OOI](https://oceanobservatories.org/), [NOAA](https://oceanexplorer.noaa.gov/),
[ONC](https://www.oceannetworks.ca/), [MBARI](https://www.mbari.org/).
These are discovery leads, not citations asserting verified technical properties.

All four registry candidates are excluded from release. None is permanently
rejected as a scientific source. They are rejected from the **initial dropdown**
because there is no completed retrieval/rights validation. No suitable second or
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
