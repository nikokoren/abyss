# Requirements: Ambient Ocean Camera for TRMNL

> Original product brief. Implementation decisions subsequently changed delivery
> to full-resolution colour with native TRMNL dithering, a 15-minute camera
> rotation and three-hour processing. Use [validation.md](validation.md) for
> current status and [architecture.md](architecture.md) for operating limits.
> This brief is retained as the original requirements record.

## 1. Overview

Build a TRMNL recipe that displays compelling still images extracted from underwater research camera footage. The initial source is the Ocean Observatories Initiative (OOI) hydrothermal vent camera at Axial Seamount, but the solution must support multiple camera feeds and data sources.

The recipe should turn scientific video footage into an attractive, low-resolution, monochrome image suitable for an e-paper display. It should run entirely in the cloud, without requiring the user's computer to be online or perform any processing.

A core product requirement is **discovering and supporting multiple camera sources**, then allowing users to select their preferred source during recipe setup through a dropdown.

## 2. Goals

- Create an ambient, science-oriented TRMNL display featuring real underwater research footage.
- Automatically select visually compelling frames rather than displaying arbitrary or uninteresting frames.
- Process images specifically for monochrome e-paper displays.
- Run all recurring processing in the cloud, ideally within free service tiers.
- Discover additional compatible underwater camera feeds and make them selectable by users.
- Provide accurate source attribution and recording timestamps.
- Build a reusable pipeline that can accommodate additional camera sources without redesigning the system.

## 3. Initial Data Source

### Ocean Observatories Initiative: Axial Seamount

Initial candidate source:

`https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/2026/`

Example recording:

`https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/2026/10/27/CAMHDA301-20261027T181500.mp4`

Known characteristics:

- Underwater research footage from the Axial Seamount region.
- Includes hydrothermal vent activity, mineral deposits, seafloor terrain and changing camera views.
- Recordings are approximately 950 MB in MP4 format.
- Files appear in timestamped intervals.
- The server supports HTTP byte-range requests, allowing partial downloads.
- The camera pans, so points of interest may move through the frame.

The source must be validated for continued availability, recording cadence, licensing or reuse restrictions, attribution requirements, and whether remote frame extraction works reliably.

The source is a starting point, not a hard-coded assumption about the final product.

## 4. Research and Source Discovery

Before finalizing the architecture, investigate additional publicly accessible underwater camera feeds and related scientific video sources.

### Sources to investigate

Potential discovery targets include:

- Other Ocean Observatories Initiative cameras and observatories.
- NOAA underwater observatories, research cameras and remotely operated vehicle footage.
- MBARI underwater observatory and seafloor camera feeds.
- Ocean Networks Canada observatories.
- Other university, government or research-institution camera archives.
- Public live streams, scheduled recordings and regularly updated video archives.

These are candidates to investigate, not confirmed compatible sources.

### Evaluate each candidate

For every potential source, establish:

- Name and scientific location.
- Organization operating the camera.
- Subject matter, such as hydrothermal vents, deep-sea ecosystems, coral reefs, seafloor habitats or marine life.
- Whether footage is live, periodically recorded or an archive.
- Update frequency and typical delay between recording and publication.
- Availability of direct video files, streams, snapshots or APIs.
- Whether frames can be extracted efficiently without downloading entire recordings.
- Reliability, uptime and accessibility without authentication.
- Licensing, reuse rights and attribution requirements.
- Technical requirements, including codecs, resolution, timestamps and access restrictions.
- Suitability for monochrome e-paper.
- Whether the camera moves, and whether useful points of interest appear frequently enough to produce good images.
- Expected bandwidth, compute requirements and operational costs.

### Source registry

Create a structured source registry rather than scattering source-specific URLs throughout the code.

Each source definition should include, where applicable:

- Stable source ID.
- Display name.
- Short description.
- Institution or operator.
- Location.
- Subject category.
- Source type: live stream, periodic recording, archive or snapshot.
- Source discovery method.
- Retrieval adapter or processing strategy.
- Update cadence and expected delay.
- Attribution text and link.
- Licensing or reuse notes.
- Availability status and last successful retrieval.
- Known limitations.

Only expose sources in the user-facing dropdown once they have been tested and confirmed compatible. Do not present an archive as live footage or imply that a source updates more frequently than it does.

The system should be designed so that new sources can be added through configuration and, when necessary, a small source-specific adapter.

## 5. User Setup and Source Selection

Add a user-selectable source dropdown to the TRMNL recipe setup process.

### Requirements

- Display available, validated camera sources in a dropdown.
- Use readable source names rather than raw URLs.
- Provide a short description for each option, including the location and what the camera shows.
- Identify whether a source is live, periodically updated or archival.
- Include the Axial Seamount camera as the initial option, subject to successful validation.
- Persist the user's selection using TRMNL recipe/plugin settings.
- Use the selected source to determine which footage is processed.
- Make adding a source possible without changing the general frame-processing pipeline.
- Handle missing, invalid or unavailable selections gracefully.
- Provide a sensible default source.
- Ensure source selection works within TRMNL's supported plugin settings and recipe architecture.

