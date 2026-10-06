"""SC-004 consumes explicitly labeled local wallet-adapter and RPC evidence."""


def evaluate_payment(events, policy):
    if not isinstance(policy, dict) or policy != {"require_shielded": True}:
        raise ValueError("SC-004 requires payment policy {require_shielded: true}")
    requests = [e for e in events if e["method"] == "WalletPayment" and e["phase"] == "request"
                and e["mode"] == "wallet-adapter"]
    findings, complete = [], []
    for request in requests:
        seq = request["sequence"]
        flow = request["metadata"]["flow_id"]
        replies = [e for e in events if e["method"] == "WalletPayment" and e["phase"] in {"response", "error"}
                   and e["mode"] == "wallet-adapter" and e["metadata"].get("request_sequence") == seq
                   and e["metadata"].get("flow_id") == flow]
        receipts = [e for e in events if e["method"] == "WalletTransaction" and e["phase"] == "response"
                    and e["mode"] == "wallet-adapter" and e["metadata"].get("request_sequence") == seq
                    and e["metadata"].get("flow_id") == flow]
        confirmed = []
        transparent = []
        for receipt in receipts:
            m = receipt["metadata"]
            counts = [m.get(k) for k in ["transparent_inputs", "transparent_outputs", "sapling_spends", "sapling_outputs"]]
            if any(type(v) is not int or v < 0 for v in counts):
                raise ValueError("Incomplete wallet transaction structure evidence")
            sends = [e for e in events if e["method"] == "SendTransaction" and e["phase"] == "request"
                     and e["mode"] == "upstream" and e["metadata"].get("payload_sha256") == m["payload_sha256"]
                     and e["elapsed_ns"] >= receipt["elapsed_ns"]]
            accepted = [e for e in events if e["method"] == "SendTransaction" and e["phase"] == "response"
                        and e["mode"] == "upstream" and e["metadata"].get("error_code") == 0
                        and any(e["metadata"].get("request_sequence") == s["sequence"]
                                and e["session"] == s["session"] for s in sends)]
            if sends and accepted:
                confirmed.append(receipt)
                if counts[0] or counts[1]:
                    transparent.append((receipt, sends, accepted))
        blocked = any(e["phase"] == "error" and e["metadata"].get("error_code") == -8 and "privacy" in str(e["metadata"].get("error", "")).lower()
                      for e in replies) and request["metadata"].get("privacy_policy") == "FullPrivacy" and request["metadata"].get("receiver_type") == "transparent"
        permissive = request["metadata"].get("receiver_type") == "transparent" and request["metadata"].get("privacy_policy") in {
            "AllowRevealedRecipients", "AllowFullyTransparent", "NoPrivacy"}
        complete.append(bool(confirmed) or blocked)
        if not transparent and not permissive:
            continue
        evidence = [request] + replies + receipts
        for _, sends, accepted in transparent:
            evidence += sends + accepted
        evidence = sorted({e["sequence"]: e for e in evidence}.values(), key=lambda e: e["sequence"])
        findings.append({
            "rule_id": "SC-004", "title": "Transparent payment path under a shielded requirement",
            "severity": "HIGH" if transparent else "MEDIUM",
            "observed_behavior": ("The wallet created a transaction with transparent components and the verification backend accepted its exact payload."
                                  if transparent else "The instrumented client selected a validated transparent recipient under a policy permitting recipient disclosure."),
            "evidence": evidence, "payment_policy": policy,
            "possible_privacy_consequence": "Transparent transaction components can publicly expose addresses and amounts despite the tested flow's shielded requirement.",
            "affected_component": "instrumented local zcashd wallet payment adapter",
            "suggested_investigation": "Reject transparent recipient selection when shielding is required and enforce an appropriate wallet privacy policy; inspect the actual transaction before submission.",
            "flow_id": flow,
        })
    coverage = {"rule_id": "SC-004", "executed": True,
                "coverage": "verified-payment-outcomes" if requests and all(complete) else "incomplete-payment-outcomes",
                "covered": bool(requests) and all(complete)}
    return findings, coverage
