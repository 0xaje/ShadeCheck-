"""A recorded walkthrough of validated real acceptance evidence, never a simulator."""
from pathlib import Path
import json
from .suite import verify
from .dashboard_server import latest_suite


def run_demo(suite=None):
    root = Path(suite) if suite else latest_suite(Path('out/acceptance'))
    if root is None:
        raise ValueError('No recorded run. Run python scripts/acceptance.py first, or supply --suite PATH.')
    verify(root)
    summary = json.loads((root / 'suite.json').read_text())
    print('RECORDED REGTEST EVIDENCE WALKTHROUGH — no new transaction or network test is executed.')
    print(f'Run: {root.name}')
    print(f"Acceptance: {summary['acceptance_status']}; aggregate privacy: {summary['privacy_status']}")
    for entry in summary['reports']:
        if any(term in entry['report'] for term in ['transparent-fallback', 'regressed-comparison', 'severity-increase']):
            report = json.loads((root / entry['report']).read_text())
            print(f"{entry['report']}: {report['status']}; {len(report['findings'])} findings; evidence root {report['evidence_root']}")
    print('A shielded payment can still expose broadcast linkage. PASS applies only to selected tests.')
    print(f'Inspect: shadecheck dashboard --suite "{root}"')
    return 0
