"""Replay original real CI evidence for offline integrity tests; no fresh RPC claim."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    spec = importlib.util.spec_from_file_location('developer_walkthrough', ROOT / 'scripts/developer_walkthrough.py')
    walkthrough = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(walkthrough)
finally:
    sys.path.pop(0)


class WalkthroughEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        archive = ROOT / 'examples/range-client/recorded-walkthrough-20261024.zip'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                         '312991d6c82108a37af4135ea14439c253b111c8a14f521d641bd51fb5bfe4cf')
        with zipfile.ZipFile(archive) as z:
            z.extractall(self.temp.name)
        self.root = Path(self.temp.name) / 'onboarding-ci'

    def rehash(self, *names):
        path = self.root / 'walkthrough.json'
        manifest = json.loads(path.read_text())
        for item in manifest['artifacts']:
            if item['path'] in names:
                item['sha256'] = hashlib.sha256((self.root / item['path']).read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))

    def test_original_recorded_run_recomputes_without_backend(self):
        result = walkthrough.verify(self.root)
        self.assertEqual(result['strict_exits'], {'baseline-run': 0, 'unchanged-run': 0, 'changed-run': 1})
        self.assertEqual(result['comparison_exits'], {'unchanged-run': 0, 'changed-run': 1})

    def test_extra_nested_manifest_cannot_escape_inventory(self):
        folder = self.root / 'extra'
        folder.mkdir()
        (folder / 'walkthrough.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            walkthrough.verify(self.root)

    def test_unknown_manifest_version_is_rejected(self):
        path = self.root / 'walkthrough.json'
        value = json.loads(path.read_text()); value['schema_version'] = 99
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'controlled developer walkthrough'):
            walkthrough.verify(self.root)

    def test_edited_receipt_and_node_proof_still_must_match_recorded_delivery(self):
        names = ['changed-run/client-receipt.json', 'changed-run/backend-proof.json']
        for name in names:
            path = self.root / name
            value = json.loads(path.read_text())
            value['blocks'][0]['block_hash'] = '00' * 32
            path.write_text(json.dumps(value))
        self.rehash(*names)
        with self.assertRaisesRegex(ValueError, 'Observer delivery differs'):
            walkthrough.verify(self.root)

    def test_rehashed_comparison_cannot_hide_a_regression(self):
        name = 'changed-run-comparison.json'
        path = self.root / name
        value = json.loads(path.read_text())
        value['baseline_comparison']['regressions'] = 0
        path.write_text(json.dumps(value))
        self.rehash(name)
        with self.assertRaisesRegex(ValueError, 'comparison differs'):
            walkthrough.verify(self.root)
