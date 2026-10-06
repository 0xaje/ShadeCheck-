"""Synthetic rule-boundary unit tests, never runtime evidence."""
import tempfile
import unittest
from pathlib import Path
from shadecheck.core import Recorder, load_events, evaluate


class SelectiveFetchTests(unittest.TestCase):
    def evaluate_trace(self, ids, peer="client", delta=1_000_000, upstream=True):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'events.jsonl'
            r = Recorder(p, 'upstream' if upstream else 'protocol-fixture')
            r.record('GetBlockRange', 'response', 'client', height=1, transaction_ids=['a', 'b'])
            for txid in ids:
                r.record('GetTransaction', 'request', peer, transaction_id=txid)
            r.close()
            events = load_events(p)
            for e in events[1:]:
                e['elapsed_ns'] = events[0]['elapsed_ns'] + delta
            return evaluate(events, rules=['SC-003'])

    def test_subset_requires_same_session_and_membership(self):
        self.assertEqual(self.evaluate_trace(['a'])['status'], 'FAIL')
        self.assertEqual(self.evaluate_trace(['a'], peer='other')['status'], 'PASS')
        self.assertEqual(self.evaluate_trace(['unrelated'])['status'], 'PASS')

    def test_complete_fetch_and_no_fetch_do_not_show_subset(self):
        self.assertEqual(self.evaluate_trace(['a', 'b', 'a'])['status'], 'PASS')
        self.assertEqual(self.evaluate_trace([])['status'], 'PASS')

    def test_window_and_upstream_boundaries(self):
        self.assertEqual(self.evaluate_trace(['a'], delta=30_000_000_001)['status'], 'PASS')
        self.assertEqual(self.evaluate_trace(['a'], delta=-1)['status'], 'PASS')
        self.assertEqual(self.evaluate_trace(['a'], upstream=False)['status'], 'WARN')

    def test_missing_coverage_and_invalid_rule(self):
        with self.assertRaises(ValueError):
            evaluate([], rules=['SC-003'])
        with self.assertRaises(ValueError):
            evaluate([], rules=['SC-999'])
