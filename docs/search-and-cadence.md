# Recent-recording search and cadence measurement

## Selection behavior

The production `run` command samples the three newest eligible video recordings,
including across UTC date boundaries. Six coarse moments per recording and up
to six fine seeks give a maximum of 24 frames, under one shared **96 MiB** budget.
Each recording has a ten-frame cap. Refinement visits each recording's strongest
usable moment before spending another window on the same recording.

Each recording's best readable frame is published to the bounded session index
(`sources/ID/sessions.json`, six recent winners). Current camera selection compares
winners within the current three-recording window. Known sessions reuse their
saved image and scores; changed model/search contexts require reevaluation. A
new, weaker clip can leave the existing camera winner unchanged. Capture and
publication timestamps stay accurate. A failed session batch leaves the camera's
previous latest metadata intact. Partial extraction remains visible in diagnostics;
only fully searched URLs enter the durable processed list.

Defaults:

```
--recordings 3 --coarse-candidates 6 --refine-candidates 6 \
--refine-windows 3 --candidates 10 --max-bytes 100663296
```

[Retention and fresh evaluation](retention-and-sessions.md) explains saved images,
QR fallbacks, output-branch compaction and leakage-free review batches.

`--interval` limits coarse sampling density; refinement intentionally samples
more densely near promising moments. `inspect` retains its single-recording
uniform sample/processing-comparison behavior. No automatic public release or
rights approval is implied by a successful search.

## Measuring OOI cadence

The independent **Observe OOI cadence and frame search** workflow runs hourly,
at minute 17 UTC. Scheduled runs list the current UTC day and two preceding days.
They do not download video, install video dependencies, or publish images. The
observation module's metadata-only path uses Python's standard library.

Reports distinguish:

- **Recording intervals:** differences between filename timestamps visible in
  the archive. Report includes sample count, median, range and common gaps.
  Gaps can reflect recording schedules, missing files or incomplete coverage;
  do not interpret the median alone as an SLA.
- **Publication appearances:** a new filename first observed after an earlier
  successful listing of the same date. Its appearance is bracketed between the
  preceding request's start and the current response's completion. Baseline
  files, including a newly checked day, have unknown publication time and never
  create a delay measurement.
- **Timestamp uncertainty:** filenames are parsed as UTC but that timezone has
  not been independently confirmed. Delay bounds are therefore labeled nominal;
  filename intervals do not depend on a constant timezone offset.

The history retains seven days of seen records and up to 168 observations. Failed
listings are errors, not observations that all files disappeared. If no directory
can be read, the last good state is preserved. Hourly Actions scheduling may be
late or dropped; bounds use actual observed checks, not the cron's intended time.
Wait for at least two observed additions before describing publication delay as
measured. No artificial sleeps or fake historical polling are used to create data.

Metadata evidence lives on the `source-observations` branch:

- `observations/ooi-axial/state.json`: durable first-seen history.
- `observations/ooi-axial/latest-cadence.json`: latest measured summary.
- `observations/ooi-axial/latest-search.json`: most recent requested benchmark,
  preserving its own run URL and tested commit (not overwritten by hourly checks).
- Run-ID/attempt reports: historical metadata evidence, without imagery.

```
git fetch origin refs/heads/source-observations:refs/remotes/origin/source-observations
git show origin/source-observations:observations/ooi-axial/latest-cadence.json
git show origin/source-observations:observations/ooi-axial/latest-search.json
```

Pushes changing this study/search implementation trigger an initial live search
benchmark and observation. A manual workflow run can request another benchmark;
normal hourly checks do not. The benchmark exercises actual OOI discovery and
coarse/fine extraction without bypassing the independent public-release rights
gate. All candidate images are temporary and only reports are retained.

The twice-daily publication schedule is unchanged. Measuring an hourly archive
listing does not mean generating an hourly TRMNL image. Set an eventual publication
schedule from observed cadence, source quality and account quotas rather than
assuming every check can supply fresh footage.

Hourly metadata jobs still consume runner startup time and metadata transfer.
On a private repository, include 24 scheduled jobs/day in the plan/billing budget;
public standard-runner policy does not establish unlimited hosting/storage.
Artifacts expire after seven days. Metadata-only Git history grows over time;
monitor repository size and retire/reduce observation frequency once enough
cadence and delay data has been collected.

## First observed runner result — 28 October 2026 (Berlin)

[GitHub run 40600427507](https://github.com/nikokoren/abyss/actions/runs/40600427507)
completed successfully on tested commit `c094b56a98e341094290fe734113220c67b8f076`.
Immutable metadata evidence was saved in commit
`30c6908481b749a667d1ac71c7e351f54fec7171` on `source-observations`.

The archive observation listed 24 recordings over 25–27 October (UTC filename
dates); all 23 consecutive filename gaps were exactly 10,800 seconds, or three
hours. There were zero publication-delay samples because this was the baseline.
First appearance is not a guarantee that a file is complete/decodable; the
production one-hour age filter and stable range/ETag checks remain in place.

The adaptive search processed the 21:15, 18:15 and 15:15 UTC recordings from
27 October. It extracted all 12 coarse frames and all four fine frames, with
complete coverage and no seek errors or budget exhaustion. Transfer was
44,501,800 bytes over 175 upstream range requests in 55.044 seconds, under the
67,108,864-byte shared cap. The three full recordings total 2,847,869,733 bytes;
the search retrieved about 1.56% of that payload.

The winner was the 18:15 recording at offset 781.689 seconds, quality .938558.
It was a coarse candidate; the fine samples did not outperform it. This run
demonstrates choosing an older recording over the newest, without claiming
refinement must always improve the score. No imagery was published.

[Cadence report](evidence/ooi-20261028-cadence.json) ·
[Adaptive-search report](evidence/ooi-20261028-search.json)
