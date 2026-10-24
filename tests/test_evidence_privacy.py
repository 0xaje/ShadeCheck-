"""Security boundaries with synthetic inputs, never runtime acceptance evidence."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

import grpc
from shadecheck.core import Recorder, load_events, evaluate
from shadecheck.generated import service_pb2 as pb, service_pb2_grpc as rpc
from shadecheck.harness import start_server
from shadecheck.privacy import private_write


class EvidencePrivacy(unittest.TestCase):
    def test_sessions_are_stable_within_run_but_unlinkable_between_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            sessions = []
            for run in (1, 2):
                recorder = Recorder(Path(temp)/str(run)/'events.jsonl', 'protocol-fixture')
                recorder.record('GetLatestBlock', 'request', 'ipv4:127.0.0.1:12345')
                recorder.record('GetLatestBlock', 'request', 'ipv4:127.0.0.1:12345')
                recorder.record('GetLatestBlock', 'request', 'ipv4:127.0.0.1:54321')
                recorder.close()
                events = load_events(recorder.path)
                self.assertEqual(events[0]['session'], events[1]['session'])
                self.assertNotEqual(events[0]['session'], events[2]['session'])
                self.assertNotEqual(events[0]['session'], hashlib.sha256(b'ipv4:127.0.0.1:12345').hexdigest())
                sessions.append(events[0]['session'])
            self.assertNotEqual(*sessions)

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permission boundary')
    def test_files_are_private_under_permissive_umask_and_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            old = os.umask(0)
            try:
                path=Path(temp)/'new'/'report.json'
                private_write(path,'private')
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
                path.chmod(0o666)
                private_write(path,'updated')
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                link=Path(temp)/'link'
                link.symlink_to(path)
                with self.assertRaises(OSError): private_write(link, 'overwrite')
                self.assertEqual(path.read_text(),'updated')
            finally: os.umask(old)

    def test_sensitive_response_is_forwarded_but_not_recorded(self):
        class Backend(rpc.CompactTxStreamerServicer):
            def SendTransaction(self, request, context):
                return pb.SendResponse(errorCode=7,errorMessage='mnemonic secret-sentinel address-sentinel')
        with tempfile.TemporaryDirectory() as temp:
            backend=grpc.server(ThreadPoolExecutor(max_workers=2))
            rpc.add_CompactTxStreamerServicer_to_server(Backend(),backend)
            port=backend.add_insecure_port('127.0.0.1:0');backend.start()
            self.addCleanup(lambda:backend.stop(0).wait())
            with grpc.insecure_channel(f'127.0.0.1:{port}') as upstream:
                recorder=Recorder(Path(temp)/'events.jsonl','protocol-fixture')
                observer,port=start_server(recorder,upstream=rpc.CompactTxStreamerStub(upstream))
                try:
                    with grpc.insecure_channel(f'127.0.0.1:{port}') as channel:
                        result=rpc.CompactTxStreamerStub(channel).SendTransaction(pb.RawTransaction(data=b'synthetic'),timeout=5)
                        self.assertIn('secret-sentinel',result.errorMessage)
                finally: observer.stop(0).wait();recorder.close()
            events=load_events(recorder.path)
            self.assertEqual(events[-1]['metadata']['error_code'],7)
            self.assertNotIn('sentinel',recorder.path.read_text())
            self.assertEqual(evaluate(events)['findings'][0]['severity'],'MEDIUM')

    def test_publication_requires_explicit_acknowledgement_before_reading_files(self):
        path=Path(__file__).resolve().parents[1]/'scripts/export_site.py'
        spec=importlib.util.spec_from_file_location('export_site',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with self.assertRaisesRegex(ValueError,'Publication exposes'):
            module.export('not-a-suite','not-an-output','not-a-run','not-a-commit')


if __name__=='__main__': unittest.main()
