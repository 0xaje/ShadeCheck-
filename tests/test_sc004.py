"""Synthetic boundary tests only, not actual wallet/runtime evidence."""
import tempfile
import unittest
from pathlib import Path
from shadecheck.core import Recorder, load_events, evaluate

POLICY = {"require_shielded": True}


class TransparentFallbackTests(unittest.TestCase):
    def trace(self, outputs=1, accepted=True, privacy="AllowRevealedRecipients", mismatch=False, blocked=False, error_code=-8):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "events"
            r = Recorder(path, "upstream")
            seq = r.record("WalletPayment", "request", "adapter", source_mode="wallet-adapter",
                           flow_id="flow", privacy_policy=privacy, receiver_type="transparent")
            if blocked:
                r.record("WalletPayment", "error", "adapter", source_mode="wallet-adapter",
                         request_sequence=seq, flow_id="flow", error="privacy policy rejects transparent recipient", error_code=error_code)
            else:
                r.record("WalletPayment", "response", "adapter", source_mode="wallet-adapter",
                         request_sequence=seq, flow_id="flow")
                r.record("WalletTransaction", "response", "adapter", source_mode="wallet-adapter",
                         request_sequence=seq, flow_id="flow", payload_sha256="actual",
                         transparent_inputs=0, transparent_outputs=outputs, sapling_spends=1, sapling_outputs=2)
                send = r.record("SendTransaction", "request", "peer", payload_sha256="other" if mismatch else "actual", payload_size=100)
                r.record("SendTransaction", "response", "peer", request_sequence=send, error_code=0 if accepted else 1)
            r.close()
            return load_events(path)

    def test_high_requires_matching_accepted_payload(self):
        result = evaluate(self.trace(), rules=["SC-004"], payment_policy=POLICY)
        self.assertEqual(result["findings"][0]["severity"], "HIGH")
        for trace in [self.trace(accepted=False), self.trace(mismatch=True)]:
            self.assertEqual(evaluate(trace, rules=["SC-004"], payment_policy=POLICY)["findings"][0]["severity"], "MEDIUM")

    def test_fullprivacy_can_never_hide_transparent_execution(self):
        result = evaluate(self.trace(privacy="FullPrivacy"), rules=["SC-004"], payment_policy=POLICY)
        self.assertEqual(result["findings"][0]["severity"], "HIGH")

    def test_verified_shielded_execution_has_no_transparent_finding(self):
        result = evaluate(self.trace(outputs=0, privacy="FullPrivacy"), rules=["SC-004"], payment_policy=POLICY)
        self.assertEqual(result["status"], "PASS")

    def test_only_specific_privacy_rejection_supplies_coverage(self):
        self.assertEqual(evaluate(self.trace(privacy="FullPrivacy", blocked=True), rules=["SC-004"], payment_policy=POLICY)["status"], "PASS")
        self.assertEqual(evaluate(self.trace(privacy="FullPrivacy", blocked=True, error_code=-4), rules=["SC-004"], payment_policy=POLICY)["status"], "WARN")

    def test_explicit_policy_required(self):
        with self.assertRaises(ValueError):
            evaluate(self.trace(), rules=["SC-004"])
