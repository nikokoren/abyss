# Bounded image history, session winners and fresh evaluation

Production keeps full source resolution and native TRMNL rendering. The normal
processing schedule remains 03:23 and 15:23 UTC (04:23 and 16:23 CET in Berlin
on 28 October); the recipe's 15-minute polling
and camera rotation are independent.

## What stays online

The public bundle has a **640 MiB** budget, below Pages' 1 GB site limit. Current
camera images are protected even when a camera is offline. Video session winners
referenced by `sources/ID/sessions.json` are also protected. Each video camera's
index keeps its six newest recording winners. Still cameras keep their current
full-resolution observation and, when space permits, one previous observation.
Optional full-size history retires first if the total exceeds the budget.

QR URLs keep identifying the same observation. Each page has a compact attributed
JPEG preview and the exact original snapshot or video/timestamp link. The twelve
newest previews per camera are retained, plus current/session previews. Older
pages continue linking to the original footage when their preview retires. Full
PNG links are removed from a page when those files retire; the page never silently
switches to a different observation. Source archives must still serve their media
for direct original-footage playback. Existing issued QR pages are migrated before
any referenced full-size PNG is removed.

Direct bookmarks to retired full-size PNGs have a limited lifetime. Use the QR
observation URL for lasting references. A TRMNL device already displaying a cached
bitmap keeps it; the next successful poll uses the current protected image. New
full-resolution images are not downscaled by retention. `state/retention.json`
reports actual bytes, removals and protected assets. A budget too small for current
assets blocks deployment rather than deleting the last good images.

`ocean-output` is a generated snapshot branch: each update has one root commit
containing the current `public/` and processing `state/`. `state/previous-sources.json`
keeps one previous processing-state snapshot for recovery. An exact force-with-lease
on that branch rejects concurrent updates. The main source branch, preference
labels and learned models are not rewritten. A 32-entry metadata publication log
records source commits, previous snapshot IDs and retention statistics. Old large
PNG blobs are no longer reachable through output-branch ancestry; GitHub may
retain unreferenced objects until its garbage collection runs. Git checkout/index
for the source workspace is not changed by publication.

## How session selection works

The default video search samples six evenly spaced moments in each of three
recent recordings, then up to six nearby refinement frames. Each recording's
strongest moment gets a refinement opportunity before revisiting a recording.
The per-recording cap is ten candidates, and all video transfers share one
**96 MiB** budget. Short recordings, quality rejection or retrieval errors can
reduce the maximum **24 frames**. Partial coverage is reported explicitly.

The best readable frame of each recording is saved with its immutable image,
recording URL, frame offset, source time, score and model/search context. The
camera winner is then chosen among the saved winners for the current three
recordings. Valid cached winners participate when only one recording is new.
A new clip does not automatically displace a stronger recent session. Model or
search-policy changes trigger rescoring and prevent mixing incompatible cached
scores. Identical camera winners keep their original publication timestamp.
A failed multi-session publication cannot commit a half-finished camera update.
The unchanged technical quality gate still rejects unreadable frames.

## What the fresh review validates

The video gallery loads the trusted feedback state. It excludes recordings used
in actual submitted choices and requests footage newer than the latest reviewed
recording for that camera. Previously offered but unreviewed frames are not
silently treated as labels. One new eligible recording is enough to create a
batch; if none is available, the gallery says **Waiting for fresh footage** and
creates no comparisons. Infrastructure failures remain errors, not empty success.

The gallery freezes the current model ID and every candidate's learned ranking
and quality-only score before any new choices arrive. Submit 20–30 useful A/B
choices from the fresh gallery. On feedback submission, the training report's
`prospective_evaluation` compares those frozen predictions with your choices.
This compares both rankers on the same candidate pool, whose fine sampling was
guided by the active model; it is not an independent end-to-end search benchmark.
Ties receive half credit; Neither decisions do not count as A/B wins. Edited or
split submissions are deduplicated. Training recordings and unavailable model
predictions are excluded. Fewer than ten choices are reported as collecting;
measured percentages still include recording counts and a small-sample caution.
Pairs within the same recording are correlated, so these percentages are not
proof of broad generalization.

The existing connected-recording holdout evaluation remains separate. New labels
train the next model, while prospective accuracy refers to the frozen model that
made the predictions. Reviewers' choices cannot be supplied by the pipeline.
