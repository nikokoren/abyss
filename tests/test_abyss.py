import argparse
import copy
import io
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from abyss.adapters import discover
from abyss.imaging import fingerprint, quality, render, render_for_source, similarity
from abyss.network import RangeVideo, RetrievalError, check_url
from abyss.pipeline import run
from abyss.publication import atomic_json, catalog, read_json
from abyss.recipe import generate
from abyss.registry import eligible, load
from abyss.video import extract


def source():
    return {'id':'test-camera','name':'Test camera','description':'Synthetic test', 'type':'archive',
            'status':'validated','adapter':'direct','allowed_hosts':['camera.example'],
            'video_url':'https://camera.example/test.mp4','recorded_at':'2026-01-01T10:00:00+00:00',
            'attribution':'Test fixture','attribution_url':'https://camera.example/',
            'license':'Test-only','license_url':'https://camera.example/terms',
            'validation':{'retrieval_at':'2026-01-01','terms_reviewed_at':'2026-01-01','evidence':'fixture'},
            'scoring':{'min_score':.10},'fixture':True}


def args(root, video=None):
    return argparse.Namespace(output=str(root),base_url='https://site.example/abyss',source=None,force=False,
                              local_video=str(video) if video else None,recorded_at='2026-01-01T10:00:00+00:00',
                              max_bytes=4*1024*1024,candidates=3,interval=1,width=800,height=448,
                              method='ordered',contrast=1.25,brightness=1.03)


class RegistryTests(unittest.TestCase):
    def test_unverified_sources_not_selectable(self):
        sources = load('sources.json')
        self.assertTrue(eligible(sources[0]))
        for item in sources:
            if item['status'] != 'validated':
                self.assertFalse(eligible(item))
            else:
                self.assertTrue(eligible(item))
        s = source()
        self.assertTrue(eligible(s))
        s['validation']['terms_reviewed_at'] = None
        self.assertFalse(eligible(s))

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'sources.json'
            p.write_text(json.dumps({'schema_version':1,'sources':[source(),source()]}))
            with self.assertRaises(ValueError): load(p)

    def test_discovery_and_timestamp(self):
        s = source()
        s.update(adapter='ooi_directory',base_url='https://camera.example/files/',lookback_days=1)
        listing = b'<a href="CAMHDA301-20260101T100000.mp4">good</a><a href="CAMHDA301-20260101T115900.mp4">incomplete</a><a href="https://evil.test/x.mp4">bad</a>'
        with patch('abyss.adapters.read_small',return_value=listing):
            result = discover(s,datetime(2026,1,1,12,tzinfo=timezone.utc))
        self.assertEqual(result['url'],'https://camera.example/files/2026/01/01/CAMHDA301-20260101T100000.mp4')
        self.assertEqual(result['recorded_at'],'2026-01-01T10:00:00+00:00')

    def test_missing_timestamp_stays_unknown(self):
        s = source(); s.pop('recorded_at')
        self.assertIsNone(discover(s)['recorded_at'])

    def test_invalid_direct_timestamp(self):
        s = source(); s['recorded_at'] = '2026-01-01T10:00:00'
        with self.assertRaises(ValueError): discover(s)


class ImageTests(unittest.TestCase):
    def setUp(self):
        a = np.random.default_rng(42).integers(30,220,(320,512),dtype='uint8')
        self.scene = Image.fromarray(a)

    def test_bad_exposures_rejected(self):
        for level in (0,255,128):
            self.assertEqual(quality(Image.new('L',(300,200),level))['score'],0)

    def test_sharpness_and_duplicates(self):
        self.assertGreater(quality(self.scene)['score'],quality(self.scene.filter(ImageFilter.GaussianBlur(8)))['score'])
        original = quality(self.scene)
        repeated = quality(self.scene,[original['fingerprint']])
        self.assertLess(repeated['score'],original['score'])
        self.assertEqual(similarity(fingerprint(self.scene),fingerprint(self.scene)),1)

    def test_all_render_modes(self):
        for mode in ('ordered','floyd','threshold','grayscale'):
            image = render(self.scene,800,448,mode)
            self.assertEqual(image.size,(800,448))
            self.assertEqual(image.mode,'L' if mode=='grayscale' else '1')
            self.assertGreater(np.asarray(image).std(),0)

    def test_dimensions_guarded(self):
        with self.assertRaises(ValueError): render(self.scene,0,448)

    def test_attributed_render_preserves_edge_notices_and_separates_credit(self):
        # A wide frame with source notices at both edges would lose them to a crop.
        original = Image.new('L', (1600, 400), 160)
        draw = ImageDraw.Draw(original)
        draw.rectangle((0, 0, 100, 399), fill=0)
        draw.rectangle((1499, 0, 1599, 399), fill=0)
        s = load('sources.json')[0]
        image = render_for_source(original, s, method='threshold')
        self.assertEqual(image.size, (800, 448))
        self.assertEqual(image.mode, '1')
        self.assertEqual(image.getpixel((20, 200)), 0)
        self.assertEqual(image.getpixel((780, 200)), 0)
        self.assertEqual(image.getpixel((400, 200)), 255)
        self.assertEqual(image.getpixel((400, 405)), 0)  # letterboxing, no overlay
        self.assertLess(np.asarray(image)[415:440].mean(), 1)  # visible credit glyphs
        self.assertEqual(image.getpixel((0, 447)), 255)  # separate white credit band
        with self.assertRaisesRegex(ValueError, 'attribution'):
            render_for_source(original, s, width=64)


