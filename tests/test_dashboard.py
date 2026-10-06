"""HTTP and precision boundaries; no simulated privacy findings."""
import json
import threading
import unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from shadecheck.dashboard_server import create_server, display_safe


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def test_empty_state_and_packaged_assets(self):
        with urlopen(self.url+'/api/data') as response:
            data=json.load(response)
            self.assertIsNone(data['suite'])
            self.assertEqual(data['reports'],[])
            self.assertEqual(len(data['rules']),5)
        for path in ['/','/app.js','/style.css']:
            with urlopen(self.url+path) as response:
                self.assertEqual(response.status,200)
                self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])
                self.assertTrue(response.read())

    def test_host_and_non_artifact_requests_rejected(self):
        for path,headers,status in [('/api/data',{'Host':'external.example'},403),('/download/../../pyproject.toml',{},404),('/download/bundle',{},404)]:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url+path,headers=headers))
            self.assertEqual(error.exception.code,status)

    def test_large_integer_display_is_exact_and_nonmutating(self):
        original={'timestamp_ns':1791256364012345678,'sequence':1,'nested':[True,2**53]}
        safe=display_safe(original)
        self.assertEqual(safe['timestamp_ns'],'1791256364012345678')
        self.assertEqual(safe['nested'],[True,'9007199254740992'])
        self.assertEqual(original['timestamp_ns'],1791256364012345678)
