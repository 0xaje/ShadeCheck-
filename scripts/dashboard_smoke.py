"""Check the dashboard against the just-created real acceptance suite in CI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
import io

from shadecheck.dashboard_server import create_server, latest_suite

ROOT=Path(__file__).resolve().parents[1]


def main():
    suite=latest_suite(ROOT/'out/acceptance')
    if suite is None:
        raise ValueError('Run acceptance first; no runtime data is invented for UI tests')
    server=create_server(suite,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    output=ROOT/'out/dashboard';output.mkdir(exist_ok=True)
    url=f'http://127.0.0.1:{server.server_port}'
    try:
        data=json.load(urllib.request.urlopen(url+'/api/data'))
        for report in data['reports']:
            downloaded=urllib.request.urlopen(url+'/download/'+report['id']).read()
            if downloaded!=(suite/report['path']).read_bytes():
                raise ValueError('JSON download differs from actual report')
        archive=zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url+'/download/bundle').read()))
        if archive.read('suite.json')!=(suite/'suite.json').read_bytes():
            raise ValueError('Bundle differs from verified snapshot')
        chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
        if not chrome:
            raise RuntimeError('A real browser is required for the UI integration check')
        env=dict(os.environ,SHADECHECK_DASHBOARD_URL=url,CHROME_EXECUTABLE=chrome,SHADECHECK_SCREENSHOT_DIR=str(output))
        subprocess.run(['node','tests/dashboard_browser.cjs'],cwd=ROOT,env=env,check=True,timeout=120)
        print('All report downloads and bundle contents match real acceptance artifacts.')
        return 0
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    sys.exit(main())
