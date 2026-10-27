import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from test_abyss import FakeOpener, args, source
from abyss.adapters import directory_recordings, discover_many
from abyss.cadence import observe
from abyss.network import RangeVideo, RetrievalError, TransferBudget
from abyss.pipeline import run
from abyss.publication import read_json
from abyss.search import search

UTC = timezone.utc


def recording(hour, day=1):
    return {'url': f'https://camera.example/{day:02}-{hour:02}.mp4',
            'recorded_at': f'2026-01-{day:02}T{hour:02}:00:00+00:00'}


class DiscoveryTests(unittest.TestCase):
    def test_recent_recordings_cross_midnight_and_ignore_incomplete(self):
        s = source(); s.update(adapter='ooi_directory',base_url='https://camera.example/files/',lookback_days=2)
        def pages(url, hosts):
            if '/01/02/' in url:
                return b'<a href="CAMHDA301-20260102T003000.mp4">recent</a><a href="CAMHDA301-20260102T000000.mp4">eligible</a>'
            return b'<a href="/files/2026/01/01/CAMHDA301-20260101T230000.mp4">absolute path</a><a href="https://camera.example/files/2026/01/01/CAMHDA301-20260101T220000.mp4">full URL</a><a href="https://evil.example/CAMHDA301-20260101T235900.mp4">bad</a>'
        with patch('abyss.adapters.read_small',side_effect=pages):
            result=discover_many(s,datetime(2026,1,2,1,tzinfo=UTC),limit=3)
        self.assertEqual([r['recorded_at'] for r in result], [
            '2026-01-02T00:00:00+00:00','2026-01-01T23:00:00+00:00','2026-01-01T22:00:00+00:00'])


class CadenceTests(unittest.TestCase):
    def test_baseline_never_claims_publication_delay(self):
        with patch('abyss.cadence.directory_recordings',return_value=[recording(6),recording(9),recording(12)]):
            report,state=observe(source(),now=datetime(2026,1,1,13,tzinfo=UTC),days=1)
        self.assertEqual(report['recording_intervals_seconds']['median'],10800)
        self.assertEqual(report['baseline_recordings'],3)
        self.assertEqual(report['publication_delay_observations'],0)
        self.assertFalse(any('appeared_between' in r for r in state['records'].values()))

    def test_two_observations_bracket_appearance_and_preserve_state(self):
        before=datetime(2026,1,1,12,10,tzinfo=UTC)
        with patch('abyss.cadence.directory_recordings',return_value=[recording(9)]):
            _,state=observe(source(),now=before,days=1)
        original=copy.deepcopy(state)
        with patch('abyss.cadence.directory_recordings',return_value=[recording(9),recording(12)]):
            report,after=observe(source(),state,now=before+timedelta(hours=1),days=1)
        self.assertEqual(state,original)
        self.assertEqual(report['new_recordings_since_prior_coverage'],1)
        self.assertEqual(report['publication_delay_observations'],1)
        self.assertEqual(report['new_appearances'][0]['nominal_publication_delay_bounds_seconds'],[600,4200])
        self.assertEqual(after['records'][recording(9)['url']]['first_seen_at'],before.isoformat())

    def test_new_date_without_previous_coverage_is_baseline(self):
        prior={'records':{},'coverage':{'2026-01-01':'2026-01-01T23:00:00+00:00'}}
        with patch('abyss.cadence.directory_recordings',return_value=[recording(0,day=2)]):
            report,_=observe(source(),prior,now=datetime(2026,1,2,1,tzinfo=UTC),days=1)
        self.assertEqual(report['publication_delay_observations'],0)
        self.assertEqual(report['baseline_recordings'],1)

    def test_directory_failure_is_not_empty_success(self):
        with patch('abyss.cadence.directory_recordings',side_effect=OSError('network blocked')):
            with self.assertRaisesRegex(RuntimeError,'No archive directories'): observe(source())


