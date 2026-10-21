# ShadeCheck — final demo recording guide

Target: approximately two minutes, landscape 16:9, readable 1080p footage.
This is the primary recording plan. Rehearse timing before the final export.
The organizer submission form requests a two-minute video; keep the complete export at or below two minutes.

## 1. Understand the demonstration

Zcash shielding protects transaction information. Application requests can still
expose observable clues. ShadeCheck records defined behaviors, evaluates explicit
rules, and gives developers evidence-backed results and baseline comparisons.

The video demonstrates detection, a controlled change in behavior, and a
regression check. The public site shows saved real evidence; the local runner
executes a fresh controlled test. Neither establishes anonymity or universal
wallet compatibility. The native-wallet transaction scenarios and Zingo sync
experiment are separate workflows; do not present them as one Zingo transaction.

Two green/red meanings must stay separate:

- Acceptance PASS: the harness verified its expected outcomes.
- Privacy FAIL: at least one selected privacy requirement was violated.

The acceptance suite includes deliberately weak configurations. These expected
FAIL reports do not mean the test harness failed.

## 2. Prepare before recording

Public viewer: https://shade-check-nu.vercel.app/
Local viewer: http://127.0.0.1:9070/
Independent-client CI: https://github.com/0xaje/ShadeCheck-/actions/runs/39599061669
Evidence and reproduction: https://github.com/0xaje/ShadeCheck-/tree/main/examples/zingo

Keep Docker Desktop running. Keep the terminal hosting the local dashboard open.
If the dashboard is already working, do not restart or rerun acceptance merely
for recording. If it is stopped, run these Bash/WSL commands from the checkout:

```bash
cd ~/ShadeCheck-
./.venv/bin/python scripts/regtest.py up
./.venv/bin/python -m shadecheck.cli dashboard --enable-runner --project .
```

Use a second terminal for other commands; the dashboard terminal stays occupied.
If you need the latest source, stop the dashboard first, run `git pull --ff-only`
and `./.venv/bin/python -m pip install .`, then restart it. Existing saved runs
remain available. A new full acceptance run is not needed for each video take.

Open three tabs, ordered public viewer, local viewer, independent-client CI.
The Zingo result is a previous CI execution; do not claim it is running locally
unless you actually build and run the separate integration.

Use your existing screen recorder/editor. Capture landscape at 1080p, enable
Do Not Disturb, close unrelated tabs, and use a readable browser zoom. Record
screen footage first and the narration separately if that feels easier. You do
not need to appear on camera. Keep background music absent or quiet enough that
every word is clear. Do not show wallet files, seeds, keys or unrelated accounts.

### Optional OBS setup on Windows

If you need a recorder, OBS Studio's official quick-start guide is at
https://obsproject.com/kb/quick-start-guide (download from the official OBS site).

1. Run its Auto-Configuration Wizard for recording.
2. Under Sources, add Window Capture for the browser, or Display Capture for the screen.
3. In the Audio Mixer, confirm the microphone meter responds; use Settings > Audio to select the microphone if needed.
4. Check Settings > Output, make a short test recording, and play it back before the final take.

Use landscape 1080p when your computer supports it. You can record narration
separately in your existing editor. Avoid installing new tools if your current
recorder already captures readable screen footage and clear audio.

## 3. Exact navigation rehearsal

### A. Public summary

Open the public viewer and show the top summary cards: Acceptance PASS,
Aggregate privacy FAIL, 24 saved reports, five executed families. The sidebar
says Recorded evidence. The source CI link refers to that specific saved run.
Scroll down to Test reports when moving to the finding.

### B. Shielded broadcast evidence — SC-002

In Reports, set Status to All statuses, Rule to SC-002, and type
`separated/broadcast-observer` in Search. Click the matching report in the left
list if necessary. It is the default report in the currently deployed snapshot.

The right panel shows HIGH and “Broadcast payload linked to a transport
session.” Expand “Current evidence · 3 events.” Point briefly to SendTransaction,
its response error_code 0, and GetMempoolStream. The submission and mempool events
have the same payload_sha256. This is a byte fingerprint, not the Zcash txid.

This saved scenario used an actual shielded transaction. Its separate backend
proof is available through Artifacts, but do not spend the short video searching
through all files. Do not claim the observer identified the person sending it.

### C. Fresh local sync comparison — SC-001

Switch to the localhost tab. At the top, click “Run real sync comparison” once.
Expand “Actual execution log” and wait for completed status. Keep the actual
button click and final output in your footage. Expected log:

- narrow: FAIL, 1 finding;
- aligned: PASS, 0 findings;
- REAL SC-001 COMPARISON VERIFIED;
- completed, process exit 0 for the orchestration.

Process exit 0 means the comparison verified both expected outcomes. The weak
case's own strict gate fails; do not say the overall successful orchestration
returned exit 1. The result buttons download JSON, not an HTML detail view.

The public table does not refresh from this local test. These are different runs.
If you later use the public narrow/aligned reports, label them saved examples,
not the outputs of this fresh local execution. Do not say the test changed Zingo.
This comparison uses the existing controlled protocol client.

Allow the test to finish. If editing removes waiting time, add “Wait shortened”
while making the cut. If it fails unexpectedly, stop and troubleshoot. Do not
substitute old output and present it as this run.

