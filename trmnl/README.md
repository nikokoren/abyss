# TRMNL integration

Generate `settings.yml` after at least one source passes technical and rights
validation **and** has published an image:

```
python -m abyss.cli recipe --base-url https://OWNER.github.io/abyss
```

Import generated settings in a TRMNL private plugin/recipe, with `full.liquid`
and `shared.liquid` from this folder. The export follows public recipe select
fields (`custom_fields`, `field_type: select`, label/value option mappings).
Settings persist as `trmnl.plugin_settings.custom_fields_values.source_id`.
The recipe polls one small catalog; Liquid selects `sources[source_id]` and
falls back to a retained default when a selection disappears. All validated
sources are preprocessed by the shared scheduled job, so changing selection
changes the displayed footage without exposing keys or triggering costly
per-user video jobs. It does not trigger an immediate processing job.

The 800×480 default display uses an 800×448 image plus a title bar. OOI's image
contains the complete resized footage and a separate NSF/WHOI/UW credit band;
Shared markup does not overlay a second credit onto that footage. Other
devices can use CLI width/height and adapted markup. Grayscale is opt-in;
ordered 1-bit output is the conservative default pending physical testing.
Only a full-screen layout is supplied. Use TRMNL's preview and a physical device
to validate rendering; cloud TRMNL import/render has not been executed here.
Re-import regenerated settings when sources are added/disabled. An already
installed recipe retains its old dropdown until updated, but the catalog marks
unavailable sources and keeps honest timestamps. No validated sources means no
settings export, rather than a misleading placeholder choice.
