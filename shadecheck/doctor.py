"""Read-only prerequisites for controlled local tests; no chain or wallet creation."""
import subprocess
import sys


def inspect():
    checks=[{'name':'Python 3.11+','ok':sys.version_info>=(3,11),'detail':'.'.join(map(str,sys.version_info[:3]))}]
    for name,args,accept in [
        ('Docker Linux engine',['docker','info','--format','{{.OSType}}'],lambda x:x.strip()=='linux'),
        ('Docker Compose v2',['docker','compose','version','--short'],lambda x:x.strip().lstrip('v').split('.')[0].isdigit() and int(x.strip().lstrip('v').split('.')[0])>=2),
    ]:
        try:
            value=subprocess.run(args,capture_output=True,text=True,timeout=15)
            ok=value.returncode==0 and accept(value.stdout)
            detail=value.stdout.strip()[:60] if ok else 'Unavailable: start Docker with Linux containers and install Docker Compose v2.'
        except (OSError,subprocess.TimeoutExpired):
            ok=False;detail='Unavailable: install/start Docker Desktop or Docker Engine with Compose v2.'
        checks.append({'name':name,'ok':ok,'detail':detail})
    return {'status':'READY' if all(x['ok'] for x in checks) else 'BLOCKED','checks':checks,
            'scope':'Local prerequisites only; does not validate wallet behavior or privacy.'}
