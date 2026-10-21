"""Verify a built wheel outside the source checkout against actual saved evidence."""
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT=Path(__file__).resolve().parents[1]


def main():
    suite=sorted((ROOT/'out/acceptance').iterdir())[-1]
    wheels=ROOT/'out/wheels'
    subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','.', '-w',str(wheels)],cwd=ROOT,check=True)
    wheel=next(wheels.glob('shadecheck-*.whl'))
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);venv.EnvBuilder(with_pip=True).create(root/'venv')
        python=root/'venv'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
        subprocess.run([str(python),'-m','pip','install',str(wheel)],cwd=root,check=True)
        subprocess.run([str(python),'-I','-m','shadecheck.cli','--help'],cwd=root,check=True,stdout=subprocess.DEVNULL)
        run=subprocess.run([str(python),'-I','-m','shadecheck.cli','demo','--suite',str(suite)],cwd=root,check=True,capture_output=True,text=True)
        if 'RECORDED REGTEST EVIDENCE WALKTHROUGH' not in run.stdout or (root/'out').exists():
            raise ValueError('Installed demo did not preserve the recorded-only contract')
        missing=subprocess.run([str(python),'-I','-m','shadecheck.cli','demo'],cwd=root,capture_output=True,text=True)
        if missing.returncode!=2:raise ValueError('Missing evidence did not fail closed')
    print('INSTALLED WHEEL VERIFIED: external directory, recorded evidence, missing-evidence error, no fabricated events.')


if __name__=='__main__':main()
