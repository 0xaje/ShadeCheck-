export default function handler(req, res) {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate');

  const leakyReport = {
    correlation_window_seconds: 30,
    evidence_modes: ["upstream"],
    evidence_root: "b23d03ca5efae53b49f563a608e23bd4bd3093018fbbb6d0d25b7e7bb4d8b4e3",
    status: "FAIL",
    policy: "strict",
    rules: [
      { rule_id: "SC-001", executed: true, covered: true, coverage: "complete-range-delivery" },
      { rule_id: "SC-002", executed: true, covered: true, coverage: "broadcast-observed" }
    ],
    findings: [
      {
        rule_id: "SC-002",
        title: "Broadcast payload linked to a transport session",
        severity: "HIGH",
        observed_behavior: "Accepted submission and identical mempool bytes observed within the configured window.",
        possible_privacy_consequence: "The RPC observer can associate these submitted bytes with this connection; this does not identify a person.",
        affected_component: "lightwalletd broadcast transport",
        suggested_investigation: "Review the server trust model and whether an independent broadcast path reduces the observer's linkability.",
        evidence: [
          {
            sequence: 9,
            method: "SendTransaction",
            phase: "request",
            mode: "upstream",
            timestamp_ns: "1792112339907304082",
            session: "ab2252f91a4f251a0a2ad13762eb730da1061426c49cb327a8c30d61ecc44ae2",
            metadata: { payload_size: 2140, payload_sha256: "45f7aedf57fbdb44c3774a2b64c3da8fd751c483c29ef0ff78f6978521aee370" },
            event_hash: "d5962b32ece25abcce98d20363daddc1c47c266f4b371cbe6caa5c245ab3723d"
          },
          {
            sequence: 10,
            method: "SendTransaction",
            phase: "response",
            mode: "upstream",
            timestamp_ns: "1792112339907382382",
            session: "ab2252f91a4f251a0a2ad13762eb730da1061426c49cb327a8c30d61ecc44ae2",
            metadata: { error_code: 0, request_sequence: 9 },
            event_hash: "b93768a3d628113eeb7ce7b329982a23682ac7932985e76a7dd93ed11512717e"
          },
          {
            sequence: 11,
            method: "GetMempoolStream",
            phase: "response",
            mode: "upstream",
            timestamp_ns: "1792112339917783882",
            session: "ab2252f91a4f251a0a2ad13762eb730da1061426c49cb327a8c30d61ecc44ae2",
            metadata: { payload_size: 2140, payload_sha256: "45f7aedf57fbdb44c3774a2b64c3da8fd751c483c29ef0ff78f6978521aee370" },
            event_hash: "b23d03ca5efae53b49f563a608e23bd4bd3093018fbbb6d0d25b7e7bb4d8b4e3"
          }
        ]
      },
      {
        rule_id: "SC-001",
        title: "Block range violates configured sync disclosure policy",
        severity: "MEDIUM",
        observed_behavior: "Requested heights 83 through 89 (7 blocks): start height is not aligned to the configured boundary; inclusive request size differs from the configured chunk size.",
        possible_privacy_consequence: "The service observes the connection's exact scan boundary and request size. These can depend on local sync state, but wallet history or identity is not proven.",
        affected_component: "lightwalletd block-range synchronization",
        suggested_investigation: "Review fixed-size aligned retrieval, local filtering, and chain-tip handling against the declared policy; evaluate extra bandwidth and other privacy tradeoffs.",
        evidence: [
          {
            sequence: 1,
            method: "GetBlockRange",
            phase: "request",
            mode: "upstream",
            timestamp_ns: "1792112339905926182",
            session: "ab2252f91a4f251a0a2ad13762eb730da1061426c49cb327a8c30d61ecc44ae2",
            metadata: { start_height: 83, end_height: 89 },
            event_hash: "1b78f14ef09ff5f7e53b72f7a31be07a05ad20ac9a1ed8a152b72c57510b1ef7"
          }
        ]
      }
    ],
    limitations: [
      "Defined tests cover SC-001 through SC-004; SC-005 requires a compatible saved baseline.",
      "A transport peer identifies a connection, not a person or wallet.",
      "Local fixture replay is not consensus validation or network acceptance.",
      "Transaction SHA-256 fingerprints are not Zcash transaction IDs.",
      "No violation observed does not establish anonymity."
    ]
  };

  const shieldedReport = {
    correlation_window_seconds: 30,
    evidence_modes: ["upstream", "wallet-adapter"],
    evidence_root: "9e3c01bf77ae123cde88231901a1cfa501235678432190875634125648792014",
    status: "PASS",
    policy: "strict",
    rules: [
      { rule_id: "SC-001", executed: true, covered: true, coverage: "complete-range-delivery" },
      { rule_id: "SC-004", executed: true, covered: true, coverage: "verified-payment-outcomes" }
    ],
    findings: [],
    limitations: [
      "Defined tests cover SC-001 through SC-004; SC-005 requires a compatible saved baseline.",
      "A transport peer identifies a connection, not a person or wallet.",
      "Local fixture replay is not consensus validation or network acceptance.",
      "Transaction SHA-256 fingerprints are not Zcash transaction IDs.",
      "No violation observed does not establish anonymity."
    ]
  };

  res.status(200).json({
    suite: {
      name: "thezecathon-live-deployment",
      acceptance_status: "PASS",
      privacy_status: "FAIL",
      rules_executed: ["SC-001", "SC-002", "SC-003", "SC-004", "SC-005"],
      steps: 13,
      limitations: [
        "Defined tests cover SC-001 through SC-004; SC-005 requires a compatible saved baseline.",
        "A transport peer identifies a connection, not a person or wallet.",
        "Local fixture replay is not consensus validation or network acceptance.",
        "Transaction SHA-256 fingerprints are not Zcash transaction IDs.",
        "Passing a defined test does not establish anonymity."
      ],
      loaded_at: new Date().toISOString()
    },
    rules: [
      { id: "SC-001", title: "Sync Pattern Disclosure", test: "Block-range size and alignment against the declared policy.", boundary: "No wallet-history inference; timing and repeated-history analysis are outside coverage." },
      { id: "SC-002", title: "Broadcast Linkability", test: "Connection-to-payload association; HIGH adds accepted submission and exact mempool bytes.", boundary: "A connection is not a person. Shielded payments can still reveal broadcast linkage." },
      { id: "SC-003", title: "Selective Transaction Fetch", test: "A non-empty proper subset of IDs from a delivered multi-transaction compact block.", boundary: "Delivery does not prove wallet processing or ownership." },
      { id: "SC-004", title: "Transparent Fallback", test: "Instrumented transparent selection or accepted transparent components under a shielded requirement.", boundary: "Tests an explicit recipient path, not automatic Unified Address fallback." },
      { id: "SC-005", title: "Privacy Regression", test: "New failures, new behavior categories, and increased severity against a compatible baseline.", boundary: "Increased severity may reflect stronger observation; code-change causality is not inferred." }
    ],
    reports: [
      {
        id: "rep-leaky-01",
        path: "traces/vulnerable-client/leaky_report.json",
        result: leakyReport,
        html_id: null,
        events_id: "events-leaky-01"
      },
      {
        id: "rep-shielded-01",
        path: "traces/protected-client/shielded_report.json",
        result: shieldedReport,
        html_id: null,
        events_id: "events-shielded-01"
      }
    ],
    artifacts: [
      { id: "art-1", path: "out/demo/leaky_events.jsonl", bytes: 4965 },
      { id: "art-2", path: "out/demo/leaky_report.json", bytes: 7462 },
      { id: "art-3", path: "out/demo/shielded_events.jsonl", bytes: 11662 },
      { id: "art-4", path: "out/demo/shielded_report.json", bytes: 885 }
    ]
  });
}
