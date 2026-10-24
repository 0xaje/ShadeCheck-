# Submission and deployment checklist

1. Require green unit, protocol-conformance, real acceptance, browser, package-install, and consumer-gate checks on the release commit.
2. Confirm the demo never creates events and fails without a validated recorded run.
3. Export the public site from a real completed acceptance directory with the exact CI run URL and source commit. Exported findings are read from recomputed reports, not typed into JavaScript.
4. Serve the exported `public` directory. Vercel configuration rewrites only `/api/data`; artifact URLs must serve the actual exported files, not fall back to index.html.
5. Open the public URL on desktop and mobile. Verify source run link, empty/error states, status/rule filters, baseline before/after values, all downloads, and bundle revalidation.
6. The public site shows recorded evidence. It has no live scan button. Fresh execution is available through the local acceptance command or GitHub Actions workflow_dispatch (fork the repository to run it with your own account).
7. Keep repository tokens server-side if a hosted execution service is added. Do not expose a token in the static viewer. Restrict any worker to controlled regtest scenarios; arbitrary URL scanning is outside scope.
8. Record the two-minute video from actual execution/evidence. Note any pre-warmed backend or edited waiting periods. Include a clear PASS-not-anonymity boundary.
9. Submit the correct track, description, public repository, public recorded-demo URL, and video. Recheck the organizer's authenticated submission form and current rules before sealing the submission.

## Installed package check

Build a wheel, install it in a fresh virtualenv, change out of the repository, then run `shadecheck --help` and `shadecheck demo --suite ABSOLUTE_PATH`. The latter must read validated evidence and must not rely on a repository-only scripts folder. Without evidence it returns an error instead of synthesizing a result.

## Consumer integration

Run your client through the observer before invoking the Action. Only the supported RPCs are currently forwarded. Use explicit sync/payment policy configuration for the corresponding rules. Failures must be required checks in the consumer repository to enforce merges. A negative test may continue temporarily only when a subsequent assertion requires exact exit 1 and a valid expected finding; execution errors must not pass that assertion.

## Current trust boundary

The public export is an auditable snapshot of a controlled run, not remote attestation. Hashes detect accidental/inconsistent edits but do not authenticate an author. The recorded native adapter and node are trusted, and all wallets/keys are local test wallets. A successful suite verifies expected PASS, WARN, and FAIL behavior; it does not certify the sample architecture as private.

## Deploy the prepared public snapshot on Vercel

Import this GitHub repository into your Vercel account (or redeploy its existing project). Use the repository root, framework Other, and output directory `public`. The committed vercel.json skips build/install commands because this is a prevalidated static export, rewrites `/api/data` to the generated JSON, and supplies the recorded-run ZIP download header. No Zcash wallet keys, GitHub token, or runtime API secrets are required by the public viewer.

Check the deployment URL Vercel actually assigns; no deployed URL is assumed or fabricated in this repository. Open `/api/data`, inspect source commit/run metadata, download a report and the run ZIP, and run offline validation on the extracted suite. The static site is not a hosted execution service. Use `shadecheck dashboard --enable-runner --project .` for local controlled execution, or fork/run the existing GitHub Actions workflow for fresh remote execution.

The committed recorded export was generated and browser-tested by the source CI run documented in RELEASE_VALIDATION.md. Regenerate exports from a new verified suite when replacing its recorded data; do not hand-author findings or status values.

## Public evidence review

The exporter now requires `--acknowledge-public-evidence` and a validated controlled regtest suite. Read [evidence handling](evidence-privacy.md), review the full artifact inventory, and publish only disposable local test data. Public downloads intentionally retain original bytes; this is not an automatic redaction service.
