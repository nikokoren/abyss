"""Measure filename intervals and bracket new-file appearances over observations."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median
from .adapters import directory_recordings
from .network import classify_failure


def observe(source, previous=None, now=None, days=3):
    previous = previous or {}
    fixed_now = now is not None
    now = now or datetime.now(timezone.utc)
    if not 1 <= days <= 14:
        raise ValueError('Observation days must be 1..14')
    records, coverage, errors, observed = {}, {}, [], {}
    for offset in range(days):
        day = now - timedelta(days=offset)
        date = day.date().isoformat()
        try:
            request_start = now if fixed_now else datetime.now(timezone.utc)
            listed = directory_recordings(source, day)
            seen_at = now if fixed_now else datetime.now(timezone.utc)
            coverage[date] = request_start.isoformat()
            observed[date] = seen_at.isoformat()
            for record in listed:
                if record['recorded_at'] <= seen_at.isoformat():
                    records[record['url']] = record
        except Exception as exc:
            errors.append({'date': date, 'category': classify_failure(exc), 'error': str(exc)[:500]})
    if not coverage:
        failure = RuntimeError('No archive directories accessible: ' + '; '.join(e['error'] for e in errors))
        categories = {e['category'] for e in errors}
        failure.failure_category = next(iter(categories)) if len(categories) == 1 else 'mixed_directory_failures'
        raise failure
    now = now if fixed_now else datetime.now(timezone.utc)
    known = {k: dict(v) for k, v in previous.get('records', {}).items()}
    new, baseline = [], []
    for url, record in records.items():
        date = record['recorded_at'][:10]
        seen_at = observed[date]
        if url not in known:
            absence = previous.get('coverage', {}).get(date)
            entry = {**record, 'first_seen_at': seen_at, 'baseline': absence is None}
            if absence:
                start = datetime.fromisoformat(record['recorded_at'])
                # A bounded observation window, not an exact publication time.
                entry['appeared_between'] = [absence, seen_at]
                entry['nominal_publication_delay_bounds_seconds'] = [
                    max(0, (datetime.fromisoformat(absence) - start).total_seconds()),
                    max(0, (datetime.fromisoformat(seen_at) - start).total_seconds())]
                new.append(entry)
            else:
                baseline.append(entry)
            known[url] = entry
        known[url]['last_seen_at'] = seen_at
    cutoff = (now - timedelta(days=7)).isoformat()
    known = {k: v for k, v in known.items() if v['last_seen_at'] >= cutoff}
    stamps = sorted({r['recorded_at'] for r in records.values()})
    gaps = [(datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()
            for a, b in zip(stamps, stamps[1:])]
    observed_delays = [r['nominal_publication_delay_bounds_seconds'] for r in known.values()
                       if 'nominal_publication_delay_bounds_seconds' in r]
    summary = {'schema_version': 1, 'source_id': source['id'], 'checked_at': now.isoformat(),
               'status': 'partial' if errors else 'observed',
               'timestamp_basis': 'Filename parsed as UTC; source timezone not independently confirmed',
               'directory_dates_checked': sorted(coverage), 'directory_errors': errors,
               'recordings_listed': len(records), 'new_recordings_since_prior_coverage': len(new),
               'baseline_recordings': len(baseline),
               'recording_intervals_seconds': {'samples': len(gaps),
                    'median': median(gaps) if gaps else None, 'minimum': min(gaps) if gaps else None,
                    'maximum': max(gaps) if gaps else None,
                    'common': [{'seconds': value, 'count': count} for value, count in Counter(gaps).most_common(5)]},
               'latest_nominal_recording_at': stamps[-1] if stamps else None,
               'publication_delay_observations': len(observed_delays),
               'new_appearances': new,
               'publication_delay_note': 'Baseline files have unknown publication time. Delay bounds require prior successful coverage of that date; filename timezone remains an assumption.'}
    observations = (previous.get('observations', []) + [{
        'checked_at': now.isoformat(), 'recordings_listed': len(records), 'new_recordings': len(new),
        'coverage': sorted(coverage)}])[-168:]
    state = {'schema_version': 1, 'source_id': source['id'], 'records': known,
             'coverage': {k: v for k, v in {**previous.get('coverage', {}), **coverage}.items() if k >= cutoff[:10]}, 'observations': observations}
    return summary, state
