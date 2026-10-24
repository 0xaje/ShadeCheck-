"""Real external-client onboarding: baseline, unchanged run, changed request, CI gate.

Uses only the dedicated local regression backend. Offline --verify starts nothing.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

import grpc
import regtest as backend
from shadecheck.core import Recorder, evaluate, load_events
from shadecheck.doctor import inspect
from shadecheck.generated import service_pb2_grpc as rpc
from shadecheck.harness import start_server
from shadecheck.privacy import private_directory, private_write
from shadecheck.regression import compare_result, load_baseline

ROOT = Path(__file__).resolve().parents[1]
POLICY = {'chunk_size': 20, 'alignment_height': 0}
SCENARIOS = {'baseline-run': 0, 'unchanged-run': 0, 'changed-run': 1}


def write(path, value):
    private_write(path, json.dumps(value, indent=2, sort_keys=True) + '\n')


def cli(*args, expected=0):
    result = subprocess.run([sys.executable, '-m', 'shadecheck.cli', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    if result.returncode != expected:
        raise RuntimeError(f'CLI {args[0]} returned {result.returncode}; expected {expected}: {result.stderr.strip()}')
    print(result.stdout.strip(), flush=True)
    return result.returncode


def capture(root, name, start, end):
    directory = root / name
    private_directory(directory)
    with ExitStack() as stack:
        recorder = Recorder(directory / 'events.jsonl', 'upstream')
        stack.callback(recorder.close)
        channel = stack.enter_context(grpc.insecure_channel('127.0.0.1:9067'))
        server, port = start_server(recorder, upstream=rpc.CompactTxStreamerStub(channel))
        stack.callback(lambda: server.stop(0).wait())
        # Different process, outside the checkout: imports must come from the
        # installed package. A local in-process stub is not the consumer test.
        process = subprocess.run([sys.executable, str(ROOT / 'examples/range-client/client.py'),
                                  '--server', f'127.0.0.1:{port}', '--start', str(start), '--end', str(end)],
                                 cwd=directory, capture_output=True, text=True, timeout=45)
        if process.returncode:
            raise RuntimeError(f'External range client failed (exit {process.returncode})')
        receipt = json.loads(process.stdout)
    write(directory / 'client-receipt.json', receipt)
    proofs = [{'height': b['height'], 'block_hash': backend.node('getblockhash', b['height'])}
              for b in receipt['blocks']]
    if proofs != receipt['blocks']:
        raise RuntimeError('External client received a noncanonical block')
    write(directory / 'backend-proof.json', {'network': 'regtest', 'blocks': proofs})
    code = cli('test', '--events', directory / 'events.jsonl', '--rules', 'SC-001',
               '--config', root / 'policy.json', '--policy', 'strict',
               '--output', directory / 'report.json', expected=SCENARIOS[name])
    cli('report', '--input', directory / 'report.json', '--format', 'html',
        '--output', directory / 'report.html')
    return code


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / 'walkthrough.json').read_text())
    if manifest.get('kind') != 'shadecheck-developer-walkthrough' or manifest.get('network') != 'regtest':
        raise ValueError('Not a controlled developer walkthrough')
    inventory = manifest['artifacts']
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name != 'walkthrough.json'}
    if actual != {item['path'] for item in inventory} or len(actual) != len(inventory):
        raise ValueError('Artifact inventory differs')
    for item in inventory:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Artifact path or hash mismatch')
    if json.loads((root / 'policy.json').read_text()) != {'schema_version': 1, 'sync': POLICY}:
        raise ValueError('Walkthrough policy changed')
    results = {}
    requests = {}
    for name, expected in SCENARIOS.items():
        folder = root / name
        events = load_events(folder / 'events.jsonl')
        receipt = json.loads((folder / 'client-receipt.json').read_text())
        proof = json.loads((folder / 'backend-proof.json').read_text())
        start, end = receipt['requested_start'], receipt['requested_end']
        if [b['height'] for b in receipt['blocks']] != list(range(start, end + 1)):
            raise ValueError('Incomplete external-client receipt')
        if proof.get('network') != 'regtest' or proof['blocks'] != receipt['blocks']:
            raise ValueError('Canonical node proof differs from client receipt')
        requested = [e for e in events if e['method'] == 'GetBlockRange' and e['phase'] == 'request']
        delivered = [e for e in events if e['method'] == 'GetBlockRange' and e['phase'] == 'response']
        if (len(requested) != 1 or any(e['mode'] != 'upstream' for e in events)
                or requested[0]['metadata']['start_height'] != start
                or requested[0]['metadata']['end_height'] != end):
            raise ValueError('Actual observer request differs from receipt')
        observed = [{'height': e['metadata']['height'],
                     'block_hash': bytes.fromhex(e['metadata']['block_hash'])[::-1].hex()} for e in delivered]
        if observed != receipt['blocks']:
            raise ValueError('Observer delivery differs from external-client receipt')
        result = evaluate(events, rules=['SC-001'], sync_policy=POLICY)
        if result != json.loads((folder / 'report.json').read_text()):
            raise ValueError('Report differs from actual recorded evidence')
        if result['status'] != ('FAIL' if expected else 'PASS') or manifest['strict_exits'][name] != expected:
            raise ValueError('Unexpected policy status or recorded strict exit')
        results[name] = result
        requests[name] = (start, end)
    start, end = requests['baseline-run']
    if end - start + 1 != 20 or start % 20 or requests['unchanged-run'] != (start, end) or requests['changed-run'] != (start + 3, start + 9):
        raise ValueError('Walkthrough ranges do not represent the declared change')
    baseline = load_baseline(root / 'baseline.json')
    if baseline['result'] != results['baseline-run']:
        raise ValueError('Baseline is not the captured compliant run')
    for name, expected in [('unchanged-run', 0), ('changed-run', 1)]:
        comparison = compare_result(results[name], baseline)
        if comparison != json.loads((root / f'{name}-comparison.json').read_text()):
            raise ValueError('Baseline comparison differs from recomputed evidence')
        if comparison['baseline_comparison']['regressions'] != expected or manifest['comparison_exits'][name] != expected:
            raise ValueError('Unexpected regression or comparison exit')
    print(f'DEVELOPER WALKTHROUGH ARTIFACTS VERIFIED: {root}', flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New output directory; existing evidence is never overwritten')
    parser.add_argument('--verify', type=Path, help='Recompute a saved bundle without Docker or fresh RPCs')
    args = parser.parse_args()
    if args.verify:
        if args.output: parser.error('Use --verify or --output, not both')
        verify(args.verify)
        return 0
    if inspect()['status'] != 'READY':
        raise RuntimeError('Local prerequisites blocked. Run python -m shadecheck.cli doctor and fix its reported requirements.')
    root = (args.output or ROOT / 'out/developer-walkthrough' / (time.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])).resolve()
    if root.exists(): raise ValueError('Choose a new output directory; existing evidence is preserved')
    private_directory(root)
    print('Starting dedicated local regression backend; first build can take several minutes...', flush=True)
    backend.up()
    available = min(backend.require_regtest()['blocks'], backend.lightd_info().blockHeight)
    start = ((available + 1) // 20 - 1) * 20
    if start < 1: raise RuntimeError('No complete non-genesis historical chunk is available')
    write(root / 'policy.json', {'schema_version': 1, 'sync': POLICY})
    exits = {}
    for name, first, last in [('baseline-run', start, start + 19), ('unchanged-run', start, start + 19), ('changed-run', start + 3, start + 9)]:
        print(f'External client: {name}, blocks {first}–{last}', flush=True)
        exits[name] = capture(root, name, first, last)
    cli('baseline', 'save', '--input', root / 'baseline-run/report.json',
        '--events', root / 'baseline-run/events.jsonl', '--output', root / 'baseline.json')
    comparisons = {}
    for name, expected in [('unchanged-run', 0), ('changed-run', 1)]:
        comparisons[name] = cli('compare', '--input', root / name / 'report.json',
                                '--events', root / name / 'events.jsonl', '--baseline', root / 'baseline.json',
                                '--output', root / f'{name}-comparison.json', expected=expected)
        cli('report', '--input', root / f'{name}-comparison.json', '--format', 'html',
            '--output', root / f'{name}-comparison.html')
    write(root / 'walkthrough.json', {
        'schema_version': 1, 'kind': 'shadecheck-developer-walkthrough', 'network': 'regtest',
        'client': 'Separate Python range client using installed protocol bindings; not a full wallet',
        'strict_exits': exits, 'comparison_exits': comparisons,
        'artifacts': [{'path': p.relative_to(root).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(root.rglob('*')) if p.is_file()],
        'limitations': ['Configured completed-range policy, not a universal privacy requirement or anonymity test.',
                        'Live tip truncation, reorg/resume behavior and production privacy transports are not evaluated.',
                        'Offline verification checks consistency; local node/driver are trusted and authorship is not authenticated.',
                        'Automated clean-environment testing is not independent user adoption.']})
    verify(root)
    print(f'REAL DEVELOPER WALKTHROUGH VERIFIED: unchanged PASS; changed request FAIL; new regression FAIL. Reports: {root}', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, grpc.RpcError, subprocess.SubprocessError) as error:
        print(f'Developer walkthrough error: {error}', file=sys.stderr)
        raise SystemExit(2)
