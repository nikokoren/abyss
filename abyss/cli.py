import argparse
import json
import logging
import tempfile
from pathlib import Path
from PIL import Image
from .adapters import discover
from .imaging import quality, render_for_source
from .pipeline import candidates, run, utcnow
from .publication import atomic_json
from .recipe import generate
from .registry import eligible, load


def main():
    parser = argparse.ArgumentParser(description='Underwater camera processing for TRMNL')
    parser.add_argument('--registry', default='sources.json')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('sources')
    for name in ('run', 'inspect'):
        p = sub.add_parser(name)
        p.add_argument('--source')
        p.add_argument('--output', default='output')
        p.add_argument('--base-url')
        p.add_argument('--max-bytes', type=int, default=96 * 1024 * 1024)
        p.add_argument('--candidates', type=int, default=10, help='Maximum frames per recording including refinement')
        p.add_argument('--recordings', type=int, default=3)
        p.add_argument('--preference-model', default='preferences/model.json')
        p.add_argument('--coarse-candidates', type=int, default=6)
        p.add_argument('--refine-candidates', type=int, default=6, help='Total extra frame seeks across the search')
        p.add_argument('--refine-windows', type=int, default=3)
        p.add_argument('--interval', type=float, default=60)
        p.add_argument('--width', type=int, default=800)
        p.add_argument('--height', type=int, default=448)
        p.add_argument('--method', choices=['native', 'ordered', 'floyd', 'threshold', 'grayscale'], default='native',
                       help='native preserves source resolution and color; TRMNL performs device rendering')
        p.add_argument('--contrast', type=float, default=1.25)
        p.add_argument('--brightness', type=float, default=1.03)
        p.add_argument('--force', action='store_true')
        p.add_argument('--local-video', help='Explicit fixture mode only; never validates a remote source')
        p.add_argument('--recorded-at', help='Optional timezone-qualified fixture recording time')
    recipe = sub.add_parser('recipe')
    recipe.add_argument('--output', default='output')
    recipe.add_argument('--base-url', required=True)
    recipe.add_argument('--destination', default='output/recipe/settings.yml')
    retention = sub.add_parser('retain')
    retention.add_argument('--output', default='output')
    retention.add_argument('--base-url', required=True)
    retention.add_argument('--max-bytes', type=int, default=640 * 1024 * 1024)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        if args.command == 'recipe':
            generate(args.output, args.base_url, args.destination)
            return
        if args.command == 'retain':
            from .retention import retain
            print(json.dumps(retain(args.output, args.base_url, max_bytes=args.max_bytes), indent=2))
            return
        sources = load(args.registry)
        if args.command == 'sources':
            print(json.dumps([{**s, 'recipe_eligible': eligible(s)} for s in sources], indent=2))
        elif args.command == 'inspect':
            matching = [s for s in sources if s['id'] == args.source]
            if not matching:
                parser.error('inspect requires a known --source ID')
            source = matching[0]
            if not source.get('adapter'):
                parser.error('Source has no retrieval adapter')
            recording = ({'url': 'local-fixture', 'recorded_at': args.recorded_at} if args.local_video else discover(source))
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as tmp:
                frames, diagnostics = candidates(source, recording, tmp, args)
                scores = []
                for i, (seconds, frame) in enumerate(frames):
                    with Image.open(frame) as image:
                        scores.append({'frame_seconds': seconds, **quality(image)})
                        for method in ('ordered', 'floyd', 'threshold', 'grayscale'):
                            render_for_source(image, source, args.width, args.height, method).save(output / f'{i:02}-{method}.png')
                atomic_json(output / 'inspection.json', {'source_id': source['id'], 'checked_at': utcnow(),
                            'recording': recording, 'diagnostics': diagnostics, 'scores': scores,
                            'fixture': bool(args.local_video), 'note': 'Technical inspection only; reuse terms require separate review'})
            print(json.dumps(diagnostics, indent=2))
        else:
            if not args.base_url:
                parser.error('run requires --base-url for the public image endpoint')
            from urllib.parse import urlsplit
            parsed = urlsplit(args.base_url)
            if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
                parser.error('--base-url must be an HTTPS URL without credentials, query or fragment')
            if args.local_video and not all(s.get('fixture') for s in sources if eligible(s)):
                parser.error('Local video requires a separate fixture-only registry; cannot impersonate a real source')
            results = run(sources, args)
            if not results or any(v == 'failed' for v in results.values()):
                raise SystemExit(1)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
