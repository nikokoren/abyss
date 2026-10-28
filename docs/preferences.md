# Teach Abyss your image preferences

## Use the gallery

1. Open the repository's **Actions → Build preference review gallery**. Use the
   latest successful run, or **Run workflow** and choose the camera to review:
   `ooi-axial` (video), `ooi-hydrate-ridge` or `ooi-international-district` (stills).
   Scheduled runs continue to use Axial; each manual still-camera run produces
   its own gallery. The run summary names the camera.
2. Download **abyss-review-gallery**, unzip it, and open `index.html` in your
   browser. The file includes its images and application code. No API key,
   account on another service, or continuously running personal computer is needed.
3. Choose **A**, **B**, or **Neither**. Optionally mark a scene **Feels repetitive**.
   Original mode is selected by default. The optional e-paper approximation uses
   the former Abyss processing, not TRMNL's hosted native renderer. Skip pairs
   that look effectively identical. **Neither** means both scenes are unwanted;
   it teaches rejection of both and should not stand in for "these look the same."
   Keyboard shortcuts:
   `1`, `2`, `0`, and `S` to skip. Undo corrects the last change; **Review saved
   choices** lets you edit earlier decisions, including after reopening.
4. Aim for 30–50 comparisons across several batches. Choices save in browser
   storage. Download a JSON backup to move between browsers/devices or recover
   if storage is cleared; restore it in the matching gallery.
5. Click **Submit choices** and post the prefilled GitHub issue. Sign in as the
   configured reviewer (`nikokoren` by default in this repository). Large batches
   are split into several short drafts; post each numbered draft. Opening a
   draft does not send feedback until you post the issue. Your browser copy stays
   saved, so resubmission is safe.
6. **Learn image preferences** validates the issue and trains in GitHub Actions.
   Check the run's summary for counts/readiness and validation results. The next
   gallery and next configured production processing job load the updated model.

Feedback is stored in repository issues and the `preference-data` branch.
In a public repository those labels, model and metadata are public. Gallery
stills are delivered as an Actions artifact, whose access follows repository
permissions; they are not deployed to public Pages by this workflow. Artifact
access in a public repository is not a private-storage guarantee. Source rights
and attribution requirements still govern wider recipe publication.

The gallery artifact lasts 30 days. Feedback, feature manifests and learned
weights persist in Git. No raw recordings or model binaries are committed.
A fresh gallery is scheduled daily at **05:43 Berlin time currently** (04:43 UTC;
local time changes with daylight saving). The publication schedule remains twice
per day; personal preference learning does not alter it.

Browser policies can prohibit opening local HTML. This environment's managed
Chromium blocks file URLs; browser behavior was verified over loopback HTTP and
with networking disabled after loading. On a managed device with that restriction,
use an approved HTML preview or serve the extracted directory temporarily while
reviewing. For example `python3 -m http.server 8000` in that directory, then visit
its local page. This is optional review hosting, not recurring footage processing.

## What the model learns

The fixed feature extractor is **ImageNet-pretrained ResNet18 on CPU**. It outputs
512 normalized appearance features, augmented with brightness/contrast/sharpness,
clipping, basic quality and a bias term (518 values total). This can capture
visual structure and appearance beyond the original hand-written quality score.
It is not a vent/animal/plume detector and does not label scientific subjects.
The image encoder stays frozen; a small regularized logistic ranker learns from
paired choices on top of it. No hosted vision API, GPU or paid model endpoint is
required.

A/B choices train winner-minus-loser ranking constraints. **Neither** supplies
negative-utility anchors for both images; it does not create a false preference
for one over the other. Repetitive flags add negative anchors and a recent-hash
penalty. Skipped pairs are not training data.

At least eight unique comparisons, including four A/B choices, are required for
activation. Influence ramps up with feedback to a maximum 45% blend at 30
comparisons; technical quality/novelty retains the remaining weight. The model
ranks both promising moments for fine sampling and final readable candidates.
A scene below the source's technical minimum never wins over a readable scene
because of a learned preference score. Missing/incompatible/corrupt models or
unavailable vision dependencies use the quality scorer and report the fallback.

Coarse sampling stays uniform across recordings. The gallery includes every
coarse/fine candidate, including low-scoring scenes, and every fifth pair is an
exploration choice. Other pairs emphasize uncertain/close current scores. This
keeps the review pool broader than only the algorithm's winners. You can skip
pairs that are visually indistinguishable.

## Honest evaluation

Thirty comparisons from one gallery are not thirty independent scenes. The
training report counts unique reviewed pairs, not clicks or issue submissions.
Repeated/reversed pairs are deduplicated; the most recently updated issue is the
authoritative decision. Editing the same issue replaces its saved batch, while
Git history retains the audit trail.

Held-out evaluation groups all connected recording URLs together. A recording
cannot appear in both training and evaluation through different frames or
comparisons. Until at least three independent groups and enough held-out choices
exist, the report explicitly says evaluation is unavailable. A ready model can
still be provisional; its own training accuracy is never presented as evidence
of generalization. Once measurable, the report compares held-out ranking accuracy
against the original quality-only baseline. Keep reviewing fresh batches and
inspect this comparison rather than assuming improvement from model readiness.

No personal preference model has learned your taste until you actually submit
choices. The initial gallery initializes an empty `needs_more_feedback` model;
synthetic automated-test labels are never written into your live model.

## Cloud persistence and security

`preference-data` is separate from `main`, image-delivery state and cadence state:

- `batches/<batch-id>.json`: immutable metadata and trusted feature vectors.
- `feedback/issue-N.json`: normalized owner-authored feedback, including exact
  candidate features needed to reproduce training.
