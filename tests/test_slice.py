import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from shadecheck.core import Recorder, evaluate, load_events
from shadecheck.harness import probe

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/transaction-v5.hex"


class VerticalSliceTests(unittest.TestCase):
    def capture(self, directory):
        path = Path(directory) / "events.jsonl"
        recorder = Recorder(path, "protocol-fixture")
        try:
            response = probe(recorder, bytes.fromhex(FIXTURE.read_text()))
        finally:
            recorder.close()
        return path, response

    def test_real_grpc_fixture_is_rejected_but_session_link_is_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            path, response = self.capture(directory)
            self.assertNotEqual(response.errorCode, 0)
            events = load_events(path)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["session"], events[1]["session"])
            result = evaluate(events)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["findings"][0]["severity"], "MEDIUM")
            self.assertFalse(result["findings"][0]["network_acceptance_reported"])
            self.assertEqual(result["findings"][0]["evidence"], events)
            self.assertEqual(evaluate(events, "advisory")["status"], "WARN")

    def test_cli_exit_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            report = Path(directory) / "report.json"
            run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "test",
                                  "--fixture", str(FIXTURE), "--record", str(events),
                                  "--output", str(report)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertEqual(json.loads(report.read_text())["status"], "FAIL")
            output = Path(directory) / "report.html"
            run = subprocess.run([sys.executable, "-m", "shadecheck.cli", "report",
                                  "--input", str(report), "--format", "html",
                                  "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("protocol-fixture", output.read_text())

    def test_tampered_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.capture(directory)
            content = path.read_text().replace('"payload_size":', '"payload_size":9')
            path.write_text(content)
            with self.assertRaises(ValueError):
                load_events(path)

    def test_empty_and_uncovered_runs_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            recorder = Recorder(path, "protocol-fixture")
            recorder.record("GetMempoolStream", "request", "loopback")
            recorder.close()
            self.assertEqual(evaluate(load_events(path))["status"], "WARN")
            path.write_text("")
            with self.assertRaises(ValueError):
                load_events(path)

    def test_evidence_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.capture(directory)
            with self.assertRaises(FileExistsError):
                Recorder(path, "upstream")


if __name__ == "__main__":
    unittest.main()
