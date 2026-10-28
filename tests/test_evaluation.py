"""Fresh recordings and frozen pre-feedback predictions prevent evaluation leakage."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from abyss.adapters import NoFreshRecordings, discover_many
from abyss.evaluation import feedback_context, prospective_report
from abyss.publication import atomic_json
from abyss.review import review_inputs
from test_abyss import source


class FreshDiscoveryTests(unittest.TestCase):
    def camera(self):
        value = source(); value.update(adapter='ooi_directory', base_url='https://camera.example/files/', lookback_days=2)
        return value

    def record(self, hour):
        return {'url': f'https://camera.example/{hour}.mp4', 'recorded_at': f'2026-01-01T{hour:02}:00:00+00:00'}

    def test_review_does_not_reuse_training_recordings_or_older_sessions(self):
        records = [self.record(n) for n in (15, 12, 9, 6)]
        with patch('abyss.adapters.directory_recordings', return_value=records):
            fresh = discover_many(self.camera(), datetime(2026, 1, 1, 17, tzinfo=timezone.utc), limit=3,
                exclude_urls=[records[1]['url']], recorded_after=records[2]['recorded_at'])
        self.assertEqual(fresh, [records[0]])

    def test_waiting_for_fresh_is_distinct_from_network_failure(self):
        with patch('abyss.adapters.directory_recordings', return_value=[self.record(9)]):
            with self.assertRaises(NoFreshRecordings):
                discover_many(self.camera(), datetime(2026, 1, 1, 17, tzinfo=timezone.utc),
                              recorded_after=self.record(9)['recorded_at'])
        with patch('abyss.adapters.directory_recordings', side_effect=OSError('network blocked')):
            try:
                discover_many(self.camera(), datetime(2026, 1, 1, 17, tzinfo=timezone.utc),
                              recorded_after=self.record(9)['recorded_at'])
            except RuntimeError as error:
                self.assertNotIsInstance(error, NoFreshRecordings)
            else:
                self.fail('Network failure must not become an empty successful gallery')

    def test_feedback_context_uses_only_the_configured_reviewer_and_actual_reviewed_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = 'a' * 32
            atomic_json(Path(tmp) / 'batches' / (identity + '.json'), {'candidates': {
                'seen': {'source_id': 'ooi-axial', 'recording_url': 'https://camera.example/seen.mp4', 'recorded_at': '2026-01-01T09:00:00+00:00'},
                'unreviewed': {'source_id': 'ooi-axial', 'recorded_at': '2026-01-01T15:00:00+00:00'}}})
            atomic_json(Path(tmp) / 'feedback/issue-1.json', {'reviewer': 'owner', 'batch_id': identity,
                'frames': {'seen': {'recording_url': 'https://camera.example/seen.mp4'}}})
            atomic_json(Path(tmp) / 'feedback/issue-2.json', {'reviewer': 'someone-else', 'batch_id': identity,
                'frames': {'unreviewed': {'recording_url': 'https://camera.example/other.mp4'}}})
            context = feedback_context(tmp, 'owner', 'ooi-axial')
            self.assertEqual(context['recorded_after'], '2026-01-01T09:00:00+00:00')
            self.assertEqual(context['training_recording_urls'], ['https://camera.example/seen.mp4'])
            with patch('abyss.review.discover_many', return_value=[]) as discover:
                review_inputs(self.camera(), fresh_context=context)
            self.assertEqual(discover.call_args.kwargs['exclude_urls'], context['training_recording_urls'])
            self.assertEqual(discover.call_args.kwargs['recorded_after'], context['recorded_after'])


class ProspectiveTests(unittest.TestCase):
    def data(self):
        candidates = {}
        for key in ('a0', 'a1'):
            candidates[key] = {'recording_url': 'https://camera.example/new.mp4', 'quality_score': .6,
                               'selection_score': .8, 'preference_score': .9}
        for i in range(6):
            candidates[f'b{i}'] = {'recording_url': 'https://camera.example/new.mp4', 'quality_score': .8,
                                   'selection_score': .7, 'preference_score': .4}
        manifest = {'reviewer': 'owner',
                    'evaluation_context': {'eligible': True, 'model_id': 'frozen-old-model', 'training_recording_urls': []},
                    'candidates': candidates}
        doc = {'reviewer': 'owner', 'updated_at': '2026-01-02', 'issue_number': 1, 'batch_id': 'batch',
               'comparisons': [{'key': f'{a}:b{i}', 'a': a, 'b': f'b{i}', 'choice': 'a'}
                               for a in ('a0', 'a1') for i in range(6)]}
        return manifest, doc

    def test_compares_frozen_model_and_baseline_not_newly_retrained_predictions(self):
        manifest, doc = self.data()
        report = prospective_report([doc], {'batch': manifest}, 'owner')
        self.assertEqual(report['status'], 'measured')
        self.assertEqual(report['learned_accuracy'], 1)
        self.assertEqual(report['quality_baseline_accuracy'], 0)
        self.assertEqual(report['unseen_recording_count'], 1)
        self.assertEqual(report['batches'][0]['model_id'], 'frozen-old-model')

    def test_edited_choices_replace_previous_votes_and_neither_is_not_a_pairwise_win(self):
        manifest, doc = self.data()
        newer = dict(doc, updated_at='2026-01-03', issue_number=2,
                     comparisons=[dict(row, choice='b') for row in doc['comparisons']])
        report = prospective_report([doc, newer], {'batch': manifest}, 'owner')
        self.assertEqual(report['comparisons'], 12)
        self.assertEqual(report['learned_accuracy'], 0)
        self.assertEqual(report['quality_baseline_accuracy'], 1)
        newer['comparisons'] = [dict(row, choice='neither') for row in newer['comparisons']]
        self.assertEqual(prospective_report([doc, newer], {'batch': manifest}, 'owner')['status'], 'awaiting_feedback')

    def test_unqualified_or_leaked_snapshots_are_never_reported_as_validation(self):
        manifest, doc = self.data()
        for change in ({'eligible': False}, {'training_recording_urls': ['https://camera.example/new.mp4']}, {'model_id': None}):
            original = dict(manifest['evaluation_context']); manifest['evaluation_context'].update(change)
            self.assertEqual(prospective_report([doc], {'batch': manifest}, 'owner')['comparisons'], 0)
            manifest['evaluation_context'] = original

    def test_ties_count_half_and_small_samples_stay_provisional(self):
        manifest, doc = self.data()
        for candidate in manifest['candidates'].values():
            candidate['selection_score'] = .8
        doc['comparisons'] = doc['comparisons'][:2]
        report = prospective_report([doc], {'batch': manifest}, 'owner')
        self.assertEqual(report['learned_accuracy'], .5)
        self.assertEqual(report['status'], 'collecting')
