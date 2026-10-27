# Recent-recording search and cadence measurement

## Selection behavior

The production `run` command now searches up to the three newest eligible
recordings, including across UTC day boundaries. It skips URLs already recorded
as successfully processed or rejected, unless `--force` is used. Selection is
across the current batch of unseen recordings, not an all-time best-frame library.

1. Coarse stage: up to four uniformly spaced frame samples per recording.
2. Rank all decoded candidates with the existing quality and recent-image
   similarity scoring.
3. Fine stage: sample two additional nearby offsets around each of the two best
   usable moments. The offset is one quarter of that recording's coarse spacing.
4. Choose the highest-scoring candidate across both stages and all recordings.
   Equal scores prefer the newer recording. Preserve the previous public image
   if no candidate clears the source threshold.

Default maximum: 12 coarse + 4 fine samples across three recordings. A recording
has a separate eight-candidate maximum. Short recordings may use fewer coarse
samples; dark/flat or otherwise low-quality scenes do not trigger refinement.
No animal/vent recognition or subject-following crop has been added.

One **64 MiB video-payload budget is shared across the entire source search**,
not reset for each recording. Each recording keeps its range cache through both
stages. Invalid files and failed seeks are recorded individually. Good decoded
frames from other recordings survive; `search_complete: false` discloses partial
coverage, including budget exhaustion. Only completely searched recordings are
added to the durable processed list; partial failures can be retried on a later
run. This does not guarantee the whole search fits every source's codec/GOP;
actual bytes and coverage must be inspected.

Arguments on `python -m abyss.cli run`:

```
--recordings 3 --coarse-candidates 4 --refine-candidates 4 \
--refine-windows 2 --candidates 8 --max-bytes 67108864
```

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
