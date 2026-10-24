# Connect a controlled client and choose a useful CI requirement

First complete the [getting-started walkthrough](GETTING_STARTED.md). The small [range client](../examples/range-client/client.py) is an integration example, not a wallet. Existing wallet integrations require their own supported RPCs, network parameters and reproducible workflow.

## Write the requirement before enabling a gate

Record four things in your integration documentation:

1. Observer: which service can see the requests?
2. Promise: which behavior should that observer not see, or which explicit batching policy should it see?
3. Exercise: which real client workflow provides the required rule coverage?
4. Action: what code/configuration would a developer investigate if it fails?

For this example, the observer serves historical compact blocks; the application promises fixed-size aligned batches for a completed range. A narrower request is a scheduling-policy regression, not proof of wallet ownership or a newly discovered Zcash vulnerability.

A direct broadcasting service inherently receives submitted bytes. SC-002 is appropriate only when that visibility matters to the declared trust model. Hiding a label or removing observation coverage does not establish a privacy improvement.

## Capture actual traffic

Start the dedicated local backend with `python scripts/regtest.py up`. In terminal A:

```bash
python -m shadecheck.cli observe --upstream 127.0.0.1:9067 --plaintext-upstream --port 9068 --output out/my-client/events.jsonl
```

Keep that terminal open. The observer listens on loopback. Plaintext is explicit here for controlled local regtest; use the supported TLS upstream configuration for another approved test environment. No spending key is sent to ShadeCheck.

In terminal B, run your real client against `127.0.0.1:9068`. The example below requests historical heights 80–99, which the initialized local backend must already contain:

```bash
python examples/range-client/client.py --server 127.0.0.1:9068 --start 80 --end 99
```

Wait for the client to complete, then stop terminal A with Ctrl+C. Use a new event path for each run; the recorder refuses to overwrite evidence. The [automated walkthrough](GETTING_STARTED.md) also independently compares every returned block hash with the node.

Create a policy file named `my-policy.json`:

```json
{"schema_version":1,"sync":{"chunk_size":20,"alignment_height":0}}
```

Evaluate only the rule exercised here:

```bash
python -m shadecheck.cli test --events out/my-client/events.jsonl --rules SC-001 --config my-policy.json --policy strict --output out/my-client/report.json
python -m shadecheck.cli report --input out/my-client/report.json --format html --output out/my-client/report.html
```

The complete aligned example should return exit 0. A complete request for heights 83–89 should produce SC-001 and exit 1 under the same policy. Neither result establishes anonymity. Missing coverage, invalid input or execution errors require investigation; strict WARN/errors return 2.

## Baseline and changed behavior

Save the compliant report with its actual evidence:

```bash
python -m shadecheck.cli baseline save --events out/my-client/events.jsonl --input out/my-client/report.json --output my-baseline.json
```

Capture your changed application to a different event file, then:

```bash
python -m shadecheck.cli test --events out/changed/events.jsonl --rules SC-001 --config my-policy.json --baseline my-baseline.json --policy strict --output out/changed/report.json
```

Keep the backend, scenario and requirement comparable. The baseline validates existing evidence; it cannot exempt a known strict failure. A new request pattern does not by itself prove that a particular code change caused it.

## Consumer GitHub Action

Your preceding integration step must start/stop the observer and run the real client. Replace these example paths with the output of that step. The Action evaluates supplied evidence; it does not launch arbitrary wallet code automatically.

This is a job fragment, not a complete workflow file: place `steps` under your own job, and set `permissions` at workflow or job scope. For a complete executable example, use the linked onboarding workflow.

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@v4
  # Run the controlled backend, observer and real client here.
  - name: Enforce the declared range policy and baseline
    uses: 0xaje/ShadeCheck-@bbbbd166279edcbb92819dddaac6dc2443d6432e
    with:
      events: out/changed/events.jsonl
      config: my-policy.json
      baseline: my-baseline.json
      rules: SC-001
      policy: strict
      output-dir: out/privacy-gate
  - uses: actions/upload-artifact@v4
    if: always()
    with:
      name: private-test-evidence
      path: out/privacy-gate/
      retention-days: 7
```

Configure this check as required in the consumer repository if you intend it to block merges. GitHub repository visibility and artifact permissions determine who can read uploaded evidence; the name “private-test-evidence” is not access control. Use throwaway regtest data for public CI, and review [evidence handling](evidence-privacy.md).

The repository's [real onboarding workflow](../.github/workflows/developer-onboarding.yml) contains a complete executable consumer example with both positive and negative gates. Its negative case allows failure only temporarily, then requires exact exit 1 plus SC-001 and SC-005 findings. An arbitrary process error cannot make that workflow pass.
