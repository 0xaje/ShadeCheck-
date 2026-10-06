"""Synthetic unit boundaries only; actual CI proof uses real upstream traces."""
import json
import tempfile
import unittest
from pathlib import Path
from shadecheck.core import Recorder, canonical, evaluate, load_events
from shadecheck.regression import save_baseline, load_baseline, compare_result
from shadecheck.cli import main


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.number = 0

    def trace(self, first=20, last=39, peer='peer'):
        self.number += 1
        directory = self.root / str(self.number)
        directory.mkdir()
        path = directory / 'events.jsonl'
        r = Recorder(path, 'upstream')
        seq = r.record('GetBlockRange', 'request', peer, start_height=first, end_height=last)
        for h in range(first,last+1):
            r.record('GetBlockRange', 'response', peer, request_sequence=seq,height=h,transaction_ids=[])
        r.close()
        result = evaluate(load_events(path), rules=['SC-001'], sync_policy={'chunk_size':20,'alignment_height':0})
        (directory/'report.json').write_text(canonical(result))
        return directory,result

    def baseline(self, directory):
        target = directory/'baseline.json'
        save_baseline(directory/'events.jsonl', directory/'report.json',target)
        return load_baseline(target)

    def test_portable_baseline_and_incidental_fields(self):
        directory,_=self.trace()
        b=self.baseline(directory)
        _,current=self.trace(first=40,last=59,peer='different')
        result=compare_result(current,b)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['baseline_comparison']['regressions'],0)
        self.assertIn('events',b)

    def test_new_failure_and_resolved_behavior(self):
        directory,_=self.trace()
        b=self.baseline(directory)
        weak,current=self.trace(23,29)
        result=compare_result(current,b)
        f=next(f for f in result['findings'] if f['rule_id']=='SC-005')
        self.assertEqual(f['change']['change'],'new-failure')
        self.assertTrue(f['evidence'])
        self.assertEqual(result['status'],'FAIL')
        clean=self.trace()[1]
        resolved=compare_result(clean,self.baseline(weak))
        self.assertEqual(resolved['status'],'PASS')
        self.assertTrue(resolved['baseline_comparison']['resolved_behaviors'])

    def test_new_behavior_and_known_failure_not_exempted(self):
        directory,current=self.trace(20,26)
        b=self.baseline(directory)
        result=compare_result(self.trace(23,29)[1],b)
        self.assertEqual(result['findings'][-1]['change']['change'],'new-sensitive-behavior')
        known=compare_result(current,b)
        self.assertEqual(known['baseline_comparison']['regressions'],0)
        self.assertEqual(known['status'],'FAIL')

    def test_context_mismatch_and_tamper_rejected(self):
        directory,current=self.trace()
        b=self.baseline(directory)
        current['sync_policy']={'chunk_size':10,'alignment_height':0}
        with self.assertRaises(ValueError): compare_result(current,b)
        path=directory/'baseline.json'
        value=json.loads(path.read_text());value['events'][0]['session']='edited';path.write_text(canonical(value))
        with self.assertRaises(ValueError): load_baseline(path)
        with self.assertRaises(FileExistsError): save_baseline(directory/'events.jsonl',directory/'report.json',path)

    def test_forged_report_and_missing_coverage_rejected(self):
        directory,result=self.trace()
        result['status']='FAIL'
        (directory/'report.json').write_text(canonical(result))
        with self.assertRaises(ValueError):self.baseline(directory)
        empty=self.root/'empty';r=Recorder(empty,'upstream');r.record('GetLatestBlock','request','p');r.close()
        result=evaluate(load_events(empty))
        report=self.root/'empty-report';report.write_text(canonical(result))
        with self.assertRaises(ValueError):save_baseline(empty,report,self.root/'empty-baseline')

    def test_severity_escalation_and_current_missing_coverage(self):
        path=self.root/'broadcast';r=Recorder(path,'upstream')
        seq=r.record('SendTransaction','request','p',payload_size=100,payload_sha256='test')
        r.record('SendTransaction','response','p',request_sequence=seq,error_code=0)
        r.record('GetMempoolStream','response','p',payload_sha256='test');r.close()
        events=load_events(path);partial=self.root/'partial'
        partial.write_text(canonical(events[0])+'\n')
        report=self.root/'partial-report';report.write_text(canonical(evaluate(events[:1])))
        bp=self.root/'broadcast-baseline';save_baseline(partial,report,bp)
        result=compare_result(evaluate(events),load_baseline(bp))
        self.assertEqual(result['findings'][-1]['change']['change'],'severity-increased')
        self.assertTrue(result['findings'][-1]['baseline_evidence'])
        empty=self.root/'requestless';r=Recorder(empty,'upstream');r.record('GetLatestBlock','request','p');r.close()
        result=compare_result(evaluate(load_events(empty)),load_baseline(bp))
        self.assertEqual(result['status'],'WARN')
        self.assertEqual(result['baseline_comparison']['status'],'WARN')

    def test_cli_save_compare_test_baseline_and_exit(self):
        directory,_=self.trace();target=directory/'baseline.json'
        self.assertEqual(main(['baseline','save','--events',str(directory/'events.jsonl'),'--input',str(directory/'report.json'),'--output',str(target)]),0)
        weak,_=self.trace(23,29);output=self.root/'comparison.json'
        self.assertEqual(main(['compare','--events',str(weak/'events.jsonl'),'--input',str(weak/'report.json'),'--baseline',str(target),'--output',str(output)]),1)
        config=self.root/'policy.json';config.write_text(canonical({'schema_version':1,'sync':{'chunk_size':20,'alignment_height':0}}))
        out2=self.root/'test.json'
        self.assertEqual(main(['test','--events',str(weak/'events.jsonl'),'--rules','SC-001','SC-005','--config',str(config),'--baseline',str(target),'--output',str(out2)]),1)
        self.assertEqual(json.loads(output.read_text()),json.loads(out2.read_text()))
