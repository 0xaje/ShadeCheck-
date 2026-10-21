"""Submission integrity boundaries. No synthetic runtime findings."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from shadecheck.cli import main
from shadecheck.action_runner import main as action
from shadecheck.reporting import render_markdown


class SubmissionTests(unittest.TestCase):
    def test_demo_without_evidence_fails_without_creating_events(self):
        with tempfile.TemporaryDirectory() as temp:
            old=Path.cwd()
            try:
                os.chdir(temp)
                self.assertEqual(main(['demo']),2)
                self.assertFalse(Path('out').exists())
            finally:os.chdir(old)

    def test_action_requires_explicit_evidence_source(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'SC_OUTPUT':str(Path(temp)/'output'),'SC_EVENTS':'','SC_FIXTURE':''}):
            self.assertEqual(action(),2)
            self.assertFalse((Path(temp)/'output/report.json').exists())

    def test_markdown_escapes_untrusted_text(self):
        result={'status':'FAIL','rules':[],'findings':[{'title':'<script>x</script>|row','severity':'HIGH'}]}
        text=render_markdown(result)
        self.assertNotIn('<script>',text)
        self.assertIn('&lt;script&gt;',text)
        self.assertIn('&#124;',text)


class RunnerBoundaryTests(unittest.TestCase):
    def test_runner_rejects_unknown_commands_and_non_checkouts(self):
        from shadecheck.jobs import LocalRunner
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):LocalRunner(temp)
        runner=LocalRunner(Path(__file__).resolve().parents[1])
        with self.assertRaises(ValueError):runner.start('curl arbitrary-target')
        self.assertEqual(runner.get()['status'],'idle')

    def test_loopback_post_requires_token_and_fixed_scenario(self):
        import threading
        from urllib.request import urlopen,Request
        from urllib.error import HTTPError
        from shadecheck.dashboard_server import create_server
        server=create_server(project=Path(__file__).resolve().parents[1],port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            import json
            token=json.load(urlopen(base+'/api/data'))['runner']['token']
            for headers,body,status in [({},b'{"scenario":"acceptance"}',403),({'X-ShadeCheck-Token':token},b'{"scenario":"arbitrary-command"}',400),({'X-ShadeCheck-Token':token},b'{"scenario":"acceptance","command":"anything"}',400)]:
                with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/jobs',data=body,headers=headers))
                self.assertEqual(error.exception.code,status)
            self.assertEqual(server.runner.get()['status'],'idle')
        finally:server.runner.close();server.shutdown();server.server_close();thread.join()