If TRMNL setup settings support dependent fields, additional options may be shown based on the selected source. Keep the initial setup simple and avoid unnecessary configuration.

Do not ask users to supply their own API keys or URLs unless a source genuinely requires them.

## 6. Cloud Processing and Hosting

All video retrieval, frame extraction, selection, processing and publication must happen in the cloud.

The user's Mac or other personal device must not be required to run scripts, stay online or download video files.

### Preferred starting architecture

Evaluate GitHub Actions and other suitable free-tier cloud services.

GitHub Actions is the preferred first prototype because it can run scheduled workflows and execute FFmpeg and Python-based processing. Confirm current free-tier limits and applicable repository restrictions before committing to it as the production solution.

Potential responsibilities:

1. Check which recordings are available for the selected source.
2. Identify new or unprocessed footage.
3. Retrieve only the data required to extract candidate frames where technically feasible.
4. Extract and score frames.
5. Process the selected frame for e-paper.
6. Publish the resulting image and metadata to a stable, publicly accessible endpoint.
7. Make the latest processed image available to the TRMNL recipe.

Investigate a suitable hosting option for the output image, such as GitHub Pages, an object store or another free-tier service. Confirm that the chosen service supports the necessary public access, update frequency, caching behavior and storage requirements.

Separate processing from image delivery so that the recipe does not need to download or decode large video files itself.

### Cost and resource constraints

- Prefer free services and free tiers.
- Avoid downloading the same large recording repeatedly.
- Avoid processing recordings that have already been handled.
- Use HTTP range requests when supported and effective.
- Avoid running unnecessarily frequent jobs.
- Track bandwidth, storage, execution time and service quotas.
- Design graceful degradation for rate limits, failed downloads and exhausted quotas.
- Document any limits that could cause future costs or require a paid plan.

Do not assume that an entire 950 MB recording can be downloaded and processed frequently at zero cost. Measure the actual requirements before selecting a recurring schedule.

## 7. Frame Extraction and Selection

The camera pans, so frame selection must account for changing composition and subject position.

A frame should not be selected solely because it is the most recent or sharpest.

### Candidate extraction

- Sample frames at configurable intervals.
- Support different recording lengths and source update cadences.
- Avoid repeatedly extracting nearly identical frames where possible.
- Handle source-specific seeking and codec limitations.
- Allow a configurable maximum number of candidate frames per recording.

Begin with a simple, measurable baseline rather than requiring an expensive AI model.

### Initial quality scoring

Evaluate candidate frames using criteria such as:

- Sharpness and motion blur.
- Brightness and exposure.
- Contrast and tonal range.
- Clipped highlights and crushed shadows.
- Visual complexity and composition.
- Similarity to recently published images.
- Presence of meaningful subject matter where practical.

The scoring system should favour frames that are both technically usable and visually interesting.

### Subject-aware selection

Investigate whether lightweight computer vision or an optional hosted vision model can identify interesting underwater scenes, including:

- Hydrothermal vent chimneys.
- Visible vent plumes.
- Tube worms and other marine life.
- Distinctive seafloor structures.
- Other source-specific points of interest.

Subject detection should be an enhancement, not a requirement for the first working version. Generic quality scoring must work even when subject detection is unavailable.

Do not assume the same visual criteria will be appropriate for every camera. Make scoring extensible by source or subject category.

### Avoiding repetitive output

- Compare candidate images with the currently published image and recent history.
- Penalize near-duplicates when other good candidates are available.
- Avoid selecting an inferior frame merely to create variety.
- Keep the last known good image when a new recording contains no acceptable candidates.

## 8. E-Paper Image Processing

Produce an image that looks intentional on a monochrome TRMNL display.

### Processing requirements

- Resize or crop to the configured target display dimensions and aspect ratio.
- Convert to grayscale or monochrome as appropriate.
- Tune contrast and brightness.
- Evaluate thresholding and dithering techniques.
- Preserve important structures, including dark chimneys, light mineral deposits and visible plumes.
- Avoid losing detail in highlights and shadows.
- Avoid excessive noise and dithering artifacts.
- Support the actual dimensions and capabilities of the target TRMNL device.
- Make processing parameters configurable and easy to compare.

Create a small test set containing representative scenes and compare several processing methods before choosing defaults.

The goal is legibility and visual quality on e-paper, not photographic fidelity on a normal monitor.

## 9. Metadata and Source Attribution

Each published image should have associated metadata:

- Source ID and display name.
- Recording timestamp, when available.
- Frame timestamp within the recording.
- Time the frame was extracted.
- Time the image was processed.
- Time the image was published.
- Link to the original source.
- Attribution and licensing information where required.
- Optional quality score and selection reason for diagnostics.

