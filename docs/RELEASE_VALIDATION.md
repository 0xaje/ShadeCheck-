# Privacy hardening validation — October 24, 2026

Source commit: `74d2f8f199ed2b631c899aef8a25c722f4deeee4`.

[Real acceptance run 40081554868](https://github.com/0xaje/ShadeCheck-/actions/runs/40081554868) passed 53 unit/boundary checks, all five rule families on the controlled regression backend, consumer gate exit assertions, an installed-wheel check, and browser/local-runner checks. The original downloaded archive has SHA-256 `265f33cf4061140a0d83639fbf293f21c9840dd8a9591c58d972c0cada211853`. Offline verification revalidated 24 reports and 112 hashed acceptance artifacts. The committed public snapshot was refreshed from this exact run.

Fresh recordings now use per-run keyed session identifiers, omit arbitrary backend broadcast response text, and retain compatibility-only message fingerprints without raw RPC bodies. Evidence files use private POSIX permissions. Public export requires explicit acknowledgement and a validated controlled regtest suite. These controls reduce retained data; they do not make transaction fingerprints or exported metadata anonymous. See [evidence handling](evidence-privacy.md).

The read-only `shadecheck doctor` command checks prerequisites and reports a blocked setup clearly. Its READY state is not a privacy test result. [Rule applicability](rule-applicability.md) explains which requirements fit which observers and distinguishes configured policy failures from discovered vulnerabilities.

The [current-release funded-wallet gate](modern-wallet.md) has separate execution status and coverage. A source build or an incomplete runtime is not a verified integration. The historical checks below remain an audit record, not claims that their older components are the recommended current production stack.

---

## Historical submission-hardening validation — October 21, 2026

Source commit: `c3ce35f93979eae57fa91c394be2bf7ced3d3e1a`

Source run: https://github.com/0xaje/ShadeCheck-/actions/runs/39577173119

The code revision above passed:

- 37 unit/boundary tests, including missing-evidence demo errors, explicit Action source selection, untrusted Markdown text escaping, and fixed-runner HTTP/token boundaries.
- Actual regtest acceptance with all five rule families, transparent and shielded transaction proofs, exact mempool bytes, independent node checks, portable baselines, JSON/HTML output, and strict exit assertions.
- The real aligned consumer Action gate passed; the actual narrow consumer gate returned exact exit 1 and the expected SC-001 finding. Execution errors were not accepted as negative-test success.
- A built wheel installed into a fresh virtual environment and executed outside the source checkout. Its demo read real saved evidence, did not create runtime events, and failed without evidence.
- Chrome checks on both localhost and the exported static recorded site: filters, evidence, precision-preserving timestamp strings, baseline severity changes, real downloads, rule/artifact counts, and mobile width.
- A browser-launched actual local sync comparison job. It completed with process exit 0 after validating its required PASS and FAIL reports. The new job traces were independently recomputed afterward.

The downloaded CI artifact was independently audited: 24 reports and 112 hashed acceptance artifacts revalidated. Its public export includes 114 downloadable acceptance files (the manifest adds suite.json/suite.html), a ZIP, original event/report downloads, and source run/commit provenance. The static export contains no execution token or synthetic findings.

## Corrected issues

- Removed synthetic demo events labeled upstream, fabricated transaction-shaped payloads, hard-coded hosted findings/PASS states, and simulated privacy guarantees.
- Replaced the demo with a packaged recorded-evidence walkthrough.
- Removed implicit Action fixture selection and shell interpolation of inputs; preserved exact gate exits and explicit protocol-test separation.
- Fixed dashboard mobile navigation overflow and packaged-demo path resolution.
- Added portable Windows/POSIX npm launchers and a project MIT license while retaining upstream notices.
- Added opt-in loopback execution of fixed regtest commands with actual logs, single-job concurrency, timeout/termination, and validation before report download.
- Rewrote submission claims to preserve the actual observer, adapter, integrity, and coverage boundaries.

## Remaining human/account checks

A Windows user should pull/install and exercise the new local runner on their own Docker Desktop installation. The earlier core acceptance suite was verified on Windows; this newer runner has been verified in Linux CI, not represented as already tested on the user's Windows machine.

A Vercel deployment URL has not been verified from this environment. The repository contains the complete static public export and configuration. Deploy in the account that owns the project, then test that assigned URL and downloads.

Record the submission video and complete the organizer's submission form using the reviewed code/data. Keep evidence labelled recorded where applicable. Configure required checks in a consumer repository to enforce merge restrictions; ShadeCheck does not approve or merge PRs itself.

These checks demonstrate the documented test scope. They are not a claim of complete anonymity, universal wallet support, authenticated evidence authorship, or production security certification.

## Independent-client gate — October 21, 2026

Source revision: `48e11f0b006fa2ad4fe4cefba027e6ea8a235196`.

[Dedicated real Zingo CI](https://github.com/0xaje/ShadeCheck-/actions/runs/39599061669)
passed with 42 unit/boundary tests, an unmodified pinned upstream source build,
and successful direct and observed block scanning. Both clients scanned heights
10–110; 124 events were recorded and all 101 delivered compact block hashes
matched the separate canonical node. The report returned FAIL/strict exit 1 with
two SC-001 MEDIUM findings under the explicit 20-block policy. Other selected
families remained uncovered; SC-005 was not selected. This is a compatibility
and defined-policy experiment, not a Zingo vulnerability or production audit.

The original 89,718-byte CI artifact is committed under `examples/zingo`, with
archive SHA-256 `df27331727aebb1230daa8eb198fed565f6ce0c3db81bf58f944c126451ef4f9`.
It was downloaded, hash checked, extracted, and revalidated offline. No wallet
files/keys are included. Full scope and reproduction: [Zingo integration](zingo-integration.md).

The observer change also passed the existing [real MVP acceptance workflow](https://github.com/0xaje/ShadeCheck-/actions/runs/39597614943),
including real backend scenarios and dashboard/browser checks. This new separate
integration does not replace or merge the original 24-report acceptance snapshot.
