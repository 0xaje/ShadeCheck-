"""Structural guard tests only; these dictionaries are not runtime transaction evidence."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("regtest_driver", Path(__file__).resolve().parents[1] / "scripts/regtest.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class ShieldedStructureGuards(unittest.TestCase):
    def test_transparent_input_cannot_be_labeled_fully_shielded(self):
        with self.assertRaises(RuntimeError):
            driver.shielded_structure({"vin": [{}], "vout": [], "vShieldedSpend": [], "vShieldedOutput": [{}]})

    def test_unshielding_cannot_be_labeled_fully_shielded(self):
        with self.assertRaises(RuntimeError):
            driver.shielded_structure({"vin": [], "vout": [{}], "vShieldedSpend": [{}], "vShieldedOutput": []})

    def test_empty_or_incomplete_structure_cannot_qualify(self):
        for decoded in ({}, {"vShieldedSpend": [{}]}, {"vShieldedOutput": [{}]}):
            with self.subTest(decoded=decoded), self.assertRaises(RuntimeError):
                driver.shielded_structure(decoded)
