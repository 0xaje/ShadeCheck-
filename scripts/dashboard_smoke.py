"""Check the dashboard against the just-created real acceptance suite in CI."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
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
    server=create_server(suite,0,project=ROOT)
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
        site=ROOT/'out/site'
        class StaticHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path=='/api/data':self.path='/api/data.json'
                super().do_GET()
            def log_message(self,*args):pass
        static=ThreadingHTTPServer(('127.0.0.1',0),partial(StaticHandler,directory=str(site)))
        worker=threading.Thread(target=static.serve_forever,daemon=True);worker.start()
        try:
            env['SHADECHECK_DASHBOARD_URL']=f'http://127.0.0.1:{static.server_port}'
            subprocess.run(['node','tests/dashboard_browser.cjs'],cwd=ROOT,env=env,check=True,timeout=120)
            exported=json.load(urllib.request.urlopen(env['SHADECHECK_DASHBOARD_URL']+'/api/data'))
            for report in exported['reports']:
                raw=urllib.request.urlopen(env['SHADECHECK_DASHBOARD_URL']+'/download/'+report['id']).read()
                if raw!=(suite/report['path']).read_bytes():raise ValueError('Static download differs from actual report')
        finally:static.shutdown();static.server_close();worker.join()
        print('LOCAL AND STATIC RECORDED SITE VERIFIED: real reports, byte-exact downloads, browser filters and mobile layout.')
        print('All report downloads and bundle contents match real acceptance artifacts.')
        return 0
    finally:
        if server.runner:server.runner.close()
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    sys.exit(main())
