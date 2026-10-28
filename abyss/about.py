"""Shared public-recipe introduction and camera geography."""
from html import escape


SUMMARY = 'A window into the deep ocean'
HEADLINE = 'A window into the abyss.'
INTRO = 'Turn your TRMNL into your personal window into the deep ocean.'
OVERVIEW = (
    'Turn your TRMNL into your personal window into the deep ocean. Abyss lets you '
    'peek into a fascinating corner of our planet: the deep Pacific. '
    'Look into hydrothermal vent habitats on Axial Seamount, an active underwater volcano, '
    'and a methane seep at Southern Hydrate Ridge off Oregon. These are real research '
    'camera images from places most of us will never visit.\n\n'
    'This window is made possible by public investment in science. The U.S. National '
    'Science Foundation funds the Ocean Observatories Initiative, whose Regional '
    'Cabled Array connects deep-ocean instruments to shore through a 900-kilometre '
    'network of power and data cables. '
    'Scientists, engineers and research crews keep this observatory running, '
    'and open data lets the rest of us look in, right from your TRMNL.\n\n'
    'Abyss selects stills from these cameras\' periodic recordings and snapshots. '
    'Cycle through all three cameras, choose a few favourites, or settle into one. '
    'The default 15-minute refresh rotates your selected views. Images are processed '
    'twice daily, and a camera\'s last good image stays on display when it cannot '
    'update.'
)
CAMERAS = (
    {
        'id': 'ooi-axial', 'name': 'ASHES: Mushroom vent', 'depth': 'about 1,540 m',
        'description': ('On Axial Seamount, an active submarine volcano on the Juan de Fuca Ridge, '
                        'hundreds of kilometres off the Oregon coast. This camera looks into the ASHES hydrothermal '
                        'vent field, where hot fluids emerge from the volcanic seafloor.'),
        'site_url': 'https://interactiveoceans.washington.edu/research-sites/axial-caldera/ashes/',
        'map_url': 'https://oceanobservatories.org/array/cabled-axial-seamount-array/',
        'map_label': 'OOI Axial Seamount maps and diagrams',
        'array_graphic_url': 'https://oceanobservatories.org/wp-content/uploads/2020/10/CEV-OOI-CabledArray-Axialt-scaled.jpg',
        'site_map_url': 'https://s3-us-west-2.amazonaws.com/media.ooica.net/wp-content/uploads/2020/08/06193730/ASHES-Map-2020.png',
    },
    {
        'id': 'ooi-international-district', 'name': 'International District: Tiny Towers',
        'depth': 'about 1,520 m',
        'description': ('A second vent field on the same volcano, Axial Seamount. The Tiny Towers '
                        'camera gives us another view of its hydrothermal habitat. International '
                        'District is the name of this seafloor vent field.'),
        'site_url': 'https://interactiveoceans.washington.edu/research-sites/axial-caldera/international-district/',
        'map_url': 'https://oceanobservatories.org/array/cabled-axial-seamount-array/',
        'map_label': 'OOI Axial Seamount maps and diagrams',
        'array_graphic_url': 'https://oceanobservatories.org/wp-content/uploads/2020/10/CEV-OOI-CabledArray-Axialt-scaled.jpg',
        'site_map_url': 'https://s3-us-west-2.amazonaws.com/media.ooica.net/wp-content/uploads/2020/08/06193821/Tiny-Towers-Hydrothermal-Field-Map-2020.png',
    },
    {
        'id': 'ooi-hydrate-ridge', 'name': "Southern Hydrate Ridge: Einstein's Grotto",
        'depth': 'about 780 m',
        'description': ('About 90 km west of Newport, Oregon, on the Cascadia continental margin. Here the camera '
                        "looks across Einstein's Grotto, an active methane seep at Southern "
                        'Hydrate Ridge. This is a separate site from the volcanic vent fields '
                        'at Axial Seamount.'),
        'site_url': 'https://interactiveoceans.washington.edu/research-sites/southern-hydrate-ridge/',
        'map_url': 'https://oceanobservatories.org/array/cabled-continental-margin-array/',
        'map_label': 'OOI continental-margin maps and diagrams',
        'array_graphic_url': 'https://oceanobservatories.org/wp-content/uploads/2020/10/CEV-OOI-CabledArray-ContinentalMargint-scaled.jpg',
        'site_map_url': 'https://s3.us-west-2.amazonaws.com/media.ooica.net/wp-content/uploads/2021/01/28232704/Southern-Hydrate-Map.png',
    },
)
REGIONAL_MAP = 'https://app.interactiveoceans.washington.edu/map'
REGIONAL_GRAPHIC = 'https://oceanobservatories.org/wp-content/uploads/2023/09/OOI_Map_Cabled_Array-OPTIMIZED.png'
OOI_CREDIT = ('Ocean Observatories Initiative / Woods Hole Oceanographic Institution '
              'OOI Program Office / University of Washington; supported by the U.S. '
              'National Science Foundation, Cooperative Agreement 2244833')
OOI_ACKNOWLEDGMENT = (
    'This material is based upon work supported by the Ocean Observatories Initiative '
    '(OOI), a major facility fully funded by the US National Science Foundation under '
    'Cooperative Agreement No. 2244833, and the Woods Hole Oceanographic Institution '
    'OOI Program Office.'
)


def about_html(credits=OOI_CREDIT, acknowledgments=OOI_ACKNOWLEDGMENT):
    paragraphs = OVERVIEW.split('\n\n')
    parts = ['<h2>A window into the abyss.</h2>', *(f'<p>{escape(p)}</p>' for p in paragraphs),
             '<h2>Where are the cameras?</h2>',
             '<p>Three camera views, two research sites in the northeast Pacific. '
             'Both vent cameras are on Axial Seamount; the methane-seep camera is at '
             'Southern Hydrate Ridge. Depths are approximate.</p>',
             f'<p><a href="{REGIONAL_GRAPHIC}">Open the regional cable-network map</a> '
             '(Center for Environmental Visualization, University of Washington).</p>']
    for camera in CAMERAS:
        parts.extend([
            f'<h3 id="about-{camera["id"]}">{escape(camera["name"])}</h3>',
            f'<p><strong>{escape(camera["depth"])} below the surface.</strong> {escape(camera["description"])}</p>',
            f'<p><a href="{camera["site_url"]}">Explore this research site</a> &middot; '
            f'<a href="{camera["site_map_url"]}">Open the detailed site map</a> &middot; '
            f'<a href="{camera["array_graphic_url"]}">See the array illustration</a> &middot; '
            f'<a href="{camera["map_url"]}">{camera["map_label"]}</a></p>',
        ])
    parts.extend([
        f'<p><a href="{REGIONAL_MAP}">Explore the University of Washington interactive observatory map</a></p>',
        '<p>Maps, diagrams and site photographs remain on their official OOI and '
        'University of Washington pages, with their original captions and credits. '
        'Site maps: M. Elend, University of Washington; deployment dates are shown '
        'in the source captions.</p>',
        '<h3>Made possible by open ocean science</h3>',
        f'<p>{escape(credits)}</p><p>{escape(acknowledgments)}</p>',
        '<p><a href="https://oceanobservatories.org/how-to-use-acknowledge-and-cite-data/">'
        'OOI data acknowledgment and reuse terms</a>. Abyss is an independent recipe; '
        'source credit does not imply endorsement by OOI, NSF, WHOI or UW. '
        'For ambient viewing; OOI data are not for operational or decision-making use.</p>',
        '<p><a href="https://github.com/nikokoren/abyss/issues">Help, feedback and camera suggestions</a></p>',
    ])
    return '\n'.join(parts)
