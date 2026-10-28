# Additional camera access and reuse investigation

**Offshore wildlife follow-up:** a [seven-day, unranked sample](offshore-wildlife.md)
found clear fish in 12/42 frames, another nine uncertain fish-like forms, and
small seabed animals in all 42. This is stronger evidence for Offshore's visual
interest than its earlier quality-only selected frame. It remains technically
accessible and rights-reviewed; the observational study does not enable it.

**Fresh native-preview recheck:** six hourly snapshots each from Oregon Shelf
and Offshore still do not support adding them to the general rotation. Both
remain accessible and rights-reviewed. See the [new review and previews](oregon-native-review.md);
the earlier ordered-dither results below are historical evidence.

Updated 28 October 2026. **Southern Hydrate Ridge and International District
are enabled**, joining the existing Axial HD camera. All six new archives are
reachable and decode successfully on GitHub runners. Four cameras remain on
image-quality hold: the two water-column cameras failed the raw-image quality
gate, while both shelf-camera monochrome previews are dominated by glare.

## OOI still cameras: rights review

The [official Digital Still Camera description](https://interactiveoceans.washington.edu/instruments/digital-still-camera/)
identifies these cabled cameras as OOI-RCA instruments. It specifically names
the Oregon Shelf and Offshore seafloor sites, Southern Hydrate Ridge,
International District/Tiny Towers, and the shallow-profiler water-column
platforms at Oregon Slope Base and Axial Base. The camera systems are SubC
Rayfins with lights and pan/tilt hardware. These are distinct cameras and
habitats, rather than renamed views of the existing HD camera.

[GitHub runner investigation 40664258062](https://github.com/nikokoren/abyss/actions/runs/40664258062)
retrieved that instrument page, all six instrument archives, and date directories
for 27 and 28 October 2026. All six archives returned HTTP 200 and listed fresh
JPEG files. Filenames explicitly include `_UTC`; timestamps do not rely on the
HD camera's still-unconfirmed timezone assumption. Listings show approximately
half-hour bursts of three images. Publication appearance delay is not measured.

The core-instrument deployment records are taken from the
[official asset-management inventory](https://github.com/ooi-integration/asset-management/tree/c294b195630a9df5f1b90dac9e8ab1ef6f8effb1/deployment).
Exact records, instrument identifiers, depths and archive paths are retained in
[camera-research-targets.json](camera-research-targets.json). For the profiler
cameras, the displayed depth is the camera/platform depth, not the seabed depth.
Preliminary deployment depths are marked approximate.

| Camera | Location | Reported camera depth | Initial archive result |
| --- | --- | --- | --- |
| CAMDSB107 | Oregon Shelf seafloor | 81 m, preliminary | Fresh JPEGs, HTTP 200 |
| CAMDSB106 | Oregon Offshore seafloor | 582 m, preliminary | Fresh JPEGs, HTTP 200 |
| CAMDSB103 | Southern Hydrate Ridge, Einstein's Grotto methane seep | 775 m, preliminary | Fresh JPEGs, HTTP 200 |
| CAMDSB303 | Axial Seamount, International District/Tiny Towers | 1,521 m, preliminary | Fresh JPEGs, HTTP 200 |
| CAMDSC102 | Oregon Slope Base shallow-profiler platform | 191 m | Fresh JPEGs, HTTP 200 |
| CAMDSC302 | Axial Base shallow-profiler platform | 190 m | Fresh JPEGs, HTTP 200 |

The [OOI data terms and acknowledgment review](ooi-rights-review.md) is extended
to derived images from these six identified OOI instruments. The linked OOI
terms define data to include connected instruments and derived visualizations,
and permit direct/indirect redistribution with attribution. No separate license
or exclusion was identified on the official still-camera description. This
review covers these instrument-data JPEGs; unrelated website, expedition and
third-party photographs remain outside its scope.

Approved use: freely accessible derived previews and production stills with
intact original notices, a compact OOI/WHOI OOI Program Office/UW/NSF image
credit, full acknowledgment and terms on the product/settings pages, and no
endorsement claim. The [original terms evidence](https://github.com/nikokoren/abyss/tree/b24fb04ec4c9e1ad4d5fc89e16bb390494156bfb/terms/ooi-axial/40651933247)
is preserved separately from new technical evidence. No Creative Commons or
public-domain status is asserted for OOI imagery.

## Observed frame validation and release decision

[Runner validation 40689383752](https://github.com/nikokoren/abyss/actions/runs/40689383752)
decoded two images from each of the six cameras, with complete searches and no
failed retrievals. The [immutable evidence and credited previews](https://github.com/nikokoren/abyss/tree/cbe9af8e9a84431c21e06612c3c34e30a140a59d/research/40689383752)
and [local metadata copy](evidence/ooi-still-cameras-20261028.json) retain the
exact URLs, capture times, decoded sizes, quality metrics and byte counts.
Grayscale previews from all six cameras and 1-bit previews from the four that
passed the automated score were visually reviewed.

| Camera | Best automated score | Two-image payload | Decision |
| --- | --- | --- | --- |
| Southern Hydrate Ridge | .851 | 17,251,842 bytes | **Enabled**; readable rocky methane-seep habitat |
| International District | .842 | 39,736,917 bytes | **Enabled**; readable vent habitat |
| Oregon Shelf | .582 | 39,053,260 bytes | Hold: 1-bit preview dominated by glare despite passing the automated score |
| Oregon Offshore | .612 | 18,941,747 bytes | Hold: 1-bit preview dominated by glare despite passing the automated score |
| Oregon Slope Base water column | .085 | 45,283,165 bytes | Hold: below .30 gate; noise/backscatter |
| Axial Base water column | .055 | 40,722,570 bytes | Hold: below .30 gate; noise/backscatter |

The cameras deliver **5344 × 4008 (21.4 MP)** JPEGs of roughly 8–23 MB each.
A 65,537-byte range probe per camera established size/dimensions before changing
retrieval limits. Production now compares two recent snapshots, capped at
24 MiB per image, 48 MiB per camera search and 24 million source pixels. JPEG
native decoder scaling produces 1336 × 1002 input for ranking/rendering while
preserving the entire frame. Unknown streams, oversized images, unsupported
formats, incomplete responses and animated images are rejected. Hard ceilings
remain in the reader even if a source profile requests more.

The two enabled cameras used 56,988,759 payload bytes together in the validation
run. Range-header probes and directory/policy metadata are separate from that
figure. Current production runs every three hours, so an upstream half-hour camera
cadence does not mean the TRMNL image updates every half hour. The existing
personal ranking model is used by production when available, but this technical
trial used quality ranking alone and does not prove preference generalization.

The source registry records the reviewed terms, deployment/DOI links, exact
runner evidence and per-camera visual-review decisions. `quality_hold` means
accessible but currently unsuitable for this display; it does not report a
camera outage or Codex network failure. The staging `camera-candidates.json`
remains a reproducible validation input; `sources.json` records release status.

The same discovery, personal ranking, quality gate, publication, native layouts,
credits and last-good behavior serve both video and still cameras. Source-registry
changes trigger deployment and regenerate the recipe's static source options.
Existing installations need the updated settings/options to select new cameras;
existing markup already supports their location/depth metadata.

## Other institutions

- **Ocean Networks Canada:** official data-policy page is accessible. Solely
  ONC-owned data use CC BY 4.0; partner data may use CC BY-NC or stricter terms.
  Website multimedia have a separate policy. An unauthenticated camera-device
  API request returned **401** on the GitHub runner. No token was requested,
  invented or borrowed, and no institution-wide license was assumed to cover
  every camera.
- **NOAA Ocean Exploration:** the initial historical stream page returned 404,
  and an alternative hostname did not resolve on the runner. These are exact
  endpoint results, not evidence that NOAA footage in general is unavailable.
  The current homepage, multimedia library and data-access page returned 200.
  The data-access page specifically identifies the
  [NCEI Ocean Exploration Video Portal](https://www.ncei.noaa.gov/access/ocean-exploration/video/)
  and states that all video on that portal is public domain. This is a promising
  archive source; exact media retrieval and recurring ingestion are still
  unvalidated. It does not grant rights to unrelated third-party website images.
- **MBARI:** the current homepage is accessible; the historical MARS URL
  returned 404. A homepage promotional MP4 is not treated as an ocean camera.
  Current observatory, media and legal pages returned 200. The legal page
  licenses non-commercial classroom education and expressly restricts personal
  use/non-classroom copying without written permission. This ambient display
  is not covered by that classroom license. No permission request was sent.

Codex still returns a proxy CONNECT denial for OOI. The deployment runner's
successful archive access is independent evidence and takes precedence for
deployment reachability. Metadata/policy captures are stored on the
`camera-research` branch, with immutable run directories and per-response hashes.
