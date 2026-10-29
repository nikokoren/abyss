"""Shared public-recipe introduction and camera geography."""
from html import escape
import re


SUMMARY = 'A window into the deep ocean'
HEADLINE = 'A window into the abyss.'
INTRO = 'Turn your TRMNL into your personal window into the deep ocean.'
OVERVIEW = (
    'Turn your TRMNL into your personal window into the deep ocean. Abyss lets you '
    'peek into a fascinating corner of our planet: the deep Pacific. '
    'Look into hydrothermal vent habitats on Axial Seamount, an active underwater volcano, '
    'a methane seep at Southern Hydrate Ridge, and the Oregon Offshore seafloor. These are real research '
    'camera images from places most of us will never visit.\n\n'
    'This window is made possible by public investment in science. The U.S. National '
    'Science Foundation funds the Ocean Observatories Initiative, whose Regional '
    'Cabled Array connects deep-ocean instruments to shore through a 900-kilometre '
    'network of power and data cables. '
    'Scientists, engineers and research crews keep this observatory running, '
    'and open data lets the rest of us look in, right from your TRMNL.\n\n'
    'Abyss selects stills from these cameras\' periodic recordings and snapshots. '
    'Cycle through all four cameras, choose a few favourites, or settle into one. '
    'The default 15-minute refresh rotates your selected views. Images are processed '
    'every three hours, and a camera\'s last good image stays on display when it cannot '
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
    {
        'id': 'ooi-oregon-offshore', 'name': 'Oregon Offshore: seafloor',
        'depth': 'about 580 m',
        'description': ('On the continental slope off Oregon, the CAMDSB106 camera looks '
                        'across the seabed from the Oregon Offshore benthic platform. '
                        'Fish and small seabed animals appear in its periodic snapshots.'),
        'site_url': 'https://interactiveoceans.washington.edu/research-sites/oregon-offshore/',
        'map_url': 'https://oceanobservatories.org/array/cabled-continental-margin-array/',
        'map_label': 'OOI continental-margin maps and diagrams',
        'array_graphic_url': 'https://oceanobservatories.org/wp-content/uploads/2020/10/CEV-OOI-CabledArray-ContinentalMargint-scaled.jpg',
    },
)

def camera_options(options):
    """Match published camera choices to the names and order in About."""
    names = {c['id']: c['name'] for c in CAMERAS}
    order = {c['id']: i for i, c in enumerate(CAMERAS)}
    return sorted((dict(o, label=names.get(o['value'], o['label'])) for o in options),
                  key=lambda o: order.get(o['value'], len(order)))


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
    introduction, science, viewing = OVERVIEW.split('\n\n')
    parts = [
        '<h2>A window into the abyss.</h2>',
        f'<p>{escape(introduction)}</p>',
        '<h3>Choose your view</h3>',
        f'<p>{escape(viewing)}</p>',
        '<h3>Where are the cameras?</h3>',
        '<p>Four camera views, three research sites in the northeast Pacific. '
        'Both vent cameras are on Axial Seamount; the methane-seep camera is at '
        'Southern Hydrate Ridge, and the seafloor camera is at Oregon Offshore. '
        'Depths are approximate.</p>',
    ]
    for camera in CAMERAS:
        links = [f'<a href="{camera["site_url"]}">Explore the research site</a>']
        if camera.get('site_map_url'):
            links.append(f'<a href="{camera["site_map_url"]}">Detailed site map</a>')
        parts.extend([
            f'<h3 id="about-{camera["id"]}">{escape(camera["name"])}</h3>',
            f'<p><strong>{escape(camera["depth"])} below the surface.</strong> '
            f'{escape(camera["description"])}</p>',
            '<p>' + ' &middot; '.join(links) + '</p>',
        ])
    parts.extend([
        '<h3>Explore the maps</h3>',
        '<ul>',
        f'<li><a href="{REGIONAL_GRAPHIC}">Regional cable-network map</a> '
        '(Center for Environmental Visualization, University of Washington).</li>',
        f'<li><a href="{REGIONAL_MAP}">Interactive observatory map</a> '
        '(University of Washington).</li>',
    ])
    arrays = dict.fromkeys((c['map_url'], c['map_label'], c['array_graphic_url']) for c in CAMERAS)
    for map_url, label, graphic in arrays:
        parts.append(f'<li><a href="{map_url}">{label}</a> &middot; '
                     f'<a href="{graphic}">Array illustration</a></li>')
    parts.extend([
        '</ul>',
        '<p>Maps, diagrams and site photographs remain on their official OOI and '
        'University of Washington pages, with their original captions and credits. '
        'Site maps: M. Elend, University of Washington; deployment dates are shown '
        'in the source captions.</p>',
        '<h3>Made possible by open ocean science</h3>',
        f'<p>{escape(science)}</p>',
        f'<p>{escape(credits)}</p><p>{escape(acknowledgments)}</p>',
        '<p><a href="https://oceanobservatories.org/how-to-use-acknowledge-and-cite-data/">'
        'OOI data acknowledgment and reuse terms</a>. Abyss is an independent recipe; '
        'source credit does not imply endorsement by OOI, NSF, WHOI or UW. '
        'For ambient viewing; OOI data are not for operational or decision-making use.</p>',
        '<p><a href="https://github.com/nikokoren/abyss/issues">Help, feedback and camera suggestions</a></p>',
    ])
    return '\n'.join(parts)


def about_trmnl_html(credits=OOI_CREDIT, acknowledgments=OOI_ACKNOWLEDGMENT):
    """Use explicit breaks because TRMNL's About field removes block tags."""
    html = about_html(credits, acknowledgments)
    html = re.sub(r'<h[23][^>]*>(.*?)</h[23]>', r'<strong>\1</strong><br>', html)
    html = html.replace('<p>', '').replace('</p>', '<br><br>')
    html = html.replace('<ul>', '').replace('</ul>', '<br>')
    html = html.replace('<li>', '').replace('</li>', '<br>')
    html = re.sub(r'(?:<br>\s*){3,}', '<br><br>\n', html)
    return html.rstrip().removesuffix('<br><br>').removesuffix('<br>')


def about_field_yaml():
    """Replacement for the owner's existing TRMNL author_bio custom field."""
    lines = ['- keyname: author_bio', '  field_type: author_bio',
             '  name: About This Plugin', '  description: |']
    lines.extend('    ' + line if line else '' for line in about_trmnl_html().splitlines())
    lines.extend(['  category: "discovery,education"',
                  '  email_address: "isarworks@gmail.com"'])
    return '\n'.join(lines) + '\n'