class FakeResponse(io.BytesIO):
    def __init__(self,data,start,end,total,status=206,etag='"fixed"'):
        super().__init__(data)
        self.status = status
        self.headers = {'Content-Range':f'bytes {start}-{end}/{total}','ETag':etag}


class FakeOpener:
    def __init__(self,data,status=206,truncate=False):
        self.data,self.status,self.truncate=data,status,truncate
        self.requests=[]

    def open(self,request,timeout=25):
        start,end = map(int,request.get_header('Range').replace('bytes=','').split('-'))
        end=min(end,len(self.data)-1)
        self.requests.append((start,end))
        content=self.data[start:end+1]
        if self.truncate: content=content[:-1]
        return FakeResponse(content,start,end,len(self.data),self.status)


class RangeTests(unittest.TestCase):
    def test_allowlist(self):
        for url in ('http://camera.example/a','https://evil.example/a','https://u:p@camera.example/a','https://camera.example:8080/a'):
            with self.assertRaises(RetrievalError): check_url(url,['camera.example'])

    def test_refuse_full_download(self):
        fake=FakeOpener(b'x'*100,status=200)
        with patch('abyss.network.opener',return_value=fake):
            with self.assertRaisesRegex(RetrievalError,'full download refused'): RangeVideo('https://camera.example/a',['camera.example'])

    def test_budget_and_cache(self):
        fake=FakeOpener(b'x'*1_000_000)
        with patch('abyss.network.opener',return_value=fake):
            video=RangeVideo('https://camera.example/a',['camera.example'],300_000)
            self.assertEqual(video.block(0),video.block(0))
            self.assertEqual(video.requests,2)
            with self.assertRaisesRegex(RetrievalError,'budget'): video.block(600_000)
            self.assertLessEqual(video.bytes_read,300_000)

    def test_truncated_response(self):
        with patch('abyss.network.opener',return_value=FakeOpener(b'x'*100,truncate=True)):
            with self.assertRaisesRegex(RetrievalError,'Incomplete'): RangeVideo('https://camera.example/a',['camera.example'])


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.video = cls.root/'test.mp4'
        # Actual FFmpeg codec, container, seeking and frame extraction.
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=10:duration=8',
                        '-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-y',str(cls.video)],check=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_real_ffmpeg_over_metered_range_bridge(self):
        fake=FakeOpener(self.video.read_bytes())
        with tempfile.TemporaryDirectory() as tmp,patch('abyss.network.opener',return_value=fake):
            video=RangeVideo('https://camera.example/a',['camera.example'],2_000_000)
            with video.bridge() as url:
                frames,diagnostics=extract(url,tmp,interval=2,maximum=3)
            self.assertEqual(len(frames),3)
            self.assertEqual(diagnostics['codec'],'h264')
            self.assertIsNone(video.error)
            self.assertLessEqual(video.bytes_read,self.video.stat().st_size+1)
            self.assertTrue(all(end-start+1<=video.block_size for start,end in fake.requests))

    def test_partial_retrieval_of_padded_mp4(self):
        import struct
        padding=10_000_000
        data=self.video.read_bytes()+struct.pack('>I4s',padding+8,b'free')+b'\0'*padding
        fake=FakeOpener(data)
        with tempfile.TemporaryDirectory() as tmp,patch('abyss.network.opener',return_value=fake):
            video=RangeVideo('https://camera.example/a',['camera.example'],2_000_000)
            with video.bridge() as url:
                frames,diagnostics=extract(url,tmp,interval=2,maximum=3)
            self.assertEqual(len(frames),3)
            self.assertIsNone(video.error)
            self.assertLess(video.bytes_read,len(data)*.20)

    def test_discovery_recovery_on_known_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=source(); a=args(tmp,self.video)
            self.assertEqual(run([s],a)[s['id']],'published')
            path=Path(tmp)/'state/test-camera.json'
            state=read_json(path,{})
            state['failures']=3
            atomic_json(path,state)
            self.assertEqual(run([s],a)[s['id']],'unchanged')
            self.assertEqual(read_json(path,{})['failures'],0)
            self.assertTrue(read_json(Path(tmp)/'public/catalog.json',{})['options'])

    def test_pipeline_repeatability_failure_and_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); s=source(); a=args(root,self.video)
            ooi = load('sources.json')[0]
            for key in ('image_credit_lines', 'preserve_frame', 'acknowledgment', 'data_doi',
                        'rights_review_url', 'timestamp_basis'):
                s[key] = ooi[key]
            result=run([s],a)
            self.assertEqual(result[s['id']],'published')
            latest=root/'public/sources/test-camera/latest.json'
            original=latest.read_bytes()
            metadata=json.loads(original)
            self.assertEqual(metadata['recorded_at'],'2026-01-01T10:00:00+00:00')
            self.assertNotEqual(metadata['captured_at'],metadata['published_at'])
            self.assertTrue(metadata['fixture'])
            self.assertTrue(metadata['attribution_embedded'])
            self.assertEqual(metadata['acknowledgment'], s['acknowledgment'])
            self.assertEqual(metadata['data_doi'], s['data_doi'])
            self.assertEqual(metadata['timestamp_basis'], 'filename_assumed_utc')
            image=root/'public'/metadata['image_url'].split('/abyss/')[1]
            with Image.open(image) as rendered: self.assertEqual(rendered.size,(800,448))
            self.assertEqual(run([s],a)[s['id']],'unchanged')
            generate(root,a.base_url,root/'settings.yml')
            self.assertIn('Test camera (archive)',(root/'settings.yml').read_text())
            self.assertIn('source_id',(root/'settings.yml').read_text())
            self.assertIn('name: Abyss', (root/'settings.yml').read_text())
            self.assertIn(s['acknowledgment'], (root/'settings.yml').read_text())
            a.force=True; a.local_video=str(root/'missing.mp4')
            for _ in range(3): self.assertEqual(run([s],a)[s['id']],'failed')
            self.assertEqual(latest.read_bytes(),original)
            data=read_json(root/'public/catalog.json',{})
            self.assertFalse(data['sources'][s['id']]['available'])
            self.assertEqual(data['options'],[])
            self.assertIsNotNone(data['default_image'])
            a.force=False
            self.assertEqual(run([s],a)[s['id']],'cooldown')
            a.force=True; a.local_video=str(self.video)
            self.assertEqual(run([s],a)[s['id']],'published')
            self.assertTrue(read_json(root/'public/catalog.json',{})['options'])

    def test_no_acceptable_frames_keeps_last_good(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=source(); a=args(tmp,self.video)
            self.assertEqual(run([s],a)[s['id']],'published')
            latest=Path(tmp)/'public/sources/test-camera/latest.json'; original=latest.read_bytes()
            a.force=True; s['scoring']['min_score']=1.1
            self.assertEqual(run([s],a)[s['id']],'rejected')
            self.assertEqual(latest.read_bytes(),original)
            a.force=False
            self.assertEqual(run([s],a)[s['id']],'unchanged')

    def test_changed_credit_rerenders_known_recording_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=source(); a=args(tmp,self.video)
            self.assertEqual(run([s],a)[s['id']],'published')
            latest=Path(tmp)/'public/sources/test-camera/latest.json'
            before=read_json(latest,{})
            self.assertEqual(run([s],a)[s['id']],'unchanged')
            s['image_credit_lines']=['Test data credit: updated required acknowledgment']
            self.assertEqual(run([s],a)[s['id']],'published')
            self.assertNotEqual(read_json(latest,{})['image_sha256'],before['image_sha256'])
            self.assertTrue(read_json(latest,{})['attribution_embedded'])
            self.assertEqual(run([s],a)[s['id']],'unchanged')

    def test_two_sources_and_invalid_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=source(); other=copy.deepcopy(s); other['id']='second-camera'; other['name']='Second camera'
            a=args(tmp,self.video)
            self.assertEqual(set(run([s,other],a).values()),{'published'})
            data=read_json(Path(tmp)/'public/catalog.json',{})
            self.assertEqual(len(data['options']),2)
            self.assertNotEqual(data['sources'][s['id']]['image_url'],data['sources'][other['id']]['image_url'])
            a.source='nonexistent'
            self.assertEqual(run([s,other],a),{s['id']:'unchanged'})

    def test_empty_catalog_and_recipe_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            disabled = source()
            disabled['status'] = 'pending_rights_review'
            disabled['validation']['terms_reviewed_at'] = None
            self.assertEqual(run([disabled],args(tmp)),{})
            with self.assertRaisesRegex(ValueError,'No validated'): generate(tmp,'https://site.example',Path(tmp)/'settings.yml')

    def test_failed_publication_does_not_skip_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=source(); a=args(tmp,self.video)
            with patch('abyss.pipeline.publish',side_effect=OSError('disk full')):
                self.assertEqual(run([s],a)[s['id']],'failed')
            a.force=True
            self.assertEqual(run([s],a)[s['id']],'published')


if __name__ == '__main__': unittest.main()
