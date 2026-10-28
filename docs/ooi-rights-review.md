# OOI CAMHDA301 derived-still reuse review

Reviewed **28 October 2026**. Decision: enable the `ooi-axial` source for
attributed, freely accessible derived stills in Abyss. This review covers the
CAMHDA301 instrument recordings; it does not approve unrelated photographs,
expedition footage, third-party datasets, or institutional branding.

## Primary evidence

Official pages and the linked terms PDF were retrieved successfully by
[GitHub-hosted run 40651933247](https://github.com/nikokoren/abyss/actions/runs/40651933247).
The [immutable capture](https://github.com/nikokoren/abyss/tree/b24fb04ec4c9e1ad4d5fc89e16bb390494156bfb/terms/ooi-axial/40651933247)
contains extracted text, original PDF, retrieval timestamps, HTTP results,
original-response SHA-256 hashes and discovered links. No source imagery was
published by this capture. Codex's CONNECT 403 does not alter these results.

| Official source | Finding |
| --- | --- |
| [How to Use, Acknowledge, and Cite Data](https://oceanobservatories.org/how-to-use-acknowledge-and-cite-data/) | All OOI data are freely available. Requires OOI acknowledgment, appropriate citations and acknowledgment of U.S. NSF support. Core data must credit the WHOI OOI Program Office. Current funding acknowledgment names Cooperative Agreement **2244833**. |
| [OOI User Terms and Conditions, v2-00, 2019-01-02](https://oceanobservatories.org/wp-content/uploads/2022/12/1102-00020_Data_User_Terms_Conditions_OOI_2019-01-02_Ver_2-00.pdf) | Defines OOI data to include connected instruments and derived visualization products. Section 4.5 permits direct/indirect redistribution at no cost; 4.1 and 4.9 require attribution, citation and intact copyright notices. Sections 4.3 and 4.12 exclude operational/decision-making uses and implied promotional endorsement. |
| [UW/RCA High Definition Video Camera](https://interactiveoceans.washington.edu/instruments/high-definition-video-camera/) | Identifies the UW-built OOI camera at Mushroom in ASHES, describes its three-hour recordings and pan/tilt routine, and links directly to our exact `RS03ASHS/PN03B/CAMHDA301/` archive. This establishes that these recordings are OOI instrument data. |
| [OOI Platforms and Nodes](https://oceanobservatories.org/site-list/) | Lists ASHES Vent Field, `RS03ASHS`, and platform DOI [10.58046/OOI-RS03ASHS](https://doi.org/10.58046/OOI-RS03ASHS). This is a platform DOI, not a fabricated clip DOI. |
| [NSF Policy on Brand Standards](https://www.nsf.gov/policies/brand) | NSF logos are not public domain and require authorized use. Award-recipient permissions do not establish that Abyss is an award recipient. |

The current acknowledgment page links to the 2019 v2-00 terms PDF despite
referring to 2022 financial/administrative terms in its prose. The review uses
the actual linked document and the current acknowledgment wording; it does not
invent a newer OOI data license. Neither a Creative Commons license nor public
domain status is asserted.

## Attribution and rendering

Every production OOI device view displays this compact native credit beneath
the photograph. The separately downloadable PNG embeds the same credit outside
the complete footage:

> Data: OOI / WHOI OOI Program Office / UW | Supported by U.S. NSF 2244833

The previous two-line image credit and duplicate device metadata block were
condensed on 28 October 2026. The screen retains source, Program Office,
university and funding credit; the recipe settings and product page carry the
expanded organization names, full acknowledgment, source link and terms.

Production now preserves the complete full-resolution RGB frame, retaining all
source notices and original photo pixels. The device receives a clean photo and
native attribution text, allowing white text on a black canvas in dark mode.
The attributed downloadable artifact appends a separate credit band without
overwriting footage. Both assets are published before latest metadata updates.
The native TRMNL renderer handles resizing and
dithering for the device. Explicit 800 × 448 inspection variants and review
gallery paper previews remain available for comparison; they are not production
image delivery. Immutable QR observation pages carry the expanded credit and
link to the source snapshot or video and the exact published still.

Public metadata, generated recipe settings and the viewer carry the expanded institution names. The viewer also carries the terms
link, original recording URL, platform DOI, processing description and the
official acknowledgment:

> This material is based upon work supported by the Ocean Observatories Initiative (OOI), a major facility fully funded by the US National Science Foundation under Cooperative Agreement No. 2244833, and the Woods Hole Oceanographic Institution OOI Program Office.

The viewer states that source acknowledgment implies no endorsement and that
OOI data are not for operational or decision-making use. The intended release
provides free ambient viewing, with no claim that the image is live or that
OOI/NSF/WHOI/UW sponsor Abyss.

OOI's acknowledgment page also says “Please use the NSF logo if a presentation
is graphical in nature.” NSF's linked policy restricts logo use separately.
Abyss uses the required textual acknowledgment and does not add NSF or OOI
logos or claim award-recipient status. A newly added logo or a promotional use
would need its own authorization review. Existing notices in the footage are
retained.

## Scope and follow-up

`sources.json` now records the review date, terms evidence and approved
derived-still scope, making OOI eligible for the production pipeline. This
does not establish that Pages is deployed or that TRMNL has rendered an image.
The hosting/device steps remain in [deployment.md](deployment.md).

Publication appearance delay and filename timezone remain separate technical
uncertainties. Current timestamps are explicitly labeled as assumed UTC from
the filename; the camera page's mixed EDT/PDT schedule text is not independent
proof of the filename timezone. No terms decision was inferred from cadence.

Recheck the official pages before a broader release or changed use, especially
paid redistribution, advertising, institutional logos, or another camera/data
owner. OOI reserves the right to change its terms. No permission request or
other message was sent to OOI or NSF as part of this review.
