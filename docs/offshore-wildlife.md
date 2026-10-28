# Oregon Offshore wildlife: a seven-day visual sample

A conservative visual review found **clear fish in 12 of 42 sampled images
(29%)**, with another **9 uncertain fish-like sightings**. Small seabed animals
were visible in all 42 frames. These include crustacean-like and star-like forms;
no species identification was attempted.

This supports including Offshore as a wildlife-bearing camera. It does not
establish a visit rate or mean a new animal arrives every time the image changes.
Some of the seabed animals are residents and can appear in many frames.

## Sample and method

[GitHub-hosted run](https://github.com/nikokoren/abyss/actions/runs/40769530980)
retrieved one capture nearest each of 00:00, 04:00, 08:00, 12:00, 16:00 and
20:00 UTC on **22–28 October 2026**. Candidates had to be completed and within
30 minutes of the target slot. Capture time alone selected the images: there
was no quality, model, wildlife or aesthetic filtering. The previously praised
19:16 frame was not manually added to this cohort.

All **42/42** slots decoded successfully at **5344 × 4008**. JPEG payload was
388,265,087 bytes (about 370 MiB), below the separate 512 MiB study budget.
The study did not change production limits or its then twice-daily schedule.
Production was subsequently moved to every three hours. This study is
manual/explicit only and is not scheduled to download a week of images daily.

The assistant visually inspected all seven daily contact sheets and checked
larger previews/crops for ambiguous forms. The derivatives retain original
colour, the complete frame and source credit, at up to 2560 pixels wide.
Original full-resolution URLs remain in the manifest and gallery.

| UTC date | Clear fish | Uncertain fish-like forms | No confident fish observed | Small seabed animals visible |
| --- | ---: | ---: | ---: | ---: |
| 22 October | 4 / 6 | 1 / 6 | 1 / 6 | 6 / 6 |
| 23 October | 1 / 6 | 1 / 6 | 4 / 6 | 6 / 6 |
| 24 October | 1 / 6 | 2 / 6 | 3 / 6 | 6 / 6 |
| 25 October | 2 / 6 | 2 / 6 | 2 / 6 | 6 / 6 |
| 26 October | 0 / 6 | 2 / 6 | 4 / 6 | 6 / 6 |
| 27 October | 2 / 6 | 0 / 6 | 4 / 6 | 6 / 6 |
| 28 October | 2 / 6 | 1 / 6 | 3 / 6 | 6 / 6 |
| Total | **12 / 42** | **9 / 42** | **21 / 42** | **42 / 42** |

“Clear” requires a recognisable fish body with a head, fins or tail; recognisable
partial fish count. “Uncertain” includes plausible fish-like, eel-like, blurred
or partly cropped forms without enough anatomy to identify confidently. “Not
observed” means no confident fish was seen; it does not prove fish were absent.
The unclear sightings are excluded from the 29% figure. This is a descriptive
single-reviewer pass, not expert taxonomic validation or a random ecological
survey. Correlated resident animals and missed distant animals limit inference.

## Review the images

Download **offshore-week-wildlife-gallery** from the
[workflow run](https://github.com/nikokoren/abyss/actions/runs/40769530980), unzip,
and open `index.html`. It contains every selected frame and original image link.
The [immutable sampling manifest and images](https://github.com/nikokoren/abyss/tree/d573d25cead8b24feb66796cdae1a33db69cb724/reviews/40769530980)
remain separately from production delivery. The
[per-frame visual annotations](evidence/offshore-wildlife-review-20261028.json)
record the reviewer, certainty, notes, original URLs and preview URLs.

Examples of the variety include:

- [Sample 04: multiple fish in the illuminated scene](https://raw.githubusercontent.com/nikokoren/abyss/d573d25cead8b24feb66796cdae1a33db69cb724/reviews/40769530980/04-colour.jpg).
- [Sample 34: fish above a sediment plume](https://raw.githubusercontent.com/nikokoren/abyss/d573d25cead8b24feb66796cdae1a33db69cb724/reviews/40769530980/34-colour.jpg).
- [Sample 36: a large fish in the foreground](https://raw.githubusercontent.com/nikokoren/abyss/d573d25cead8b24feb66796cdae1a33db69cb724/reviews/40769530980/36-colour.jpg).

Raw quality scores remain a poor substitute for interest: sample 18, with no
confident fish observed, scores .617; the striking fish/plume frame 34 scores
.612. A broader, time-spread selection pool and owner preference feedback are
worth exploring. These visual observations were **not** submitted as owner
preference labels, used to train the model, or used to enable the camera.

## Teach the preference model

The **Review Offshore wildlife preferences** workflow builds an A/B gallery from
these exact 42 original snapshots. It downloads the originals within a separate
512 MiB cap, extracts the same ResNet18 features used in production, and includes
larger attributed colour previews. All 42 remain available: the static-background
duplicate filter is bypassed for this explicitly requested, time-spread review.
No assistant animal annotations are included as labels or shown to guide choices.

Download **abyss-offshore-preference-gallery**, unzip and open `index.html`.
Choose A, B or neither; skip pairs that look the same. Aim for 30–50 comparisons,
without completing every possible pair. Use **Submit choices** and post each
prefilled GitHub issue. The existing owner-only feedback workflow validates the
saved feature manifest and retrains the shared ranking model automatically.
Browser-saved choices alone do not reach cloud training; post the issue drafts.

This is a training cohort, not a new frozen video evaluation. The source remains
on its existing production hold until separately enabled. There is no recurring
weekly image download: this review workflow is manual or triggered by its own
implementation changes.

Data: OOI / WHOI OOI Program Office / University of Washington; supported by the
U.S. National Science Foundation under Cooperative Agreement 2244833. Images and
the gallery carry the full acknowledgment and link to OOI reuse terms.