class SearchTests(unittest.TestCase):
    def test_shared_budget_cannot_reset_per_recording(self):
        budget=TransferBudget(300_000)
        fake=FakeOpener(b'x'*1_000_000)
        with patch('abyss.network.opener',return_value=fake):
            first=RangeVideo('https://camera.example/first',['camera.example'],1_000_000,budget=budget)
            first.block(0)
            second=RangeVideo('https://camera.example/second',['camera.example'],1_000_000,budget=budget)
            with self.assertRaisesRegex(RetrievalError,'budget'): second.block(0)
        self.assertLessEqual(budget.used,budget.limit)
        self.assertEqual(budget.used,262146)

    def test_refinement_can_find_better_moment_in_older_recording(self):
        calls=[]
        def frames(url,directory,positions,**kwargs):
            calls.append((url,list(positions),kwargs['prefix']))
            result=[]
            for i,seconds in enumerate(positions):
                # Old recording wins globally; its fine neighborhood is strongest.
                score=220 if url.endswith('old.mp4') and 'fine' in kwargs['prefix'] else (180 if url.endswith('old.mp4') else 120)
                p=Path(directory)/f'{kwargs["prefix"]}-{i}.png'
                Image.new('L',(100,80),score).save(p)
                result.append((seconds,p))
            return result,{'extraction_errors':[]}
        def metric(image,*unused):
            score=image.getpixel((0,0))/255
            return {'score':score,'fingerprint':'0'*256}
        class Bridge:
            error=None;bytes_read=0;requests=0;total=1000
            def __init__(self,url,*unused,**kwargs):self.url=url
            def bridge(self):
                import contextlib
                return contextlib.nullcontext(self.url)
        with tempfile.TemporaryDirectory() as tmp,patch('abyss.search.RangeVideo',Bridge),patch('abyss.search.probe',return_value=(120,'h264')),patch('abyss.search.extract_positions',side_effect=frames),patch('abyss.search.quality',side_effect=metric):
            a=args(tmp); a.candidates=8;a.interval=1
            records=[{'url':'https://camera.example/new.mp4','recorded_at':recording(12)['recorded_at']},
                     {'url':'https://camera.example/old.mp4','recorded_at':recording(9)['recorded_at']}]
            best,details,completed=search(source(),records,tmp,a)
            self.assertEqual(best['recording']['url'],records[1]['url'])
            self.assertEqual(best['stage'],'fine')
            self.assertEqual(details['coarse_extracted'],8)
            self.assertEqual(details['fine_extracted'],4)
            self.assertEqual(len(completed),2)
            coarse={url:set(p) for url,p,prefix in calls if 'coarse' in prefix}
            for url,positions,prefix in calls:
                if 'fine' in prefix:self.assertTrue(set(positions).isdisjoint(coarse[url]))

    def test_blank_scenes_do_not_waste_refinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=args(tmp,'dummy');a.candidates=8
            def frames(url,directory,positions,**kwargs):
                p=Path(directory)/'blank.png';Image.new('L',(100,80),0).save(p)
                return [(p0,p) for p0 in positions],{'extraction_errors':[]}
            with patch('abyss.search.probe',return_value=(120,'h264')),patch('abyss.search.extract_positions',side_effect=frames):
                _,details,_=search(source(),[recording(12)],tmp,a)
            self.assertEqual(details['fine_extracted'],0)

    def test_one_broken_recording_does_not_discard_good_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=args(tmp,'dummy')
            p=Path(tmp)/'good.png'
            import numpy as np
            Image.fromarray(np.random.default_rng(1).integers(20,230,(80,100),dtype='uint8')).save(p)
            with patch('abyss.search.probe',side_effect=[OSError('broken'),(120,'h264')]),patch('abyss.search.extract_positions',return_value=([(30,p)],{'extraction_errors':[]})):
                best,details,completed=search(source(),[recording(12),recording(9)],tmp,a)
            self.assertEqual(best['recording']['url'],recording(9)['url'])
            self.assertFalse(details['search_complete'])
            self.assertNotIn(recording(12)['url'],completed)

    def test_pipeline_searches_unseen_older_recordings_and_skips_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=args(tmp);a.recordings=3
            s=source();records=[recording(12),recording(9),recording(6)]
            def winner(source,recordings,directory,arguments,history):
                self.assertEqual(recordings,records)
                p=Path(directory)/'selected.png';Image.new('L',(800,448),100).save(p)
                return {'recording':records[1],'seconds':30,'path':p,'quality':{'score':.8,'fingerprint':'0'*256}}, {'recordings':[]},[r['url'] for r in records]
            with patch('abyss.pipeline.discover_many',return_value=records),patch('abyss.pipeline.search',side_effect=winner) as searcher:
                self.assertEqual(run([s],a)[s['id']],'published')
                self.assertEqual(run([s],a)[s['id']],'unchanged')
                self.assertEqual(searcher.call_count,1)
            latest=read_json(Path(tmp)/'public/sources/test-camera/latest.json',{})
            self.assertEqual(latest['original_url'],records[1]['url'])
            self.assertEqual(latest['captured_at'],'2026-01-01T09:00:30+00:00')


if __name__=='__main__':unittest.main()
