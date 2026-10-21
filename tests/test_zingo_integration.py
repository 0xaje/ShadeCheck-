"""Synthetic parser tests: a successful process exit alone cannot prove sync."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    spec = importlib.util.spec_from_file_location("zingo_integration", SCRIPTS / "zingo_integration.py")
    integration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integration)
finally:
    sys.path.pop(0)


class ZingoCompletionGuards(unittest.TestCase):
    def test_native_cli_accepts_json_documents_and_plain_hash_results(self):
        with patch.object(integration, "command", return_value='{"chain":"regtest"}\n'):
            self.assertEqual(integration.node("getblockchaininfo"), {"chain": "regtest"})
        block_hash = "ab" * 32
        with patch.object(integration, "command", return_value=block_hash + "\n"):
            self.assertEqual(integration.node("getblockhash", 100), block_hash)

    def test_process_output_without_complete_scanning_is_rejected(self):
        for output in ['{}', '{"height":110}', '{"percentage_total_blocks_scanned":99,"total_blocks_scanned":100}',
                       '{"percentage_total_blocks_scanned":100,"total_blocks_scanned":0}']:
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                integration.parse_sync_status(output)

    def test_uses_last_actual_status_and_ignores_unrelated_documents(self):
        output = 'Creating a wallet\n{"save":"ok"}\n{"percentage_total_blocks_scanned":100,"total_blocks_scanned":101}'
        self.assertEqual(integration.parse_sync_status(output)["total_blocks_scanned"], 101)
        with self.assertRaises(RuntimeError):
            integration.parse_sync_status(output + '\n{"percentage_total_blocks_scanned":50,"total_blocks_scanned":50}')
