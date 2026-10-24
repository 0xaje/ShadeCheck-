"""Synthetic parser boundaries; these tests are not wallet execution evidence."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest

spec=importlib.util.spec_from_file_location('modern_wallet',Path(__file__).resolve().parents[1]/'scripts/modern_wallet.py')
modern=importlib.util.module_from_spec(spec);spec.loader.exec_module(modern)


class ModernWalletBoundaries(unittest.TestCase):
    def test_complete_percentage_at_stale_tip_cannot_prove_current_scan(self):
        status={'percentage_total_blocks_scanned':100,'total_blocks_scanned':100,
                'scan_ranges':[{'priority':'Scanned','end_block':'100'}]}
        with self.assertRaises(RuntimeError): modern.require_complete_scan(status,210)
        status['scan_ranges'][0]['end_block']='210'
        status['total_blocks_scanned']=210
        modern.require_complete_scan(status,210)
        status['percentage_total_blocks_scanned']=99
        with self.assertRaises(RuntimeError): modern.require_complete_scan(status,210)

    def test_missing_or_unrelated_numeric_fields_cannot_prove_receipt(self):
        for text in ['account: 1\nheight: 110', 'total_transparent_balance: 100_000', 'total_ironwood_balance: 99_999']:
            with self.assertRaises(RuntimeError): modern.recipient_balance(text)

    def test_exact_shielded_amount_and_no_transparent_value_required(self):
        self.assertEqual(modern.recipient_balance('total_ironwood_balance: 100_000\ntotal_transparent_balance: 0')['total_ironwood_balance'],100000)
        with self.assertRaises(RuntimeError):
            modern.recipient_balance('total_ironwood_balance: 100_000\ntotal_transparent_balance: 1')

    def test_public_testnet_label_cannot_bypass_regtest_genesis_guard(self):
        with patch.object(modern,'node',side_effect=[{'chain':'test'},'public-testnet-genesis']):
            with self.assertRaisesRegex(ValueError,'regtest genesis'): modern.wait_node()
        info={'chain':'test','blocks':0}
        with patch.object(modern,'node',side_effect=[info,modern.REGTEST_GENESIS]):
            self.assertEqual(modern.wait_node(),info)

    def test_command_without_actual_txids_does_not_become_a_submission(self):
        with self.assertRaises(RuntimeError): modern.object_with('process completed successfully','txids')
        self.assertEqual(modern.object_with('notice\n{"txids":["actual-parser-value"]}\n','txids')['txids'],['actual-parser-value'])
