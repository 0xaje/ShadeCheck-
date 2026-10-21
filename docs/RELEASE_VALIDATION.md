# Submission-hardening validation — October 21, 2026

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