Distinguish the recording time from the publication time. Do not imply that a frame is live merely because it is the latest available recording.

If the recipe displays a timestamp, it should make the age of the footage understandable to the user.

## 10. Reliability and Failure Handling

The system must remain useful when sources or processing jobs fail.

- Detect unavailable or incomplete recordings.
- Detect failed downloads and invalid video files.
- Handle missing timestamps and unexpected codecs.
- Avoid publishing corrupted or empty images.
- Retain the last known good image when a new run fails.
- Track when the source was last checked and when a new image was last published.
- Expose basic logs and error details for debugging.
- Avoid repeatedly retrying a permanently broken source.
- Mark unavailable sources in the source registry and remove or disable them in the dropdown when appropriate.
- Recover automatically when a temporarily unavailable source returns.

If the last good image is stale, preserve its actual capture timestamp. Never silently present stale footage as fresh.

## 11. Security and Compliance

- Use public sources without credentials wherever possible.
- Do not bypass authentication, access controls or technical restrictions.
- Respect source terms, copyright, licensing and attribution.
- Avoid publishing any private credentials in workflow logs or repository files.
- Keep public image hosting separate from internal processing configuration.
- Do not redistribute complete source recordings unless their licensing permits it.
- Prefer publishing only the derived still image and necessary metadata.

## 12. Suggested Implementation Phases

### Phase 1: Research and feasibility

- Audit additional underwater camera sources.
- Validate source access and reuse requirements.
- Confirm the Axial Seamount recording can be processed remotely and reliably.
- Measure seeking efficiency, bandwidth and processing time.
- Select the initial hosting and scheduling architecture.
- Produce a source comparison table and recommended initial shortlist.

**Deliverable:** source research report and technical feasibility recommendation.

### Phase 2: Single-source proof of concept

- Implement remote retrieval for the Axial Seamount source.
- Extract a configurable sample of candidate frames.
- Implement basic quality scoring.
- Generate several e-paper processing variants.
- Publish a single selected image and metadata.
- Test the workflow without running anything on the user's Mac.

**Deliverable:** automated cloud workflow producing a usable image.

### Phase 3: Multi-source architecture

- Define the source registry and adapter interface.
- Add at least two additional validated sources if suitable sources are available.
- Implement source-specific retrieval logic where required.
- Normalize timestamps and metadata.
- Confirm that the shared frame-selection and image-processing pipeline works across sources.

**Deliverable:** reusable multi-source processing system.

### Phase 4: TRMNL recipe integration

- Add the source-selection dropdown to recipe setup.
- Persist and apply the selected source.
- Connect the recipe to the published image endpoint.
- Display the appropriate image and timestamp.
- Test source changes, default settings and failure behavior.

**Deliverable:** usable TRMNL recipe with source selection.

### Phase 5: Quality and operational hardening

- Test multiple recordings and different camera compositions.
- Tune image processing for e-paper.
- Improve duplicate detection and subject-aware selection if worthwhile.
- Validate free-tier limits and actual operating costs.
- Add monitoring, retry behavior and documentation.

**Deliverable:** reliable automated recipe suitable for public release.

## 13. Acceptance Criteria

The project is complete when:

1. A cloud workflow processes footage without requiring the user's computer to run.
2. At least one validated source produces a good-quality e-paper image automatically.
3. The workflow avoids downloading entire recordings repeatedly when efficient partial retrieval is possible.
4. Candidate frames are evaluated for quality rather than selected arbitrarily.
5. The image pipeline supports camera movement and changing subject composition.
6. The recipe includes a dropdown of validated camera sources.
7. Selecting a different source changes the footage processed and displayed.
8. Additional sources can be added without rewriting the shared processing pipeline.
9. The published image includes accurate timestamps and source attribution.
10. Processing failures preserve the last known good image.
11. The system clearly distinguishes live feeds, periodically updated footage and archives.
12. The implementation has been tested against actual free-tier quotas and does not silently depend on paid services.
13. Licensing and reuse requirements are documented for every source offered to users.

## 14. Agent Deliverables

Provide the following at the end of the work:

- Source discovery report, including rejected candidates and reasons.
- Recommended architecture with cost and quota assumptions.
- Source registry and adapter design.
- Working cloud processing workflow.
- Frame-selection and e-paper processing implementation.
- TRMNL recipe setup integration with source dropdown.
- Documentation for adding and validating new sources.
- Instructions for deployment, configuration and troubleshooting.
- Known limitations, particularly source availability, freshness, image quality and free-tier constraints.

## Guiding Principle

Build a reusable **underwater camera discovery and image-selection platform**, not a one-off script for one video URL. The recipe should make scientific footage accessible as an attractive ambient display, while being honest about where the footage comes from, how old it is and what the system can reliably deliver.