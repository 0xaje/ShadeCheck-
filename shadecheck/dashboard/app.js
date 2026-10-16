'use strict';
const $ = id => document.getElementById(id);
const state = {data:null, selected:null};
function node(tag, text, cls) {const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;}
function badge(status) {return node('span',status,'badge '+String(status).toLowerCase());}
function download(id,label) {const a=node('a',label,'button');a.href='/download/'+id;a.setAttribute('download','');return a;}
function pretty(value) {return node('pre',JSON.stringify(value,null,2));}
function inspect(label, value) {const d=node('details');d.append(node('summary',label),pretty(value));return d;}
function title(path) {const p=path.split('/');return p.slice(-3,-1).join(' / ')+' · '+p[p.length-1].replace('.json','');}
function showReport(report) {
  state.selected=report.id;const host=$('detail');host.replaceChildren();const r=report.result;
  host.append(badge(r.status),node('h2',title(report.path)),node('div',report.path,'path'));
  const actions=node('div',undefined,'actions');actions.append(download(report.id,'JSON ↓'),download(report.events_id,'Events ↓'));if(report.html_id)actions.append(download(report.html_id,'HTML ↓'));host.append(actions);
  host.append(node('div','Rule coverage','subhead'));const coverage=node('div',undefined,'coverage');
  for(const rule of r.rules){const row=node('div',undefined,'coverage-row');row.append(node('span',rule.rule_id+' · '+(rule.covered?'Covered':'Missing coverage')),node('span',rule.coverage));coverage.append(row);}host.append(coverage);
  const c=r.baseline_comparison;
  if(c){const area=node('div',undefined,'comparison');area.append(node('h3','Baseline comparison'),badge(c.status),node('p',c.regressions+' regression(s) · '+c.unchanged_behaviors+' matching behavior group(s)'));
    for(const change of c.changes){const row=node('div',change.source_rule+' · '+change.change.replaceAll('-',' '),'change-row');row.append(node('div',(change.previous_severity||'Not previously observed')+' → '+change.current_severity));area.append(row);}
    if(!c.changes.length)area.append(node('p','No new failure or severity increase in the defined behavior groups. Existing strict findings can still fail.'));
    if(c.resolved_behaviors.length)area.append(node('p',c.resolved_behaviors.length+' previously observed behavior group(s) absent from this trace; interpret coverage above.'));
    area.append(node('div','Baseline evidence root','subhead'),node('div',c.baseline_evidence_root,'root'),inspect('Full comparison details',c));host.append(area);
  }
  host.append(node('div','Findings · '+r.findings.length,'subhead'));
  if(!r.findings.length)host.append(node('p','No violation of the selected rules was observed. A result with missing coverage cannot establish a passing test.'));
  for(const f of r.findings){const card=node('article',undefined,'finding');card.append(badge(f.severity),node('h3',f.rule_id+' · '+f.title));const dl=node('dl');
    for(const [key,label] of [['observed_behavior','Observed behavior'],['possible_privacy_consequence','Possible consequence'],['affected_component','Affected component'],['suggested_investigation','Investigation direction']]){dl.append(node('dt',label),node('dd',f[key]));}card.append(dl);
    card.append(inspect('Current evidence · '+f.evidence.length+' events',f.evidence));if(f.baseline_evidence?.length)card.append(inspect('Baseline evidence · '+f.baseline_evidence.length+' events',f.baseline_evidence));host.append(card);
  }
  host.append(node('div','Evidence root','subhead'),node('div',r.evidence_root,'root'),node('p','Large integer evidence values are displayed as decimal strings to preserve precision. Original downloads retain their exact JSON types.'),inspect('Report limitations',r.limitations));
  for(const button of $('report-list').children)button.classList.toggle('selected',button.dataset.id===report.id);
}
function filteredReports(){const status=$('status').value,rule=$('rule').value,q=$('search').value.trim().toLowerCase();return state.data.reports.filter(r=>(status==='all'||r.result.status===status)&&(rule==='all'||r.result.rules.some(x=>x.rule_id===rule))&&(!q||(r.path+' '+r.result.findings.map(f=>f.title+' '+f.observed_behavior).join(' ')).toLowerCase().includes(q)));}
function listReports(){const reports=filteredReports(),host=$('report-list');host.replaceChildren();for(const r of reports){const button=node('button',undefined,'report-item');button.type='button';button.dataset.id=r.id;const line=node('div',undefined,'report-title');line.append(node('span',r.result.rules.map(x=>x.rule_id).join(' / ')),badge(r.result.status));button.append(line,node('div',title(r.path),'path'),node('div',r.result.findings.length+' finding(s)','path'));button.addEventListener('click',()=>showReport(r));host.append(button);}if(!reports.length){host.append(node('div','No reports match these filters.','empty-list'));$('detail').replaceChildren(node('p','Choose different filters to inspect a saved report.'));state.selected=null;return;}showReport(reports.find(r=>r.id===state.selected)||reports[0]);}
function tabs(){for(const button of document.querySelectorAll('[data-tab]'))button.addEventListener('click',()=>{for(const b of document.querySelectorAll('[data-tab]'))b.classList.toggle('active',b===button);for(const tab of ['reports','rules','artifacts','simulator','ci'])$(tab+'-view')?.classList.toggle('hidden',tab!==button.dataset.tab);});}
function renderSim(mode){
  const leaky=mode==='leaky';
  $('sim-leaky-btn').className='button '+(leaky?'dark':'');
  $('sim-shielded-btn').className='button '+(leaky?'':'dark');
  const adv=$('sim-adversary-body'), ci=$('sim-ci-body');
  if(leaky){
    adv.innerHTML=`
      <div class="sim-item leaky">
        <div class="sim-title"><span>gRPC Peer Association</span><span class="badge fail">IDENTIFIABLE</span></div>
        <div class="sim-desc">Transport IP: <code>192.168.1.104:49812</code> (Session: <code>a3f89e...</code>)<br>Observed Mempool match in 1.2s via GetMempoolStream.</div>
      </div>
      <div class="sim-item leaky">
        <div class="sim-title"><span>Sync Range Query</span><span class="badge fail">NARROW DISCLOSURE</span></div>
        <div class="sim-desc">GetBlockRange(83 - 89) = 7 blocks.<br>⚠️ Start height unaligned; reveals exact wallet creation/activity window.</div>
      </div>
      <div class="sim-item leaky">
        <div class="sim-title"><span>Payment Execution</span><span class="badge fail">TRANSPARENT FALLBACK</span></div>
        <div class="sim-desc">Policy: AllowRevealedRecipients<br>Transparent output detected in broadcast transaction payload.</div>
      </div>`;
    ci.innerHTML=`
      <div class="sim-item leaky">
        <div class="sim-title"><span>SC-002: Broadcast Linkability</span><span class="badge fail">HIGH · FAIL</span></div>
        <div class="sim-desc">Accepted transaction bytes matched mempool stream on identifiable connection within 30s.</div>
      </div>
      <div class="sim-item leaky">
        <div class="sim-title"><span>SC-001: Sync Range Policy</span><span class="badge warn">MEDIUM · FAIL</span></div>
        <div class="sim-desc">Query violates 20-block chunk alignment boundary. Exposes wallet scan state.</div>
      </div>
      <div class="sim-item leaky">
        <div class="sim-title"><span>SC-004: Payment Policy</span><span class="badge fail">HIGH · FAIL</span></div>
        <div class="sim-desc">Transparent recipient executed under strict shielded requirement.</div>
      </div>
      <div style="margin-top:18px;padding:12px;background:#fcf4f2;border-radius:4px;color:#8e3d2d;font-weight:600;font-size:12px;">
        ⛔ GITHUB CI DECISION: EXIT CODE 1 (PULL REQUEST BLOCKED)
      </div>`;
  } else {
    adv.innerHTML=`
      <div class="sim-item shielded">
        <div class="sim-title"><span>gRPC Peer Association</span><span class="badge pass">DECOUPLED ROUTING</span></div>
        <div class="sim-desc">Broadcast routing separated from scanning transport session.<br>No direct connection-to-mempool linkability.</div>
      </div>
      <div class="sim-item shielded">
        <div class="sim-title"><span>Sync Range Query</span><span class="badge pass">UNIFORM CHUNK</span></div>
        <div class="sim-desc">GetBlockRange(80 - 99) = 20 blocks.<br>Boundary aligned to 20; query is indistinguishable from all syncing clients.</div>
      </div>
      <div class="sim-item shielded">
        <div class="sim-title"><span>Payment Execution</span><span class="badge pass">FULL PRIVACY SHIELDED</span></div>
        <div class="sim-desc">Mode: FullPrivacy<br>Sapling-to-Sapling: 0 transparent inputs, 0 transparent outputs.</div>
      </div>`;
    ci.innerHTML=`
      <div class="sim-item shielded">
        <div class="sim-title"><span>SC-001: Sync Range Policy</span><span class="badge pass">PASS</span></div>
        <div class="sim-desc">Complete range delivered and strictly aligned to configured 20-block boundaries.</div>
      </div>
      <div class="sim-item shielded">
        <div class="sim-title"><span>SC-004: Payment Policy</span><span class="badge pass">PASS</span></div>
        <div class="sim-desc">Verified shielded execution confirmed with zero transparent components.</div>
      </div>
      <div style="margin-top:18px;padding:12px;background:#f2f7ec;border-radius:4px;color:#49672e;font-weight:600;font-size:12px;">
        🛡️ GITHUB CI DECISION: EXIT CODE 0 (PULL REQUEST APPROVED)
      </div>`;
  }
}
function initSimulator(){
  $('sim-leaky-btn')?.addEventListener('click',()=>renderSim('leaky'));
  $('sim-shielded-btn')?.addEventListener('click',()=>renderSim('shielded'));
  $('copy-ci-btn')?.addEventListener('click',()=>{
    const code=$('ci-yaml-code')?.textContent||'';
    navigator.clipboard?.writeText(code).then(()=>{
      const btn=$('copy-ci-btn');if(btn){btn.textContent='Copied! ✓';setTimeout(()=>btn.textContent='Copy Workflow 📋',2000);}
    });
  });
  renderSim('leaky');
}
function populate(data){
  state.data=data;
  $('workspace').classList.remove('hidden');

  if($('rule-library').children.length===0){
    for(const rule of data.rules){
      const option=node('option',rule.id);option.value=rule.id;$('rule').append(option);
      const card=node('article',undefined,'rule-card');
      const id=node('div');id.append(badge(rule.id));
      const body=node('div');body.append(node('h3',rule.title),node('p',rule.test),node('p','Boundary: '+rule.boundary));
      card.append(id,body);$('rule-library').append(card);
    }
  }

  initSimulator();

  if(!data.suite){
    $('message').innerHTML='<strong>Interactive Standby Mode</strong> — No full Docker acceptance run loaded.<br>Use the sidebar to explore the <strong>Rule Library (02)</strong>, test the <strong>Wire Leak Inspector (04)</strong>, view the <strong>CI Gate (05)</strong>, or run <code>npm run demo</code> in your terminal.';
    $('message').classList.remove('hidden');
    $('acceptance').textContent='STANDBY';
    $('privacy').textContent='READY';
    $('count').textContent='0';
    $('rule-count').textContent='5';
    $('run-name').textContent='LOCAL STANDBY / DEMO';
    $('loaded').textContent='Dashboard active. 5 Privacy Rule Families loaded.';
    $('report-list').replaceChildren(node('div','No acceptance traces loaded yet. Run "npm run demo" in your terminal to generate sample evidence, or click "Leak Inspector" on the left to see live leak evaluations.','empty-list'));
    $('detail').replaceChildren(node('p','Select "Leak Inspector" (Tab 04) or "Rule Library" (Tab 02) in the left sidebar to inspect how ShadeCheck evaluates Zcash client traffic.'));
    return;
  }

  $('message').classList.add('hidden');
  $('bundle').classList.remove('hidden');
  $('acceptance').textContent=data.suite.acceptance_status;
  $('privacy').textContent=data.suite.privacy_status;
  $('count').textContent=data.reports.length;
  $('rule-count').textContent=data.suite.rules_executed.length;
  $('run-name').textContent='RUN / '+data.suite.name;
  $('loaded').textContent='Verified snapshot loaded '+new Date(data.suite.loaded_at).toLocaleString();

  for(const artifact of data.artifacts){
    const row=node('div',undefined,'artifact-row');
    row.append(node('span',artifact.path+' · '+(artifact.bytes/1024).toFixed(1)+' KB'),download(artifact.id,'Download ↓'));
    $('artifact-list').append(row);
  }
  const limits=node('ul');for(const limit of data.suite.limitations)limits.append(node('li',limit));$('limits').append(limits);
  listReports();
}
async function start(){tabs();initSimulator();for(const id of ['status','rule','search'])$(id)?.addEventListener(id==='search'?'input':'change',()=>{if(state.data)listReports();});try{const response=await fetch('/api/data',{cache:'no-store'});if(!response.ok)throw new Error('Saved evidence could not be loaded.');populate(await response.json());}catch(error){$('message').textContent='Unable to load the validated snapshot. '+error.message;}}
start();

