# Publication handoff

## What is ready

Abyss is deployed on GitHub Pages with four genuine OOI camera feeds, an
owner-trained preference model, source attribution and native TRMNL Framework
3.4.4 layouts. [Current validation](validation.md) distinguishes hosted results,
browser checks and the remaining limitations. [Source rights](ooi-rights-review.md)
cover attributed instrument-data stills, not institutional logos or unrelated
website imagery.

Camera names and order match About, the selection dropdown and rotation:

| Camera | Source ID | Approximate depth |
| --- | --- | --- |
| ASHES: Mushroom vent | `ooi-axial` | 1,540 m |
| International District: Tiny Towers | `ooi-international-district` | 1,520 m |
| Southern Hydrate Ridge: Einstein's Grotto | `ooi-hydrate-ridge` | 780 m |
| Oregon Offshore: seafloor | `ooi-oregon-offshore` | 580 m |

Production processes images every three hours (`23 */3 * * *`, UTC).
TRMNL's separate 15-minute refresh rotates saved views. Empty camera selection
means all published cameras; offline cameras keep their slot and last good image.
Full-resolution source colour is preserved; TRMNL handles device dithering.

## Install the current recipe

- Download https://nikokoren.github.io/abyss/abyss-trmnl.zip and import the whole
  recipe, including settings, Python transform, Shared and all four layouts.
- Production polling is **GET** https://nikokoren.github.io/abyss/catalog.json.
- [settings.txt](../trmnl/settings.txt) contains the exact editor values, complete
  Custom Fields YAML and full recipe YAML. The Custom Fields editor takes the
  list without a `custom_fields:` wrapper.
- [about.txt](../trmnl/about.txt) replaces an existing `author_bio` block and
  preserves the owner's category/contact metadata. Replace the existing About
  block rather than adding a duplicate. Generated settings use `about_abyss`.
  Both use explicit `<br>` breaks for the settings page.

Re-importing settings replaces static options; updating markup alone does not
install rotation or refresh camera choices. See the [full guide](../trmnl/README.md).

## Storefront capture

[storefront.json](../trmnl/storefront.json) is a fixed, real Oregon Offshore
photograph with fish, captured on 22 October 2026. Its original OOI JPEG preserves
5344 × 4008 colour pixels; the data includes the actual capture time and credits.
It is a manually selected showcase, not a promise that every update shows animals.

Follow [storefront.txt](../trmnl/storefront.txt): temporarily use the static data,
clear camera selections or choose Oregon Offshore, and leave QR off for capture.
Keep the existing layouts and transform. After generating the storefront image,
**restore the production polling URL before submitting the recipe**.
Do not ship the static sample as the normal feed.

## Final owner checks

1. Check the actual TRMNL account preview, including TRMNL X landscape/portrait
   and each layout you intend to publish. Review the corrected About and camera
   dropdown in the settings page.
2. On a physical device, check image readability, camera changes, rotation and
   optional QR scanning. The automated browser matrix passed 100 cases; it does
   not establish physical-device readability or hosted dithering results.
3. Restore production data after the storefront capture and confirm the final
   account settings and screenshots. Repository tests cannot inspect or submit
   the account's publication form.
4. Decide how the project's code may be reused. No code license has been chosen;
   imagery rights and required acknowledgment remain separate. This is an owner
   decision, not an assertion about TRMNL's submission policy.

Automated hints can be heuristic: photos already have `image-dither`, every view
has `layout layout--col` and an inline native `title_bar`, and QR images remain
undithered for scanning. Explicit `lg:`/`portrait:` overrides are not necessary
for every flexible layout. Do not replace working markup solely to satisfy a
pattern check; use the actual previews and the reviewer’s feedback.

Known limitations remain documented: Offshore can lose contrast on one-bit
screens, preference accuracy is provisional, ASHES video filename UTC is assumed,
and account billing/delivery usage needs monitoring. No paid API key or personal
computer left online is required by the production workflow.
