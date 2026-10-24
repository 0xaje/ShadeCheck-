"""Real current-release wallet receive/send on Zebra + Zaino local regtest.

No patched upstream source, public funds, user keys, or fabricated runtime data.
The upstream nakednet-test-mode feature deliberately selects local test transport.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

import grpc
from shadecheck.core import Recorder, evaluate, load_events
from shadecheck.generated import service_pb2 as pb, service_pb2_grpc as rpc
from shadecheck.harness import start_server
from shadecheck.privacy import private_write
from shadecheck.reporting import render_html

ROOT=Path(__file__).resolve().parents[1]
COMPOSE=['docker','compose','-f',str(ROOT/'integration/modern/compose.yml')]
INDEXER='127.0.0.1:29067'


def write(path,value):
    private_write(path,json.dumps(value,indent=2,sort_keys=True)+'\n')


def run(args, *, cwd=ROOT, env=None, timeout=300):
    value=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    if value.returncode:
        raise RuntimeError(f'{Path(args[0]).name} failed (exit {value.returncode})')
    return value.stdout


def documents(text):
    decoder=json.JSONDecoder()
    for index,char in enumerate(text):
        if char not in '{[': continue
        try: yield decoder.raw_decode(text[index:])[0]
        except ValueError: continue


def object_with(text,key):
    values=[x for x in documents(text) if isinstance(x,dict) and key in x]
    if not values: raise RuntimeError(f'Client did not produce expected {key} document')
    return values[-1]


def node(method,*params):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':list(params)}).encode()
    req=urllib.request.Request('http://127.0.0.1:29032',data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response: value=json.load(response)
    if value.get('error'): raise RuntimeError(f'Zebra RPC {method} failed: {value["error"].get("code")}')
    return value['result']


def wait_node():
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            info=node('getblockchaininfo')
            if info.get('chain')!='regtest': raise ValueError('Refusing non-regtest chain')
            return info
        except (OSError,RuntimeError): time.sleep(2)
    raise RuntimeError('Zebra startup timed out')


def wait_indexer(height):
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        try:
            with grpc.insecure_channel(INDEXER) as channel:
                info=rpc.CompactTxStreamerStub(channel).GetLightdInfo(pb.Empty(),timeout=5)
            if info.chainName.lower()!='regtest': raise ValueError('Refusing non-regtest indexer')
            if info.blockHeight>=height: return info
        except grpc.RpcError: pass
        time.sleep(2)
    raise RuntimeError('Zaino synchronization timed out')


def wallet(binary,directory,*command,endpoint=None):
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    args=[str(binary),'--chain','regtest','--data-dir',str(directory),'--birthday','1']
    args+=['--server',f'http://{endpoint}','--waitsync'] if endpoint else ['--offline']
    result=subprocess.run(args+list(command),cwd=directory,capture_output=True,text=True,timeout=360)
    if result.returncode:
        private_write(directory/'private-failure.log',result.stdout+'\n'+result.stderr)
        raise RuntimeError(f'Zingo command {command[0]} failed; private diagnostics retained locally')
    return result.stdout


def sync(binary,directory,endpoint):
    result=object_with(wallet(binary,directory,'sync','status',endpoint=endpoint),'percentage_total_blocks_scanned')
    if result['percentage_total_blocks_scanned']!=100 or result.get('total_blocks_scanned',0)<=0:
        raise RuntimeError('Client did not complete nonempty block scan')
    return result


def observe_mempool(stub,data):
    stream=stub.GetMempoolStream(pb.Empty(),timeout=20)
    try:
        for item in stream:
            if item.data==data: return
    finally: stream.cancel()
    raise RuntimeError('Identical transaction not observed in real mempool stream')


def confirm_transmission(text,stub):
    # The CLI reports its actual txid(s). Never derive Zcash txids with SHA-256.
    txids=object_with(text,'txids')['txids']
    if not txids or not all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in txids):
        raise RuntimeError('Client returned no valid transaction IDs')
    receipts=[]
    for txid in txids:
        if txid not in node('getrawmempool'): raise RuntimeError('Zebra did not accept wallet transmission')
        raw=node('getrawtransaction',txid)
        data=bytes.fromhex(raw)
        observe_mempool(stub,data)
        receipts.append({'txid':txid,'payload_sha256':hashlib.sha256(data).hexdigest(),
                         'node_mempool_confirmed':True,'payload_size':len(data)})
    node('generate',1)
    height=node('getblockchaininfo')['blocks']
    block=node('getblock',node('getblockhash',height),1)
    if not set(txids).issubset(set(block['tx'])): raise RuntimeError('Transmitted wallet transaction not mined')
    for receipt in receipts: receipt['confirmed_height']=height
    wait_indexer(height)
    return receipts


def verify(directory):
    directory=directory.resolve()
    manifest=json.loads((directory/'integration.json').read_text())
    if manifest.get('integration_status')!='VERIFIED' or manifest.get('network')!='regtest':
        raise ValueError('No verified modern integration manifest')
    pin=json.loads((ROOT/'integration/modern/client.json').read_text())
    if manifest['client']['revision']!=pin['revision']: raise ValueError('Client pin mismatch')
    entries=manifest['artifacts']
    paths={x['path'] for x in entries}
    actual={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name!='integration.json'}
    if paths!=actual or len(paths)!=len(entries): raise ValueError('Artifact inventory mismatch')
    for item in entries:
        path=(directory/item['path']).resolve()
        if not path.is_relative_to(directory) or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Artifact path or digest mismatch')
    events=load_events(directory/'events.jsonl')
    result=evaluate(events,rules=['SC-002'])
    if result!=json.loads((directory/'report.json').read_text()): raise ValueError('Report mismatch')
    high={f['payload_sha256'] for f in result['findings'] if f['severity']=='HIGH'}
    for phase in ['shielding','shielded_send']:
        receipts=manifest[phase]
        if not receipts or any(r['payload_sha256'] not in high or not r['node_mempool_confirmed'] for r in receipts):
            raise ValueError('Wallet transmission lacks HIGH evidence')
    if result['status']!='FAIL' or manifest['strict_exit']!=1: raise ValueError('Incorrect strict result')
    for mode in ['direct','observed']:
        status=json.loads((directory/f'{mode}-sync.json').read_text())
        if status['percentage_total_blocks_scanned']!=100 or status.get('total_blocks_scanned',0)<=0:
            raise ValueError('Incomplete scan')
    delivered={str(e['metadata']['height']):bytes.fromhex(e['metadata']['block_hash'])[::-1].hex()
               for e in events if e['method']=='GetBlockRange' and e['phase']=='response'}
    if not delivered or delivered!=manifest['canonical_blocks_verified']: raise ValueError('Canonical checks mismatch')
    print(f'MODERN WALLET ARTIFACTS VERIFIED: {directory}')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--verify',type=Path)
    args=parser.parse_args()
    if args.verify:
        verify(args.verify);return 0
    if args.source is None: parser.error('--source or --verify is required')
    pin=json.loads((ROOT/'integration/modern/client.json').read_text())
    source=args.source.resolve();binary=source/'target/release/zingo-cli'
    if run(['git','-C',str(source),'rev-parse','HEAD']).strip()!=pin['revision'] or run(['git','-C',str(source),'diff','HEAD','--']).strip():
        raise ValueError('Requires unmodified pinned upstream release')
    run_id=time.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    directory=ROOT/'out/modern'/run_id
    private=ROOT/'.shadecheck/modern-wallets'/run_id
    observed=private/'observed'
    miner=object_with(wallet(binary,observed,'new_taddress'),'encoded_address')['encoded_address']
    if not re.fullmatch(r't[0-9A-Za-z]{30,60}',miner): raise ValueError('Invalid local mining receiver')
    env={**os.environ,'SHADECHECK_MODERN_MINER':miner}
    directory.mkdir(parents=True,mode=0o700)
    try:
        print('Starting current Zebra/Zaino local backend...',flush=True)
        run(COMPOSE+['up','-d','zebra'],env=env,timeout=600)
        initial=wait_node()
        node('generate',110)
        height=initial['blocks']+110
        run(COMPOSE+['up','-d','zaino'],env=env,timeout=600)
        info=wait_indexer(height)
        print('Checking direct and observed current-release client synchronization...',flush=True)
        direct=sync(binary,private/'direct',INDEXER)
        write(directory/'direct-sync.json',direct)
        with ExitStack() as stack:
            recorder=Recorder(directory/'events.jsonl','upstream');stack.callback(recorder.close)
            channel=stack.enter_context(grpc.insecure_channel(INDEXER))
            observer,port=start_server(recorder,upstream=rpc.CompactTxStreamerStub(channel))
            stack.callback(lambda:observer.stop(0).wait())
            endpoint=f'127.0.0.1:{port}'
            client_channel=stack.enter_context(grpc.insecure_channel(endpoint))
            stub=rpc.CompactTxStreamerStub(client_channel)
            observed_status=sync(binary,observed,endpoint)
            write(directory/'observed-sync.json',observed_status)
            if any(direct.get(k)!=observed_status.get(k) for k in ['sync_start_height','total_blocks_scanned']):
                raise RuntimeError('Direct/observed block spans differ')
            print('Shielding real mined funds through the observed independent wallet...',flush=True)
            shield=confirm_transmission(wallet(binary,observed,'quickshield',endpoint=endpoint),stub)
            sync(binary,observed,endpoint)
            receiver=object_with(wallet(binary,private/'recipient','new_address','o'),'encoded_address')['encoded_address']
            print('Sending real shielded wallet funds through ShadeCheck...',flush=True)
            sent=confirm_transmission(wallet(binary,observed,'quicksend',receiver,'100000',endpoint=endpoint),stub)
            recipient=sync(binary,private/'recipient',INDEXER)
            balance=next((v for v in documents(wallet(binary,private/'recipient','balance')) if isinstance(v,dict)),None)
            if balance is None: raise RuntimeError('Recipient balance missing')
            # Prove a positive received amount rather than merely completing a scan.
            def positive(value):
                return any(positive(x) for x in value.values()) if isinstance(value,dict) else (any(positive(x) for x in value) if isinstance(value,list) else type(value) is int and value>0)
            if not positive(balance): raise RuntimeError('Recipient has no received balance')
            write(directory/'recipient-receipt.json',{'sync_status':recipient,'balance':balance})
        events=load_events(directory/'events.jsonl')
        verified={}
        for e in events:
            if e['method']=='GetBlockRange' and e['phase']=='response':
                h=e['metadata']['height'];block=node('getblockhash',h)
                if bytes.fromhex(e['metadata']['block_hash'])[::-1].hex()!=block: raise RuntimeError('Noncanonical block delivered')
                verified[str(h)]=block
        result=evaluate(events,rules=['SC-002'])
        write(directory/'report.json',result);private_write(directory/'report.html',render_html(result))
        gate=subprocess.run([sys.executable,'-m','shadecheck.cli','test','--events',str(directory/'events.jsonl'),'--rules','SC-002','--policy','strict','--output',str(directory/'strict-report.json')],cwd=ROOT)
        if gate.returncode!=1: raise RuntimeError('Independent wallet broadcast did not enforce strict exit 1')
        images=json.loads(run(COMPOSE+['images','--format','json'],env=env))
        write(directory/'integration.json',{
            'integration_status':'VERIFIED','network':'regtest','client':{**pin,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()},
            'node':node('getnetworkinfo'),'indexer_revision':info.gitCommit,'images':images,
            'shielding':shield,'shielded_send':sent,'canonical_blocks_verified':verified,'strict_exit':gate.returncode,
            'evidence_root':result['evidence_root'],
            'artifacts':[{'path':str(p.relative_to(directory)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(directory.rglob('*')) if p.is_file()],
            'limitations':['Explicit upstream nakednet-test-mode; no claim about default mixnet privacy.',
                'SC-002 only in this funded independent-client integration; other families have separate scenarios.',
                'Local regtest funds; no public testnet or mainnet compatibility claim.',
                'Offline verification recomputes recorded evidence; it is not a fresh wallet or consensus execution.']})
        verify(directory)
        print(f'CURRENT INDEPENDENT WALLET RECEIVE/SEND VERIFIED: strict SC-002 HIGH; {directory}',flush=True)
        return 0
    except Exception:
        write(directory/'integration-error.json',{'integration_status':'FAILED','message':'Modern integration failed; inspect CI step or private local diagnostics. No VERIFIED result was produced.'})
        raise


if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,RuntimeError,ValueError,grpc.RpcError,subprocess.SubprocessError) as error:
        print(f'Modern wallet integration error: {error}',file=sys.stderr);raise SystemExit(2)
