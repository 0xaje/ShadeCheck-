# Independent reader exercise

Status: **not yet independently performed**. Automated fresh-environment CI is a separate check. Do not mark this exercise passed because the project's author or assistant can run the commands.

Give an unfamiliar Zcash/Python developer only the repository URL and [getting-started guide](GETTING_STARTED.md). Ask them to use a fresh directory, throwaway local test data and their usual computer. Do not send seeds, private evidence or account credentials.

Ask them to:

1. Install ShadeCheck and explain whether they are inspecting saved evidence or running a fresh test.
2. Revalidate the saved current-wallet artifact and locate its findings and limitations.
3. Run doctor, resolve any setup block, and complete the fresh developer walkthrough.
4. Find the baseline, unchanged result and changed-request regression.
5. Explain why the harness can succeed while an intentionally violating privacy report fails.
6. Describe whether the example policy is appropriate for their own architecture and which code they would investigate.
7. Find how to connect a client and enforce a CI check.

Record the actual OS/Python/Docker versions, source commit, time spent, help requested, exact failing commands, confusing instructions and whether each task completed. Keep personal details optional and private. A maintainer should fix observed problems, then have the reader retry only affected steps.

There is no claimed completion time until it has been measured. If the reader needs live assistance, record it rather than calling the process unaided. Their successful exercise demonstrates one person's onboarding; it is not broad adoption, production compatibility or an anonymity audit.
