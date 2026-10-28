import argparse
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from test_abyss import args, source
from abyss.feedback import batch_id, normalize, parse_body
from abyss.preferences import FEATURE_COUNT, FEATURE_SPACE, digest, load_model, rank, train
from abyss.publication import atomic_json, read_json
from abyss.review import Gallery
from abyss.search import search
from abyss.pipeline import run


def features(axis):
    x=[0.0]*FEATURE_COUNT;x[0]=1;x[axis]=1
    return x


def manifest(count=10, groups=1):
    candidates={}
    for i in range(count):
        for side,axis in [('a',6),('b',7)]:
            key=digest(f'{i}-{side}')[:32]
            candidates[key]={'features':features(axis),'recording_url':f'https://camera.example/{i%groups}.mp4',
                             'fingerprint':('01' if side=='a' else '10')*128,'quality_score':.8}
    value={'schema_version':1,'feature_space':FEATURE_SPACE,'reviewer':'nikokoren','candidates':candidates}
    value['batch_id']=batch_id(value)
    return value


def feedback(count=10, groups=1, choice='a', issue=1):
    m=manifest(count,groups)
    keys=list(m['candidates'])
    payload={'schema_version':1,'batch_id':m['batch_id'],
             'comparisons':[{'a':keys[i*2],'b':keys[i*2+1],'choice':choice,'repetitive':[]} for i in range(count)]}
    doc=normalize(payload,m,reviewer='nikokoren',issue_number=issue,updated_at=f'2026-10-28T00:00:{issue:02}+00:00')
    return m,payload,doc


