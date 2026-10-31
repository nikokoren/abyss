"""Native TRMNL serverless transform. No network requests or extra dependencies."""
import hashlib
import json
import math
import time


def selected_ids(value):
    """Native multi-selects, legacy single values and CSV/JSON array strings."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            parsed = value.split(',')
        value = parsed.split(',') if isinstance(parsed, str) else parsed
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        return []
    return list(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))


def positive_number(value, default):
    try:
        value = float(value)
        return value if value > 0 and math.isfinite(value) else default
    except (TypeError, ValueError, OverflowError):
        return default


def run(input):
    if not isinstance(input, dict) or not isinstance(input.get('sources'), dict):
        # TRMNL retains its previous good transform output when a transform fails.
        raise ValueError('Abyss catalog is unavailable; keep the last rendered image')
    trmnl = input.get('trmnl') or {}
    settings = trmnl.get('plugin_settings') or {}
    fields = settings.get('custom_fields_values') or {}
    # An explicitly empty new selector means all, even if a legacy value exists.
    raw = fields.get('source_ids') if 'source_ids' in fields else fields.get('source_id')
    selected = selected_ids(raw)
    show_qr = fields.get('show_qr') is True or str(fields.get('show_qr', '')).strip().lower() in {'true', '1', 'yes', 'on'}
    sources = input['sources']
    order = input.get('rotation_order') or [o.get('value') for o in input.get('options', [])]
    order = list(dict.fromkeys([*order, *sources.keys()]))
    pool = [key for key in order if key in sources and isinstance(sources[key], dict)
            and sources[key].get('image_url') and (not selected or key in selected)]
    # Availability is intentionally not a filter: an offline feed keeps its slot
    # and its latest published good image. Withheld sources are absent upstream.
    state = dict(trmnl.get('state') or {})
    saved = state.get('abyss') or {}
    devices = dict(saved.get('devices') or {}) if isinstance(saved, dict) else {}
    device = trmnl.get('device') or {}
    key = str(device.get('friendly_id') or 'default')[:80]
    previous = devices.get(key) or {}
    if not isinstance(previous, dict):
        previous = {}
    refresh_seconds = positive_number(settings.get('refresh_interval_minutes'), 15) * 60
    interval = max(refresh_seconds, positive_number(device.get('refresh_interval_seconds'), refresh_seconds))
    fetched = settings.get('data_fetched_utc')
    clock = positive_number(fetched, time.time())
    cycle = int(clock // interval)
    signature = hashlib.sha256(json.dumps(pool).encode()).hexdigest()[:16]
    last = previous.get('source_id')
    if not pool:
        camera = None
        position = None
    else:
        if previous.get('pool') == signature and last in pool:
            position = pool.index(last)
            if previous.get('cycle') != cycle:
                position = (position + 1) % len(pool)
        else:
            position = 0
        current = pool[position]
        # Always read the current catalog entry, never a camera cached in state.
        camera = sources[current]
        devices.pop(key, None)
        devices[key] = {'pool': signature, 'cycle': cycle, 'source_id': current}
        devices = dict(list(devices.items())[-16:])
        state['abyss'] = {'devices': devices}
    return {'abyss_ready': True, 'current_camera': camera, 'show_qr': show_qr,
            'rotation': {'feed_ids': pool, 'index': position, 'interval_seconds': interval,
                         'mode': 'selected' if selected else 'all'},
            'trmnl_state': state}