- `model.json`: learned weights, model identity, readiness and evaluation.
- `training-report.json`: the same diagnostic data without the weight vector.
- `gallery-report.json`: latest gallery batch/run and resource measurements.

Only the repository owner, or exact GitHub login in repository variable
`PREFERENCE_REVIEWER`, can train via issue events/manual dispatch. Both the issue
owner and acting editor must match. Training checks the batch's content-derived
identity, known candidate IDs, reviewer and feature-space version. Browser-supplied
features are rejected; features always come from the trusted manifest branch.
Malformed/foreign feedback cannot replace the current model. Issue text is read
as data from the event JSON; it is never interpolated into shell commands. Jobs
use the shared `preference-state` concurrency group and never force-push.

The generated gallery makes no authenticated API calls. Posting feedback uses
GitHub's regular signed-in issue form. Repo credentials stay on GitHub's runner,
never in HTML, URLs, JSON backups or browser storage. No automatic comments or
messages are sent to other people.

The production workflow restores a ready model, installs the optional CPU tools,
and passes it to `run`. A changed model revisits the current recent-recording
batch once, instead of silently skipping previously processed clips. The actual
capture timestamp remains unchanged. Existing source-rights release gates remain.

## Development and resources

Core processing/tests need the normal dependencies. Vision encoding is optional:

```sh
. .venv/bin/activate
bash scripts/install_vision.sh
python -m abyss.review --output output/review --reviewer nikokoren
```

The installer pins CPU-only PyTorch/torchvision from PyTorch's official index.
ResNet18 weights come from the official HTTPS URL. Their full SHA-256 is verified
on download and on every cache load; deserialization uses `weights_only=True`.
The weights are approximately 45 MB. The CPU torch wheel is approximately 196 MB
plus smaller dependencies. Pip/model caches reduce subsequent setup transfer.
These downloads are separate from the **64 MiB video payload cap**; encoder CPU
work is also additional and must be measured independently.

A gallery samples the standard three recordings with 12 coarse + up to four fine
frames. Generated review images and HTML go only to the download artifact; the
persistent branch holds metadata/features. Each daily gallery still consumes
runner setup time, video traffic, feature inference and artifact storage. Check
private-repository Actions allowances and repository/metadata growth. Retraining
uses NumPy and saved vectors, so it downloads neither recordings nor encoder
weights. Gallery generation fails explicitly if its required encoder is missing;
production scoring falls back to the baseline.

For still cameras, a manual gallery instead requests up to **nine snapshots at
least 20 minutes apart**. This selects different capture bursts and can cross
UTC dates. Each original JPEG is decoded at full resolution for scoring; only
small review previews are embedded in the gallery. Defaults allow at most
**216 MiB** for nine images (24 MiB each); all still-review configurations are
capped at **256 MiB**, and a smaller explicit `--max-bytes` is respected. Failed
retrievals can reduce the candidate count. At least two are needed for a gallery.
The source registry's production limit of two snapshots/48 MiB is unchanged.
No review candidates are added to public Pages image history. Feedback from all
cameras trains the same appearance ranker, so still-camera choices also teach
the shared model. Review 20–30 comparisons from each still camera, then use a
fresh capture window rather than repeating the same batch.

Still-camera galleries now collapse near-identical views before creating pairs,
keeping the best-quality representative. If fewer than two distinct views remain,
the Actions summary and downloaded gallery say **No review needed**. This is a
successful observation, not a retrieval failure; no preference labels are invented
and the camera remains in normal display rotation. Video review sampling and
production selection are unchanged.

The initial heuristic combines at least 88% structural-hash agreement and 0.975
appearance-vector cosine similarity, while requiring brightness differences no
greater than 0.04 and quality-score differences no greater than 0.05. It is not
an animal/change detector, and may group small subject changes. The actual nine
Hydrate Ridge snapshots and nine International District snapshots reported as
near-identical by the owner each collapse to one representative under this rule.
The original 95% structural threshold was too sensitive to International
District's texture variations; appearance, brightness and quality guards remain.
Use CLI `--include-similar` to inspect an unfiltered
batch when checking a possible false positive. A static batch can be skipped
entirely; more clicks on visually indistinguishable scenes are not useful training.

Tests:

```sh
python -m unittest discover -s tests -v
node tests/review-core.test.js
# Optional with Playwright and Chromium installed:
python scripts/check_review_browser.py --chromium /usr/bin/chromium
```

The browser test covers choices, repetition, undo, reload persistence, backups,
imports, editing, safe GitHub draft URLs, responsive layout and offline
interactions. `--check-file` also tests opening the local HTML where browser
policy permits file URLs. Tests use clearly labeled synthetic images; they do
not create personal feedback or post issues.

## First real review batch (observed)

[Run 40603578617](https://github.com/nikokoren/abyss/actions/runs/40603578617)
successfully generated **16 real OOI candidates** (12 coarse, four fine) for
reviewer `nikokoren`. Batch ID: `938d7ba235186da5fa7d331fa713f20a`.
The CPU encoder's full weight checksum matches the official ResNet18 artifact.
The search fetched 45,026,088 video bytes in 59.087 seconds; gallery generation
including encoder preparation took 62.533 seconds, excluding dependency setup.
The [metadata report](evidence/ooi-20261028-preference-gallery.json) records the
run URL, candidate counts and exact encoder provenance.

The trusted manifest and empty model were persisted in preference-data commit
`ec4849628fde3340291039694da38027f4b693be`. The model has zero comparisons and
status `needs_more_feedback`; no synthetic labels were substituted for your
choices. The persisted branch contains no PNG/JPEG/HTML/model-binary files.
The actual imagery is in the downloadable Actions gallery artifact.