### D. Saved baseline comparison — SC-005

Return to the public viewer. Click Reports. Reset Status to All statuses,
select Rule SC-005, clear the previous Search text, and search
`unchanged-comparison`. Click the result. Show Baseline comparison: PASS,
0 regressions.

Replace Search with `regressed-comparison`. Click that result. Show Baseline
comparison: FAIL, 1 regression, with an SC-001 new failure. The report can contain
two findings because it includes the underlying SC-001 finding and its SC-005
regression finding; do not call that two independent leaks.

The important story is a saved compatible baseline versus an actual changed
request pattern. This is not proof that a specific wallet code change caused it.
Strict failing exits are asserted in the reproducible drivers/CI. The public
badge alone is not a live process-exit demonstration.

### E. Independent client proof

Switch to the Zingo CI tab, open the successful zingo job, then expand
“Real direct and observed wallet synchronization.” Scroll to the actual final
verification line: direct and observed scanning completed; 101 canonical blocks.
The run also records 124 events. Rehearse this tab before recording, so you do
not spend video time finding the log. A pre-opened CI log is recorded evidence,
not a fresh execution.

The upstream source release is zingolib_v3.0.1 at the pinned revision. Its binary
prints Zingo CLI 0.1.1; do not invent a newer binary version. The coverage is a
fresh unfunded wallet sync. Other payment/broadcast workflows and current
production transport settings are not validated by this experiment.

### F. Finish

Return to the public viewer. Clear Search and reset Rule to All rules. At the
top, click Download run. Keep the successful download visible briefly. The ZIP
contains original evidence/report artifacts. Finish on the ShadeCheck title.

## 4. Timeline and exact narration

Aim for a calm pace around 115–125 words per minute, with short pauses.
The combined script is about 215 words. Time your own reading: the timings are
editing targets, not a reason to rush or hide a slow real test.

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00–0:15 | Public title | Zcash can shield a transaction, while the application around it still reveals clues. ShadeCheck helps wallet and SDK developers test defined privacy behaviors before releasing a change. |
| 0:15–0:27 | Summary cards | This dashboard shows a recorded real regtest run. Acceptance passed because the expected outcomes were verified, including deliberately weak configurations that should fail. |
| 0:27–0:50 | SC-002 HIGH and expanded evidence | Here, the observer saw a real shielded transaction being submitted and identical bytes appearing in the mempool. ShadeCheck reports a HIGH finding because those bytes can be linked to the broadcasting connection. This identifies a connection, not a person. |
| 0:50–1:12 | Fresh local sync comparison | Now I’m running a fresh local sync comparison. The narrow request fails our configured policy; the aligned request passes. The execution log and downloadable reports show what actually happened. |
| 1:12–1:34 | Unchanged, then regressed baseline | ShadeCheck also compares saved baselines. An unchanged run has no regression. A narrower sync request introduces a new failure. Strict policy returns a nonzero exit code, allowing a CI workflow to fail. |
| 1:34–1:50 | Successful Zingo CI log | We verified synchronization using an unmodified, pinned Zingo client: 101 blocks checked against the node and 124 recorded events. That integration has its own documented coverage limits. |
| 1:50–2:00 | Download and title | Developers can inspect the evidence, reproduce the tests, and integrate the checks into CI. Passing ShadeCheck does not establish anonymity. |

If the fresh sync takes longer than its segment, preserve the real click and
result and clearly label a shortened wait. Do not claim a guaranteed runtime.

## 5. On-screen captions

Use short captions, not a second paragraph of text over the application:

- Public scenes: “Recorded real regtest evidence”.
- SC-002: “Shielded bytes can still be linked to a connection”.
- Local scene: “Fresh local execution · controlled regtest”.
- Comparison result: “Narrow FAIL → aligned PASS · selected sync policy”.
- Baseline: “Detect regressions against saved evidence”.
- Zingo: “Pinned independent client · unfunded regtest sync”.
- Closing: “Privacy CI for Zcash applications”.

Keep captions away from finding titles, statuses, evidence and the address bar.
A giant acceptance PASS should never obscure the aggregate privacy FAIL.

## 6. What you do not need to explain in the short video

Do not walk through all five rules, Docker installation, proving internals,
cryptographic hashes, or every JSON field. The rule library and documentation
provide that depth. Do not call the product an automatic scanner for any URL or
wallet. The CLI/CI harness is the product; the dashboard exposes its evidence and
controlled local execution.

Do not claim anonymity, universal support, first/only status, new vulnerability
discovery, third-party adoption, or endorsement. A policy mismatch is not by
itself a security vulnerability. A hash chain checks integrity, not authorship.

## 7. Final export check

Watch the exported file once from beginning to end. Confirm readable text, clear
audio, actual completed local output, saved/live labels, correct FAIL/PASS
interpretation, and no unrelated/private content. Confirm video length against
the actual submission form before uploading; shorten pauses and navigation
before removing evidence. Keep the original footage and local run files.

Video title suggestion: “ShadeCheck — Privacy CI for Zcash Applications”.

The deployed viewer, repository and independent-client log should be linked in
the video description. Add the actual uploaded video URL to the repository only
after upload. No video has been recorded or uploaded by this guide.
