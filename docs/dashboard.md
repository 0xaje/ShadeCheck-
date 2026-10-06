# Local evidence dashboard

The dashboard is secondary to the CLI. It reads a completed acceptance run, validates the artifact hashes and event chains, recomputes its reports and baselines with the same acceptance validator, then serves a fixed snapshot on localhost.

No sample findings, placeholder transactions, privacy scores, remote analytics, or background network tests populate this view. With no saved acceptance run it shows an empty state. An explicitly selected invalid run fails startup; the default chooses the newest acceptance directory and does not silently fall back to an older successful run.

## Windows

From the repository after a successful acceptance run:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\shadecheck.exe dashboard
```

Open http://127.0.0.1:9070 in your browser. Keep PowerShell open while viewing; Ctrl-C stops the server. The default loads the newest out/acceptance directory relative to your current working directory. To select a run explicitly:

```powershell
.\.venv\Scripts\shadecheck.exe dashboard --suite .\out\acceptance\20261006T044416-934b9551
```

An alternative port can be selected with --port. Linux: `shadecheck dashboard --suite <acceptance-directory>`.

The interface is packaged HTML/CSS/JavaScript served by Python's standard-library HTTP server. No Node installation, frontend build, CDN, or browser-side dependency download is required to use it. Browser automation dependencies are used only in CI.

## Views

- Reports: filter by status and rule, search paths/findings, and select a saved trace.
- Detail: policy result, actual coverage, findings, investigation direction, source evidence, evidence root, and limits.
- Baseline comparison: comparison status, change categories, previous/current severity, baseline evidence, and complete comparison metadata.
- Rule library: exactly five implemented families, each with its documented coverage boundary.
- Artifacts: downloads of actual files in the verified snapshot, including JSON, JSONL events, HTML, backend proof, baseline, and logs.
- Download run: a ZIP of the loaded snapshot, preserving the original artifact bytes.

Counts derive from the loaded report index and rule list. The acceptance and aggregate privacy statuses are separate: acceptance PASS verifies required test behavior; deliberate weak flows and broadcast linkability still produce privacy FAIL. A report PASS is limited to its selected rules and coverage and does not establish anonymity.

## Evidence precision and trust

JavaScript cannot exactly represent all nanosecond integers. The display API converts integer values larger than 2^53-1 to exact decimal strings. The UI labels this representation; JSON and event downloads preserve their original bytes and numeric types. It does not reinterpret transaction payload fingerprints as transaction IDs.

The loaded snapshot stays fixed. Restart the dashboard to load a newly generated run. It does not start tests, submit payments, change policies, save baselines, alter findings, or export spending keys. Server binding is limited to 127.0.0.1. This is a local developer tool, not a hosted service with authentication or remote-access support.

Artifact validation detects mismatched hashes and reports; it does not authenticate an author or prove that maliciously rewritten evidence came from the original test environment. Native adapter and node trust remain as documented in the threat model. Reports can contain sensitive test metadata; the same care applies to downloaded bundles.

## Validation

Unit checks cover empty states, packaged asset delivery, loopback host enforcement, rejection of non-artifact downloads, and exact large-integer display. The real browser check uses an actual newly generated acceptance run. It requires correct status/rule filters, saved findings, MEDIUM-to-HIGH comparison, inspectable timestamp strings, report download, the five-rule library, artifact counts, search empty state, and no horizontal overflow at mobile width. All report downloads and bundle content are checked against source bytes. Desktop/mobile screenshots are included in the real CI artifact.

## Verified real CI

[Run 37411834768](https://github.com/0xaje/ShadeCheck-/actions/runs/37411834768) passed on October 6, 2026: 32 unit tests, the fresh real acceptance suite, and Chrome browser integration. It generated the actual data before UI checks; no fabricated finding or browser test dataset supplied runtime results. All 24 JSON downloads matched their source bytes, and the run ZIP preserved the original suite metadata. Desktop/mobile screenshots were reviewed after downloading the artifact. The dashboard showed acceptance PASS separately from aggregate privacy FAIL, displayed baseline MEDIUM-to-HIGH evidence, and passed filters, search, artifact counts, rule-library, download, timestamp precision, and mobile layout checks. Windows dashboard launch awaits verification; the core acceptance run is already verified on Windows.
