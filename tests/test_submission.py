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
