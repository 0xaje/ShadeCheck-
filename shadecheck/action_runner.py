"""Composite Action entry point. Inputs are data, never shell interpolation."""
import json
import os
from pathlib import Path
import shutil
from .cli import main as cli


def main():
    try:
        output = Path(os.environ.get('SC_OUTPUT', 'out/shadecheck'))
        output.mkdir(parents=True, exist_ok=False)
        events, fixture = os.environ.get('SC_EVENTS', ''), os.environ.get('SC_FIXTURE', '')
        if bool(events) == bool(fixture):
            raise ValueError('Supply exactly one of events or fixture. No fixture is selected implicitly.')
        args = ['test', '--policy', os.environ.get('SC_POLICY', 'strict'), '--output', str(output/'report.json'),
                '--rules', *os.environ.get('SC_RULES', 'SC-002').split()]
        if events:
            shutil.copyfile(events, output/'events.jsonl')
            args += ['--events', str(output/'events.jsonl')]
        else:
            args += ['--fixture', fixture, '--record', str(output/'events.jsonl')]
        for env, flag in [('SC_CONFIG', '--config'), ('SC_BASELINE', '--baseline')]:
            if os.environ.get(env):
                args += [flag, os.environ[env]]
        code = cli(args)
        report = output/'report.json'
        if report.exists():
            result = json.loads(report.read_text())
            for fmt, suffix in [('html','html'),('markdown','md')]:
                if cli(['report','--input',str(report),'--format',fmt,'--output',str(output/f'report.{suffix}')]) != 0:
                    return 2
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                    f.write(f"status={result['status']}\nfindings_count={len(result['findings'])}\nreport_path={report.as_posix()}\nexit_code={code}\n")
            if os.environ.get('SC_SUMMARY','true') == 'true' and os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
                    f.write((output/'report.md').read_text())
        return code
    except (OSError, ValueError) as error:
        print(f'ShadeCheck Action error: {error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
