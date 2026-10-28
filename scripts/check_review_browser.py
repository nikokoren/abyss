"""Optional real-browser smoke test. Requires Playwright and installed Chromium."""
import functools
import argparse
import json
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from abyss.preferences import FEATURE_COUNT, FEATURE_SPACE
from abyss.review import Gallery


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-file',action='store_true',help='Also test file URLs when browser policy permits')
    parser.add_argument('--chromium',help='Use an installed Chromium instead of the Playwright download')
    arguments=parser.parse_args()
    source={'id':'demo','name':'SYNTHETIC DEMO · not ocean footage','fixture':True,
            'attribution':'Generated test scenes','license':'Test data only'}
    gallery=Gallery(source,'nikokoren','nikokoren/abyss')
    class Encoder:provenance={'feature_space':FEATURE_SPACE,'weights_sha256':'synthetic-test-only'}
    for i in range(4):
        image=Image.new('RGB',(800,448),(25+i*12,50+i*8,55+i*6));draw=ImageDraw.Draw(image)
        draw.polygon([(90,448),(260+i*30,80),(360,448)],fill=(120+i*20,)*3)
        draw.ellipse((220,10,330+i*20,110),fill=(190,210,210))
        features=[0.0]*FEATURE_COUNT;features[0]=1;features[6+i]=1
        gallery.add({'recording':{'url':f'https://example.invalid/test-{i}.mp4','recorded_at':'2026-01-01T00:00:00Z'},
                     'seconds':i*90,'stage':'coarse','quality':{'score':.8-i*.03,'fingerprint':'01'*128},'selection_score':.8-i*.03},image,features)
    with tempfile.TemporaryDirectory() as tmp:
        gallery.save(tmp,Encoder(),{})
        stable=Gallery(dict(source,adapter='ooi_image_directory'),'nikokoren','nikokoren/abyss')
        for i in range(2):
            stable.add({'recording':{'url':f'https://example.invalid/static-{i}.jpg','recorded_at':None},
                        'seconds':0,'stage':'snapshot','quality':{'score':.8,'fingerprint':'01'*128},
                        'selection_score':.8},image,features)
        stable.save(Path(tmp)/'static',Encoder(),{})
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=tmp))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                launch={'args':['--no-sandbox']}
                if arguments.chromium:launch['executable_path']=arguments.chromium
                browser=p.chromium.launch(**launch)
                page=browser.new_page(viewport={'width':1440,'height':1050})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.get_by_role('heading',name='Teach Abyss your eye.').wait_for()
                page.locator('#choose-a').click();assert page.locator('#count').inner_text()=='1 choice saved'
                page.locator('#repeat-a').check();page.locator('#original-mode').click()
                assert page.locator('#repeat-a').is_checked()
                page.locator('#neither').click();assert page.locator('#count').inner_text()=='2 choices saved'
                page.keyboard.press('2');assert page.locator('#count').inner_text()=='3 choices saved'
                page.locator('#undo').click();assert page.locator('#count').inner_text()=='2 choices saved'
                page.reload();assert page.locator('#count').inner_text()=='2 choices saved'
                with page.expect_download() as downloaded:page.locator('#export').click()
                file=downloaded.value;file.save_as(str(Path(tmp)/'backup.json'))
                backup=json.loads((Path(tmp)/'backup.json').read_text());assert len(backup['comparisons'])==2
                assert any(r['repetitive'] for r in backup['comparisons'])
                page.evaluate('window.open = url => {window.submittedURL=url;}')
                page.locator('#submit').click()
                from urllib.parse import urlsplit,parse_qs
                url=page.evaluate('window.submittedURL');assert url.startswith('https://github.com/nikokoren/abyss/issues/new?')
                body=parse_qs(urlsplit(url).query)['body'][0];assert '```abyss-feedback' in body
                page.evaluate('localStorage.clear()');page.reload();assert page.locator('#count').inner_text()=='0 choices saved'
                page.locator('#import-file').set_input_files(str(Path(tmp)/'backup.json'))
                page.wait_for_function("document.getElementById('count').textContent==='2 choices saved'")
                page.locator('#edit-choices').click();assert page.locator('.card[data-selected=true]').count()==1
                page.locator('#paper-mode').click()
                Path('output/validation').mkdir(parents=True,exist_ok=True)
                page.screenshot(path='output/validation/preference-gallery-desktop.png',full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path='output/validation/preference-gallery-mobile.png',full_page=True)
                assert not errors,errors
                page.context.set_offline(True)
                page.locator('#choose-b').click()
                assert page.locator('#count').inner_text()=='2 choices saved'
                page.context.set_offline(False)
                page.goto(f'http://127.0.0.1:{server.server_port}/static/')
                page.get_by_role('heading',name='No review needed.').wait_for()
                assert not page.locator('#pair-grid').is_visible()
                assert not page.locator('#submit').is_visible()
                assert page.locator('#submit').is_disabled()
                page.keyboard.press('1');page.keyboard.press('0')
                assert page.locator('#count').inner_text()=='0 choices saved'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path='output/validation/preference-gallery-static.png',full_page=True)
                assert not errors,errors
                if arguments.check_file:
                    page.goto(Path(tmp,'index.html').as_uri())
                    page.get_by_role('heading',name='Teach Abyss your eye.').wait_for()
                    page.locator('#choose-a').click();page.reload()
                    assert page.locator('#count').inner_text()=='1 choice saved'
                browser.close()
        finally:server.shutdown();server.server_close();thread.join()
    print('Browser checks passed: choices, neither/repetition, undo, reload, export/import, edit, GitHub draft, mobile layout, offline interactions and no-review-needed static batches. File-URL test is opt-in for compatible browser policies.')


if __name__=='__main__':main()
