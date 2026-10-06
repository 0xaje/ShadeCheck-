"""Synthetic rule-boundary tests only; these traces are not runtime evidence."""
import tempfile
import unittest
from pathlib import Path
from shadecheck.core import Recorder, evaluate, load_events

POLICY = {"chunk_size": 20, "alignment_height": 0}


class SyncPatternTests(unittest.TestCase):
    def trace(self, start=80, end=99, delivered=True, mode="upstream"):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events"
            r = Recorder(p, mode)
            seq = r.record("GetBlockRange", "request", "client",
                           start_height=start, end_height=end)
            if delivered:
                for height in range(start, end + 1):
                    r.record("GetBlockRange", "response", "client",
                             request_sequence=seq, height=height)
            r.close()
            return load_events(p)

    def test_aligned_and_partial_ranges(self):
        compliant = evaluate(self.trace(), rules=["SC-001"], sync_policy=POLICY)
        self.assertEqual(compliant["status"], "PASS")
        weak = evaluate(self.trace(83, 89), rules=["SC-001"], sync_policy=POLICY)
        self.assertEqual(weak["status"], "FAIL")
        self.assertEqual(weak["findings"][0]["request_size"], 7)
        self.assertEqual(len(weak["findings"][0]["violations"]), 2)

    def test_shifted_origin_is_respected(self):
        result = evaluate(self.trace(81, 100), rules=["SC-001"],
                          sync_policy={"chunk_size": 20, "alignment_height": 1})
        self.assertEqual(result["status"], "PASS")

    def test_incomplete_delivery_and_fixtures_cannot_pass(self):
        self.assertEqual(evaluate(self.trace(delivered=False), rules=["SC-001"],
                                  sync_policy=POLICY)["status"], "WARN")
        self.assertEqual(evaluate(self.trace(mode="protocol-fixture"), rules=["SC-001"],
                                  sync_policy=POLICY)["status"], "WARN")

    def test_policy_is_required_and_validated(self):
        for policy in [None, {}, {"chunk_size": 0, "alignment_height": 0},
                       {"chunk_size": True, "alignment_height": 0}]:
            with self.assertRaises(ValueError):
                evaluate(self.trace(), rules=["SC-001"], sync_policy=policy)

    def test_other_selected_missing_coverage_prevents_pass(self):
        self.assertEqual(evaluate(self.trace(), rules=["SC-001", "SC-002"],
                                  sync_policy=POLICY)["status"], "WARN")
