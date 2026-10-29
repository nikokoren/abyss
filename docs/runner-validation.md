# Validate on the deployment runner

This workflow is a bounded technical diagnostic. Current four-camera production,
rights approval and Pages readiness are recorded in [validation.md](validation.md).
Its 800 × 448 inspection output below is not the production delivery format;
production retains source-resolution RGB images and delegates dithering to TRMNL.

Source accessibility, compute compatibility, and redistribution rights are
independent checks. Codex's allowlist is not the GitHub-hosted runner's network
policy. A Codex CONNECT 403 cannot invalidate an OOI success observed elsewhere.
The user's successful Mac results are recorded in `sources.json` with provenance.

The workflow **Validate OOI on GitHub runner** runs on a standard GitHub-hosted
`ubuntu-24.04` machine when its implementation is pushed to `main`, or manually
via Actions → Run workflow. It is independent of Pages configuration, recipe
eligibility and licensing approval. It needs no personal API keys and never
publishes or uploads images or the complete recording.

It tests the exact user-verified URL by default. A manual run may specify another
OOI recording; HTTPS hostname restrictions remain enforced. It checks:

1. Origin response headers (HEAD may be unsupported without invalidating ranges).
2. A real GET for bytes 0–1023, requiring HTTP 206 and exactly 1,024 bytes.
3. Container probing and four uniform FFmpeg frame seeks through the pipeline's
   actual metered range bridge, within a 64 MiB payload cap.
4. Decoded dimensions, quality metrics, and 800×448 one-bit e-paper generation.
5. Total video payload, upstream request count, elapsed time, and transfer ratio.

Candidate images exist only in a temporary directory and are deleted. Only the
JSON technical report is retained: Actions summary, 30-day report artifact, and
`source-validation` branch at `validation/ooi-axial/latest.json` (plus immutable
run-ID/attempt reports). Runner/setup, origin, network-path, budget and processing
failures are not conflated. A proxy tunnel failure says nothing about origin
availability. Source review is not automatically changed by a failed local check.

Read the result without GitHub API access:

```sh
git fetch origin refs/heads/source-validation:refs/remotes/origin/source-validation
git show origin/source-validation:validation/ooi-axial/latest.json
```

Verify `environment: github_actions`, `commit`, `run_url`, `checked_at`,
`technical_status`, and all requested/extracted frame counts. `passed` means the
specified recording decoded and rendered on that runner within the budget;
it does not prove long-term cadence, archive discovery, subject-recognition
quality, filename timezone, or permission to redistribute stills. A signed-in
repository Actions page provides the full run log and job summary.

The report branch contains metadata only. Its bot writes require contents:write
and compatible branch protections. If persistence is restricted, retain the
Actions summary/artifact; do not reset or force-push branches. Report evidence
should be associated with the tested commit rather than silently reused after
extractor or source changes.

After runner technical validation, complete institutional reuse/attribution
review separately. Record reviewed terms and source approval before enabling
public recipe images. No additional source disabling or release requirement
should be based solely on Codex's outbound policy.
