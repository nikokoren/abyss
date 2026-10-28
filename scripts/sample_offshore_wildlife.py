"""Collect an unranked, time-spread Offshore sample for visual wildlife review."""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from abyss.adapters import directory_recordings
from abyss.about import OOI_ACKNOWLEDGMENT
from abyss.imaging import quality, render_for_source
from abyss.network import TransferBudget, classify_failure
from abyss.registry import load
from abyss.stills import download_image

UTC = timezone.utc
DAYS, HOURS, MAX_SKEW = 7, (0, 4, 8, 12, 16, 20), 30 * 60
BUDGET = 512 * 1024 * 1024


def select_slots(records, day, cutoff):
    """Nearest completed capture to each fixed clock slot; never rank image content."""
    eligible = [r for r in records if datetime.fromisoformat(r['recorded_at']) <= cutoff]
    selected = []
    for hour in HOURS:
        target = day.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target > cutoff:
            continue
        candidates = [r for r in eligible if abs((datetime.fromisoformat(r['recorded_at']) - target).total_seconds()) <= MAX_SKEW]
        record = min(candidates, key=lambda r: (abs((datetime.fromisoformat(r['recorded_at']) - target).total_seconds()),
                                               r['recorded_at'], r['url']), default=None)
        selected.append({'target_time': target.isoformat(), 'recording': record})
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    source = next(s for s in load('sources.json') if s['id'] == 'ooi-oregon-offshore')
    validation = source['validation']
    if (source['adapter'] != 'ooi_image_directory' or not validation.get('terms_reviewed_at')
            or validation.get('rights_status') != 'approved_attributed_derived_stills'):
        raise ValueError('Sampling requires an explicitly rights-reviewed OOI snapshot source')
    cutoff = now - timedelta(minutes=source.get('completion_delay_minutes', 5))
    report = {'schema_version': 1, 'source_id': source['id'], 'camera': source['name'],
              'checked_at': now.isoformat(), 'commit': os.environ.get('GITHUB_SHA'),
              'run_url': f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
                         if os.environ.get('GITHUB_RUN_ID') else None,
              'sampling': {'calendar_days_including_today': DAYS, 'target_hours_utc': list(HOURS),
                           'maximum_distance_from_slot_seconds': MAX_SKEW,
                           'max_bytes': BUDGET, 'selection_uses_quality_or_wildlife': False,
                           'completion_cutoff': cutoff.isoformat()},
              'scope': 'Descriptive visual review of visible animals, not a population or visit-rate estimate. No preference labels generated; no camera enabled.',
              **{k: source[k] for k in ('attribution', 'acknowledgment', 'license_url', 'data_doi')},
              'days': [], 'samples': []}
    slots = []
    for ago in range(DAYS - 1, -1, -1):
        day = (now - timedelta(days=ago)).replace(hour=0, minute=0, second=0, microsecond=0)
        entry = {'date': day.date().isoformat()}
        report['days'].append(entry)
        try:
            records = directory_recordings(source, day)
            entry['listed_snapshots'] = len(records)
            slots.extend(select_slots(records, day, cutoff))
        except Exception as exc:
            entry['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:1000]}
            slots.extend(select_slots([], day, cutoff))
    budget = TransferBudget(BUDGET)
    with tempfile.TemporaryDirectory() as temporary:
        for index, slot in enumerate(slots):
            sample = {'id': f'{index + 1:02d}', **slot}
            report['samples'].append(sample)
            if slot['recording'] is None:
                sample['status'] = 'missing_capture'
                continue
            try:
                path, details = download_image(slot['recording'], source, temporary, budget, index)
                with Image.open(path) as image:
                    sample.update(details, quality=quality(image), status='decoded')
                    # A review derivative only: production still preserves source RGB pixels.
                    preview = render_for_source(image, source, method='native')
                    preview.thumbnail((2560, 2100))
                    name = sample['id'] + '-colour.jpg'
                    preview.save(args.output / name, quality=93, optimize=True)
                    sample['preview'] = name
                    sample['preview_size'] = list(preview.size)
                path.unlink()
            except Exception as exc:
                sample['status'] = 'retrieval_failed'
                sample['failure'] = {'category': classify_failure(exc), 'message': str(exc)[:1000]}
            print(sample['id'], slot['target_time'], sample['status'], budget.used, flush=True)
    report.update(bytes_downloaded=budget.used, requests=budget.requests,
                  targeted_slots=len(slots), decoded_count=sum(s['status'] == 'decoded' for s in report['samples']))
    fragments = ['<!doctype html><html lang="en"><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<title>Offshore wildlife sample</title>'
                 '<style>body{font:16px system-ui;max-width:1400px;margin:auto;padding:24px}img{display:block;max-width:100%;height:auto}figure{margin:32px 0}p{line-height:1.5}</style>'
                 '<h1>How often are animals visible?</h1><p>Oregon Offshore, about 580 m deep. '
                 'Seven calendar days, six fixed time slots per day, with no quality or wildlife filtering. '
                 'Images are original-colour review derivatives; click the original link for source resolution. '
                 'Repeated sightings can be the same resident animal.</p>',
                 f'<p>Decoded {report["decoded_count"]} of {len(slots)} target slots. '
                 'Missing or failed captures must not count as animal-free frames.</p>']
    font = ImageFont.load_default(size=20)
    for day in report['days']:
        samples = [s for s in report['samples'] if s['target_time'].startswith(day['date'])]
        sheet = Image.new('RGB', (1440, 1830), 'white')
        draw = ImageDraw.Draw(sheet)
        for cell, sample in enumerate(samples):
            x, y = cell % 2 * 720, cell // 2 * 610
            draw.text((x + 10, y + 565), sample['id'] + ' / ' + sample['target_time'], font=font, fill='black')
            if sample.get('preview'):
                with Image.open(args.output / sample['preview']) as image:
                    image.thumbnail((710, 550))
                    sheet.paste(image, (x, y))
                stamp = escape(sample['recording']['recorded_at'])
                original = escape(sample['recording']['url'], quote=True)
                fragments.append(f'<figure id="sample-{sample["id"]}"><h2>Sample {sample["id"]} / {stamp}</h2>'
                                 f'<img src="{sample["preview"]}" alt="Offshore sample {sample["id"]}">'
                                 f'<figcaption><a href="{original}">Open original full-resolution snapshot</a></figcaption></figure>')
            else:
                draw.text((x + 40, y + 200), sample['status'], font=font, fill='black')
        name = 'contact-' + day['date'] + '.jpg'
        sheet.save(args.output / name, quality=93, optimize=True)
        day['contact_sheet'] = name
    fragments.append('<footer><p>' + escape(source['attribution']) + '</p><p>' +
                     escape(OOI_ACKNOWLEDGMENT) + '</p><p><a href="' + escape(source['license_url'], quote=True) +
                     '">OOI reuse terms</a>. Source credit implies no endorsement. For ambient viewing; '
                     'not for operational or decision-making use.</p></footer></html>')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'index.html').write_text('\n'.join(fragments), encoding='utf-8')
    if not report['decoded_count']:
        raise SystemExit('No sampled images decoded; inspect retrieval and directory failures')


if __name__ == '__main__':
    main()
