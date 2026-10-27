import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from test_abyss import FakeOpener, FakeResponse, source
from abyss.registry import eligible, load
from abyss.validation import classify_failure, validate


class HeadAndRangeOpener(FakeOpener):
    def __init__(self, data, head_unsupported=False):
        super().__init__(data)
        self.head_unsupported = head_unsupported

    def open(self, request, timeout=25):
        if request.get_method() == 'HEAD':
            if self.head_unsupported:
                raise urllib.error.HTTPError(request.full_url, 405, 'Method not allowed', {}, None)
            response = FakeResponse(b'', 0, 0, len(self.data), status=200)
            response.headers.update({'Content-Type': 'video/mp4',
                                     'Content-Length': str(len(self.data)),
                                     'Accept-Ranges': 'bytes'})
            return response
        return super().open(request, timeout)


class ValidationTests(unittest.TestCase):
    def test_proxy_failure_is_not_an_upstream_denial(self):
        proxy = urllib.error.URLError(OSError('Tunnel connection failed: 403 Forbidden'))
        self.assertEqual(classify_failure(proxy), 'infrastructure_proxy_tunnel')
        origin = urllib.error.HTTPError('https://camera.example/a', 403, 'Forbidden', {}, None)
        self.assertEqual(classify_failure(origin), 'upstream_http_error')

    def test_failure_report_retains_environment_and_rights_separation(self):
        proxy = urllib.error.URLError(OSError('Tunnel connection failed: 403 Forbidden'))
        with patch('abyss.validation.opener') as opener:
            opener.return_value.open.side_effect = proxy
            report = validate(source(), 'https://camera.example/test.mp4')
        self.assertEqual(report['technical_status'], 'failed')
        self.assertEqual(report['failure']['category'], 'infrastructure_proxy_tunnel')
        self.assertEqual(report['rights_status'], 'not_assessed')
        self.assertEqual(report['upstream_availability'], 'not_established_by_this_failure')

    def test_mac_evidence_is_accepted_and_rights_are_separate(self):
        ooi = load('sources.json')[0]
        self.assertEqual(ooi['validation']['technical_status'], 'runner_verified')
        self.assertEqual(ooi['validation']['user_verification']['verified_by'], 'user_on_mac')
        self.assertEqual(ooi['validation']['deployment_environment_status'], 'passed')
        self.assertEqual(ooi['status'], 'pending_rights_review')
        self.assertFalse(eligible(ooi))
        ooi['validation']['terms_reviewed_at'] = '2026-10-27'
        ooi['status'] = 'validated'
        # The recorded Codex proxy restriction is not a release gate.
        self.assertTrue(eligible(ooi))

    def test_actual_decoding_produces_metadata_only_runner_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / 'test.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=640x360:rate=10:duration=4', '-c:v',
                            'libx264', '-threads', '2', '-pix_fmt', 'yuv420p',
                            '-y', str(video)], check=True)
            for unsupported in (False, True):
                fake = HeadAndRangeOpener(video.read_bytes(), unsupported)
                with patch('abyss.validation.opener', return_value=fake), \
                     patch('abyss.network.opener', return_value=fake), \
                     patch.dict(os.environ, {'GITHUB_ACTIONS': 'true',
                                             'GITHUB_REPOSITORY': 'test/repo',
                                             'GITHUB_RUN_ID': '123', 'GITHUB_SHA': 'abc'}):
                    report = validate(source(), 'https://camera.example/test.mp4',
                                      maximum=2, interval=1)
                self.assertEqual(report['technical_status'], 'passed', report)
                self.assertEqual(report['range']['bytes_received'], 1024)
                self.assertEqual(len(report['frames']), 2)
                self.assertEqual(report['frames'][0]['rendered_mode'], '1')
                self.assertEqual(report['environment'], 'github_actions')
                self.assertEqual(report['run_url'], 'https://github.com/test/repo/actions/runs/123')
                self.assertFalse(report['imagery_published'])
                self.assertEqual(report['rights_status'], 'not_assessed')
                self.assertNotIn('image_url', report)
            self.assertEqual(list(Path(tmp).iterdir()), [video])


if __name__ == '__main__':
    unittest.main()
