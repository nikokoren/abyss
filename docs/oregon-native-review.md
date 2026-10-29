# Oregon Shelf and Offshore native-preview recheck

**Historical review, 28 October 2026.** This six-hour recheck initially held both
cameras for display quality. Offshore was subsequently enabled after a broader
[seven-day wildlife sample](offshore-wildlife.md), accepted owner preferences
and [verified production deployment](evidence/offshore-production-20261029.json).
Oregon Shelf remains on hold. The measurements below describe the earlier
review and do not revoke Offshore's current release status.

[GitHub-hosted run](https://github.com/nikokoren/abyss/actions/runs/40765670080)
sampled six snapshots per camera at least an hour apart, spanning five hours.
All 12 downloads decoded at **5344 × 4008**, without failed requests. The separate
review budget was 144 MiB per camera; production limits remain unchanged.
No preference labels or training examples were created from this inspection.

| Camera | Payload | Best quality score | Visual result |
| --- | ---: | ---: | --- |
| Oregon Shelf, about 80 m | 118,000,355 bytes | .606 | Heavy backscatter, persistent dark patches and low scene contrast across the six samples. Four-bit reveals more of the scene; one-bit remains hard to read. |
| Oregon Offshore, about 580 m | 55,338,171 bytes | .608 | Seabed detail and small seabed animals visible in four-bit. Central illumination and low contrast dominate the one-bit preview. |

The automated quality threshold of .30 passes both cameras. This does not prove
that either image makes a useful ambient display: edges from suspended particles
can score well despite a poorly readable scene. Fresh footage and native delivery
had not resolved the visual concerns at this checkpoint. The later Offshore
release retains the one-bit contrast limitation. Neither camera was classified
as offline or technically inaccessible.

Original-colour thumbnails preserve the full frame and carry embedded credit.
The best-scoring frame per camera was also rendered in the official, unmodified
Framework 3.4.4 full-screen layout, light/dark, for OG and V2. Grayscale conversion
uses the documented TRMNLP ImageQuantizer steps, without Abyss's old contrast,
sharpening or ordered-dither adjustments. These are native-layout previews,
**not a render observed in a TRMNL account or on physical hardware**.

[Technical report](evidence/oregon-native-recheck-20261028.json) records the exact
capture URLs, timestamps, scores, dimensions, transfer bytes, native layout checks
and quantizer reference. [Attributed previews and downloadable review HTML](https://github.com/nikokoren/abyss/tree/7036dbd6cbf8a3f52132301bdcf182c4c1c7c0f1/reviews/40765670080)
remain on the separate evidence branch; the workflow artifact contains a ZIP
that can be opened locally.
