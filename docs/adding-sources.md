# Add and validate a source

1. Add a stable lowercase slug and a `research_only` or `pending_validation`
   record to `sources.json`. Include operator, location, category, source type,
   cadence/delay (or explicitly unknown), attribution/rights links, limitations
   and validation status. Never invent a direct endpoint from a landing page.
2. Implement a small discovery adapter in `abyss/adapters.py`, returning
   `{'url': 'https://…/recording.mp4', 'recorded_at': 'timezone-qualified ISO8601'}`.
   `recorded_at` may be null. The existing `direct` adapter accepts `video_url`
   and `recorded_at`; OOI's date-directory adapter accepts `base_url` and optional
   `lookback_days`. Existing OOI still cameras use `ooi_image_directory`,
   `camera_code`, bounded image retrieval and explicit UTC filenames; reuse that
   adapter for a compatible archive. Always register approved HTTPS hosts in
   `allowed_hosts`.
3. For a new adapter, add its name to `registry.eligible` after tests establish
   timestamp normalization and compatibility. Do not add a new source-specific
   path to the general frame-selection/rendering code.
4. Run `python -m abyss.cli inspect --source ID --output output/inspection-ID`
   against real recordings. Keep the generated report as local evidence; record
   its measured summary and immutable evidence reference in `validation.evidence`.
   Test several days and at least two updates, range budgets, dark/blurred footage,
   timestamps, media stability, codecs, and origin failures. Measure freshness
   separately from ingestion time. Inspect authentic frames and render variants.
5. Review reuse rights for publishing derived stills and required credit links.
   Set accurate `license`, `license_url`, `attribution`, `attribution_url`,
   `validation.terms_reviewed_at`, and the technical `validation.retrieval_at`.
   Use real ISO8601 dates and evidence, never fixture results. If access or rights
   need credentials/permission, leave disabled until authorized configuration is
   actually usable. Do not ask recipe users for arbitrary keys or URLs.
6. Set `status: validated` only after both reviews pass. Optional `scoring` has
   `min_score` (default .30), `novelty_weight` (default .12); optional
   `stale_after_hours` defaults to 48 for periodically updated sources. Run the
   live pipeline and review a generated still, metadata and diagnostics.
7. Regenerate the recipe settings from the actual published catalog and re-import
   them in TRMNL. Only validated sources with a published good image appear.
   Runtime failures retain that option, its rotation slot and the last good
   image. Test selection
   on a real device. Add public camera geography to `abyss/about.py`; its camera
   list supplies the names and order for About, dropdown options and rotation.

Static registry status describes curation, not runtime health. Dynamic
`last_successful_retrieval`, failures, cooldown, last checked/published timestamps
live in per-source state and the public catalog/health summary. This prevents
scheduled jobs from rewriting source code just to record health. Preserve the
output branch across runs. To suspend a source, change registry status and
regenerate setup; already installed recipes keep their old setting and receive
fallback/last-good behavior until updated.