class FeedbackTests(unittest.TestCase):
    def test_body_and_manifest_are_verified(self):
        m,p,_=feedback()
        self.assertEqual(parse_body('My choices\n```abyss-feedback\n'+json.dumps(p)+'\n```'),p)
        modified=copy.deepcopy(m);modified['candidates'][next(iter(modified['candidates']))]['features'][6]=2
        with self.assertRaisesRegex(ValueError,'identity'):normalize(p,modified,reviewer='nikokoren',issue_number=1,updated_at='now')
        with self.assertRaisesRegex(ValueError,'reviewer'):normalize(p,m,reviewer='attacker',issue_number=1,updated_at='now')

    def test_client_features_duplicate_pairs_and_unknown_images_rejected(self):
        m,p,_=feedback()
        for mutate in (lambda q:q['comparisons'][0].update(features=[1]),
                       lambda q:q['comparisons'].append(q['comparisons'][0]),
                       lambda q:q['comparisons'][0].update(a='unknown'),
                       lambda q:q['comparisons'][0].update(repetitive=['unknown'])):
            q=copy.deepcopy(p);mutate(q)
            with self.assertRaises(ValueError):normalize(q,m,reviewer='nikokoren',issue_number=1,updated_at='now')

    def test_reversed_pairs_are_canonical(self):
        m,p,original=feedback(1)
        row=p['comparisons'][0];row['a'],row['b']=row['b'],row['a'];row['choice']='b'
        reversed=normalize(p,m,reviewer='nikokoren',issue_number=1,updated_at='now')
        self.assertEqual(reversed['comparisons'],original['comparisons'])

    def test_only_owner_authored_feedback_can_be_ingested(self):
        spec=importlib.util.spec_from_file_location('feedback_ingester','scripts/preference_feedback.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        m,p,_=feedback()
        event={'issue':{'user':{'login':'nikokoren'},'title':'Abyss preferences','body':'```abyss-feedback\n'+json.dumps(p)+'\n```','number':12,'updated_at':'2026-10-28T00:00:00Z'}}
        with tempfile.TemporaryDirectory() as tmp:
            atomic_json(Path(tmp)/'batches'/f'{m["batch_id"]}.json',m)
            with self.assertRaises(ValueError):module.ingest(tmp,event,'nikokoren','attacker')
            module.ingest(tmp,event,'nikokoren','nikokoren')
            self.assertTrue((Path(tmp)/'feedback/issue-12.json').exists())
            event['issue']['body']='malformed'
            with self.assertRaises(ValueError):module.ingest(tmp,event,'nikokoren','nikokoren')
            self.assertTrue((Path(tmp)/'feedback/issue-12.json').exists())


class LearningTests(unittest.TestCase):
    def test_learning_changes_ranking_and_starts_cautiously(self):
        _,_,doc=feedback(30)
        model=train([doc],'nikokoren')
        metrics={'score':.8,'fingerprint':'0'*256}
        self.assertEqual(model['status'],'ready')
        a=rank(metrics,features(6),model);b=rank(metrics,features(7),model)
        self.assertGreater(a['selection_score'],b['selection_score'])
        self.assertEqual(a['preference_weight'],.45)
        self.assertEqual(model['evaluation']['status'],'unavailable')
        self.assertEqual(train([],'nikokoren')['status'],'needs_more_feedback')
        self.assertEqual(train([feedback(3)[2]],'nikokoren')['status'],'needs_more_feedback')

    def test_latest_issue_wins_without_counting_duplicate_votes(self):
        _,_,first=feedback(10,issue=1)
        _,_,second=feedback(10,choice='b',issue=2)
        result=train([first,second],'nikokoren')
        self.assertEqual(result['comparisons'],10)
        self.assertGreater(rank({'score':.8,'fingerprint':'0'*256},features(7),result)['preference_score'],.5)
        self.assertEqual(result['model_id'],train([second,first],'nikokoren')['model_id'])
        self.assertEqual(train([second],'other')['comparisons'],0)

    def test_neither_and_repetitive_flags_are_kept(self):
        m,p,doc=feedback(10)
        q=copy.deepcopy(p);q['comparisons'][0]['choice']='neither';q['comparisons'][0]['repetitive']=[q['comparisons'][0]['a']]
        doc=normalize(q,m,reviewer='nikokoren',issue_number=1,updated_at='now')
        model=train([doc],'nikokoren')
        self.assertEqual(model['neither_comparisons'],1)
        self.assertEqual(len(model['repetitive_hashes']),1)
        metrics={'score':.8,'fingerprint':model['repetitive_hashes'][0]}
        self.assertGreater(rank(metrics,features(6),model)['manual_repeat_penalty'],0)
        neither=train([feedback(10,choice='neither')[2]],'nikokoren')
        self.assertEqual(neither['status'],'needs_more_feedback')

    def test_held_out_metrics_do_not_share_recording_groups(self):
        model=train([feedback(30,groups=5)[2]],'nikokoren')
        self.assertEqual(model['evaluation']['status'],'measured')
        self.assertEqual(model['evaluation']['test_comparisons'],6)
        self.assertGreater(model['evaluation']['accuracy'],.9)
        self.assertEqual(model['evaluation']['split'],'held_out_connected_recording_groups')

    def test_corrupt_or_incompatible_models_fall_back(self):
        model=train([feedback(10)[2]],'nikokoren')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.json';atomic_json(p,model)
            self.assertIsNotNone(load_model(p))
            model['feature_space']='other';atomic_json(p,model)
            self.assertIsNone(load_model(p))
            p.write_text('broken');self.assertIsNone(load_model(p))
        self.assertEqual(rank({'score':.8},None,None)['selection_score'],.8)


class RankingIntegrationTests(unittest.TestCase):
    def test_personal_model_changes_refinement_and_winner_without_bypassing_quality(self):
        model=train([feedback(30)[2]],'nikokoren');calls=[]
        class Encoder:
            def encode(self,image,metrics):return features(6 if image.getpixel((0,0))==120 else 7)
        def metric(image,*unused):
            value=image.getpixel((0,0));return {'score':0 if value==0 else .8 if value==120 else .85,'fingerprint':'0'*256}
        def frames(url,directory,positions,**kwargs):
            calls.append((kwargs['prefix'],positions));result=[]
            for i,seconds in enumerate(positions):
                value=120 if 10<seconds<50 else 200
                p=Path(directory)/f'{kwargs["prefix"]}-{i}.png';Image.new('L',(100,80),value).save(p);result.append((seconds,p))
            return result,{'extraction_errors':[]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.json';atomic_json(p,model)
            a=args(tmp,'fixture');a.candidates=8;a.preference_model=str(p);a.preference_encoder=Encoder();a.refine_windows=1;a.refine_candidates=2
            with patch('abyss.search.probe',return_value=(120,'h264')),patch('abyss.search.extract_positions',side_effect=frames),patch('abyss.search.quality',side_effect=metric):
                best,details,_=search(source(),[{'url':'local','recorded_at':None}],tmp,a)
            self.assertTrue(10<best['seconds']<50)
            fine=[p for prefix,p in calls if 'fine' in prefix][0]
            self.assertTrue(all(0<=p<60 for p in fine))
            self.assertEqual(details['preference']['status'],'active')

    def test_missing_encoder_is_a_quality_fallback(self):
        model=train([feedback(10)[2]],'nikokoren')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.json';atomic_json(p,model)
            a=args(tmp,'fixture');a.preference_model=str(p)
            image=Path(tmp)/'scene.png';Image.new('L',(100,80),100).save(image)
            with patch('abyss.search.ImageEncoder',side_effect=ImportError('not installed')),patch('abyss.search.probe',return_value=(120,'h264')),patch('abyss.search.extract_positions',return_value=([(30,image)],{'extraction_errors':[]})):
                best,details,_=search(source(),[{'url':'local','recorded_at':None}],tmp,a)
            self.assertIsNotNone(best)
            self.assertEqual(details['preference']['status'],'quality_fallback')
            self.assertIn('not installed',details['preference']['error'])

    def test_preference_cannot_promote_an_unreadable_frame(self):
        model=train([feedback(30)[2]],'nikokoren')
        class Encoder:
            def encode(self,image,metrics):return features(6 if image.getpixel((0,0))==0 else 7)
        def frames(url,directory,positions,**kwargs):
            result=[]
            for i,seconds in enumerate(positions):
                p=Path(directory)/f'{kwargs["prefix"]}-{i}.png'
                Image.new('L',(100,80),0 if seconds<60 else 180).save(p);result.append((seconds,p))
            return result,{'extraction_errors':[]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.json';atomic_json(p,model)
            a=args(tmp,'fixture');a.preference_model=str(p);a.preference_encoder=Encoder()
            s=source();s['scoring']['min_score']=.30
            with patch('abyss.search.probe',return_value=(120,'h264')),patch('abyss.search.extract_positions',side_effect=frames),patch('abyss.search.quality',side_effect=lambda image,*unused:{'score':0 if image.getpixel((0,0))==0 else .31,'fingerprint':'0'*256}):
                best,_,_=search(s,[{'url':'local','recorded_at':None}],tmp,a)
            self.assertEqual(best['quality']['score'],.31)

    def test_encode_failure_falls_back_without_losing_decoded_frames(self):
        model=train([feedback(10)[2]],'nikokoren')
        class Encoder:
            def encode(self,*unused):raise RuntimeError('encoder failed')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.json';atomic_json(p,model)
            a=args(tmp,'fixture');a.preference_model=str(p);a.preference_encoder=Encoder()
            image=Path(tmp)/'good.png';Image.new('L',(100,80),100).save(image)
            with patch('abyss.search.probe',return_value=(120,'h264')),patch('abyss.search.extract_positions',return_value=([(30,image)],{'extraction_errors':[]})):
                best,details,_=search(source(),[{'url':'local','recorded_at':None}],tmp,a)
            self.assertIsNotNone(best)
            self.assertEqual(details['preference']['status'],'quality_fallback')
            self.assertIn('encoder failed',details['preference']['error'])

    def test_new_model_revisits_known_recordings_once(self):
        model=train([feedback(10)[2]],'nikokoren')
        with tempfile.TemporaryDirectory() as tmp:
            a=args(tmp,'fixture');p=Path(tmp)/'model.json';a.preference_model=str(p)
            s=source()
            def selected(source,records,directory,arguments,history):
                image=Path(directory)/'good.png';Image.new('L',(800,448),100).save(image)
                model_id=model['model_id'] if p.exists() else None
                return {'recording':records[0],'seconds':30,'path':image,'quality':{'score':.8,'fingerprint':'0'*256}}, {'recordings':[],'preference':{'model_id':model_id}},['local-fixture']
            with patch('abyss.pipeline.search',side_effect=selected) as searcher:
                self.assertEqual(run([s],a)[s['id']],'published')
                self.assertEqual(run([s],a)[s['id']],'unchanged')
                atomic_json(p,model)
                # The model is reevaluated, but an identical winning image is not republished.
                self.assertEqual(run([s],a)[s['id']],'unchanged')
                self.assertEqual(run([s],a)[s['id']],'unchanged')
                self.assertEqual(searcher.call_count,2)


class GalleryTests(unittest.TestCase):
    def test_fresh_evaluation_eligibility_is_computed_from_actual_candidate_recordings(self):
        class Encoder: provenance = {'feature_space': FEATURE_SPACE, 'weights_sha256': 'test'}
        model = {'status': 'ready', 'model_id': 'frozen', 'comparisons': 80}
        for leaked in (False, True):
            context = {'fresh_recordings_only': True, 'training_recording_urls': ['https://camera.example/old.mp4']}
            gallery = Gallery(source(), 'nikokoren', 'nikokoren/abyss', model, evaluation_context=context)
            for i in range(2):
                url = 'https://camera.example/old.mp4' if leaked and i == 0 else f'https://camera.example/new-{i}.mp4'
                gallery.add({'recording': {'url': url, 'recorded_at': None}, 'seconds': i, 'stage': 'coarse',
                             'quality': {'score': .8, 'fingerprint': '0'*256}, 'selection_score': .9,
                             'preference_score': .95}, Image.new('RGB', (800, 448), 'gray'), features(6+i))
            with tempfile.TemporaryDirectory() as tmp:
                result = gallery.save(tmp, Encoder(), {})
            self.assertEqual(result['evaluation_context']['eligible'], not leaked)
            self.assertEqual(result['evaluation_context']['model_id'], 'frozen')

    def test_single_file_gallery_escapes_metadata_and_manifest_has_no_images(self):
        s=source();s['name']='Ocean </script><script>alert(1)</script>'
        gallery=Gallery(s,'nikokoren','nikokoren/abyss')
        class Encoder:provenance={'feature_space':FEATURE_SPACE,'weights_sha256':'test'}
        image=Image.new('RGB',(800,448),'gray')
        for i in range(2):
            metrics={'score':.8,'fingerprint':'0'*256}
            gallery.add({'recording':{'url':f'https://camera.example/{i}.mp4','recorded_at':None},'seconds':i,'stage':'coarse','quality':metrics,'selection_score':.8},image,features(6+i))
        with tempfile.TemporaryDirectory() as tmp:
            m=gallery.save(tmp,Encoder(),{})
            self.assertEqual(batch_id(m),m['batch_id'])
            html=(Path(tmp)/'index.html').read_text()
            self.assertIn('data:image/png;base64,',html)
            self.assertNotIn('Ocean </script><script>',html)
            self.assertNotIn('data:image/png',json.dumps(m))
            self.assertEqual(len(m['candidates']),2)


if __name__=='__main__':unittest.main()
