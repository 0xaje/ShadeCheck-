"""Opt-in loopback execution of fixed local regtest commands. No arbitrary shell input."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid
from .core import load_events
from .regression import recompute
from .suite import verify
from .privacy import private_open, private_directory


class BusyError(ValueError): pass


class LocalRunner:
    SCENARIOS={'acceptance':'acceptance.py','sync-pattern':'sync_pattern.py'}

    def __init__(self, project):
        self.project=Path(project).resolve()
        for path in ['scripts/acceptance.py','scripts/sync_pattern.py','integration/compose.yml']:
            if not (self.project/path).is_file():raise ValueError('Runner requires a ShadeCheck source checkout with integration services')
        self.lock=threading.RLock();self.state={'status':'idle','logs':[]};self.process=None;self.files={};self.started=None;self.ended=None

    def get(self):
        with self.lock:
            value=dict(self.state);value['logs']=list(self.state['logs'])
            if self.started:value['elapsed_seconds']=int((self.ended or time.monotonic())-self.started)
            return value

    def start(self, scenario):
        if scenario not in self.SCENARIOS:raise ValueError('Unknown controlled scenario')
        with self.lock:
            if self.state['status'] in {'queued','running','validating'}:raise BusyError('A controlled test is already running')
            key=uuid.uuid4().hex
            directory=self.project/'out/jobs'/key;private_directory(directory)
            self.state={'id':key,'scenario':scenario,'status':'queued','logs':[],'results':[]}
            self.started=time.monotonic();self.ended=None
            threading.Thread(target=self._run,args=(scenario,directory),daemon=True).start()
            return self.get()

    def _run(self, scenario, directory):
        process=None
        try:
            env=dict(os.environ,SHADECHECK_OUTPUT_ROOT=str(directory),PYTHONUNBUFFERED='1')
            command=[sys.executable,str(self.project/'scripts'/self.SCENARIOS[scenario])]
            kwargs={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
            with self.lock:
                self.process=subprocess.Popen(command,cwd=self.project,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,**kwargs)
                process=self.process;self.state['status']='running'
            def timeout():
                if process.poll() is None:
                    self._terminate(process)
            timer=threading.Timer(1200,timeout);timer.daemon=True;timer.start()
            completed_suite=None
            try:
                with private_open(directory/'execution.log',exclusive=True) as log:
                    for line in process.stdout:
                        log.write(line);log.flush()
                        with self.lock:self.state['logs']=(self.state['logs']+[line.rstrip()])[-120:]
                        if line.startswith('SHADECHECK MVP ACCEPTANCE VERIFIED:') and 'Reports: ' in line:
                            completed_suite=Path(line.split('Reports: ',1)[1].strip()).resolve()
                code=process.wait()
            finally:timer.cancel()
            with self.lock:self.state['exit_code']=code;self.state['status']='validating' if code==0 else 'failed'
            if code!=0:return
            if scenario=='acceptance':
                if completed_suite is None or not completed_suite.is_relative_to(self.project/'out/acceptance'):
                    raise ValueError('Completed suite path was not supplied by the actual acceptance process')
                verify(completed_suite);artifact_root=completed_suite
            else:artifact_root=directory
            results=[];added={}
            for report_path in sorted(artifact_root.rglob('report.json')):
                events=report_path.with_name('events.jsonl')
                if not events.is_file():continue
                report=json.loads(report_path.read_text())
                if recompute(load_events(events),report)!=report:raise ValueError('Job report does not match actual events')
                key=hashlib.sha256(str(report_path).encode()).hexdigest()
                added[key]=(report_path.name,report_path.read_bytes())
                results.append({'path':report_path.relative_to(artifact_root).as_posix(),'status':report['status'],'id':key})
            if not results:raise ValueError('Successful process did not produce verified report evidence')
            with self.lock:
                self.files.update(added);self.state['results']=results;self.state['status']='completed'
                self.state['message']='Execution and evidence validation completed. Download the new reports below. Restart the dashboard to load a new full acceptance run into the main report index; privacy statuses remain separate.'
        except Exception as error:
            with self.lock:self.state['status']='failed';self.state['error']=str(error)
        finally:
            with self.lock:
                self.ended=time.monotonic()
                if self.process is process:self.process=None

    @staticmethod
    def _terminate(process):
        if process.poll() is not None:return
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
        else:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass

    def close(self):
        with self.lock:
            if self.process:self._terminate(self.process)
