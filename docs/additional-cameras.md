# Additional camera access and reuse investigation

Investigation started 28 October 2026. The existing Axial HD camera remains
enabled. Additional cameras are held outside the production registry until
actual retrieval, decoding, image quality and rendered previews are reviewed.

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

The next runner check may publish credited grayscale/monochrome preview images
on `camera-research` under this reviewed use. It does not itself add an eligible
camera to `sources.json` or the production dropdown.

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
  Current landing-page discovery and clip-specific ownership checks continue.
- **MBARI:** the current homepage is accessible; the historical MARS URL
  returned 404. A homepage promotional MP4 is not treated as an ocean camera.
  Current observatory, media and legal pages are being examined.

Codex still returns a proxy CONNECT denial for OOI. The deployment runner's
successful archive access is independent evidence and takes precedence for
deployment reachability. Metadata/policy captures are stored on the
`camera-research` branch, with immutable run directories and per-response hashes.
