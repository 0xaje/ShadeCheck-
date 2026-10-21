"""Export byte-exact verified recorded evidence as a self-contained public site."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shadecheck.dashboard_server import snapshot, display_safe


def export(suite, output, run_url, commit):
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+',run_url):
        raise ValueError('A source GitHub Actions run URL is required')
    if not re.fullmatch(r'[0-9a-f]{40}',commit):
        raise ValueError('A full source commit SHA is required')
    payload, files = snapshot(suite)
    payload['suite']['source']={'run_url':run_url,'commit':commit,'kind':'recorded-regtest-acceptance'}
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'api').mkdir();(output/'download').mkdir()
    (output/'api/data.json').write_text(json.dumps(display_safe(payload),sort_keys=True)+'\n')
    assets=Path(__file__).resolve().parents[1]/'shadecheck/dashboard'
    for name in ['index.html','style.css','app.js']:
        shutil.copyfile(assets/name,output/name)
    for key, (_,data) in files.items():
        (output/'download'/key).write_bytes(data)
    (output/'provenance.json').write_text(json.dumps(payload['suite']['source'],indent=2)+'\n')
    print(f'Verified recorded site exported: {output}; {len(payload["reports"])} reports; source {run_url}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-run-url',required=True);p.add_argument('--source-commit',required=True)
    a=p.parse_args();export(a.suite,a.output,a.source_run_url,a.source_commit)
