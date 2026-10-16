"""Self-contained human-readable evidence reports."""
import html
import json


def render_html(result):
    esc = lambda value: html.escape(str(value))
    pretty = lambda value: esc(json.dumps(value, indent=2, sort_keys=True))
    rows = ''.join('<tr><td>'+esc(r['rule_id'])+'</td><td>'+esc(r['coverage'])+'</td><td>'+esc(r.get('covered',False))+'</td></tr>' for r in result['rules'])
    findings = ''
    for f in result['findings']:
        findings += '<article><h3>'+esc(f['rule_id'])+' · '+esc(f['severity'])+' · '+esc(f['title'])+'</h3>'
        for key,label in [('observed_behavior','Observed behavior'),('possible_privacy_consequence','Possible consequence'),
                          ('affected_component','Affected component'),('suggested_investigation','Investigation')]:
            findings += '<p><strong>'+label+':</strong> '+esc(f[key])+'</p>'
        findings += '<details><summary>Inspect current evidence ('+str(len(f['evidence']))+' events)</summary><pre>'+pretty(f['evidence'])+'</pre></details>'
        if f.get('baseline_evidence'):
            findings += '<details><summary>Inspect baseline evidence</summary><pre>'+pretty(f['baseline_evidence'])+'</pre></details>'
        findings += '</article>'
    comparison = result.get('baseline_comparison')
    baseline = '' if comparison is None else '<h2>Baseline comparison</h2><p>'+esc(comparison['status'])+' · '+str(comparison['regressions'])+' regressions</p><pre>'+pretty(comparison)+'</pre>'
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ShadeCheck evidence report</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#17202a;background:#fafafa}h1,h2,h3{line-height:1.3}article{background:white;border:1px solid #ddd;border-radius:8px;padding:20px;margin:20px 0}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:10px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#eee;padding:16px}summary{cursor:pointer}small{overflow-wrap:anywhere}</style></head><body>""" + (
        '<h1>ShadeCheck: '+esc(result['status'])+'</h1><p>Defined observable behavior tests; passing does not establish anonymity.</p>'
        '<p>Policy: '+esc(result['policy'])+' · '+str(len(result['findings']))+' findings</p><small>Evidence root: '+esc(result['evidence_root'])+'</small>'
        '<h2>Tested rules</h2><table><thead><tr><th>Rule</th><th>Coverage</th><th>Covered</th></tr></thead><tbody>'+rows+'</tbody></table>'
        '<h2>Findings</h2>'+(findings or '<p>No violation of the selected rules was observed. Check coverage above.</p>')+baseline+
        '<h2>Limitations</h2><ul>'+''.join('<li>'+esc(v)+'</li>' for v in result['limitations'])+'</ul>'
        '<details><summary>Complete JSON result</summary><pre>'+pretty(result)+'</pre></details></body></html>')


def render_markdown(result):
    status = result.get('status', 'UNKNOWN')
    status_icon = "🟢" if status == "PASS" else ("🟡" if status == "WARN" else "🔴")
    lines = [
        f"## {status_icon} ShadeCheck Privacy CI: **{status}**",
        "",
        "> *Defined observable behavior tests for Zcash applications; passing does not establish anonymity.*",
        "",
        f"**Policy:** `{result.get('policy', 'strict')}` | **Findings:** `{len(result.get('findings', []))}` | **Evidence Root:** `{result.get('evidence_root', 'N/A')[:16]}...`",
        "",
        "### Tested Rules & Coverage",
        "",
        "| Rule | Status | Documented Boundary |",
        "| :--- | :---: | :--- |",
    ]
    for r in result.get('rules', []):
        covered_badge = "✅ Covered" if r.get('covered') else "⚠️ Missing"
        lines.append(f"| **{r.get('rule_id')}** | {covered_badge} | {r.get('coverage', '')} |")

    findings = result.get('findings', [])
    if findings:
        lines.extend([
            "",
            "### ⚠️ Privacy Findings",
            "",
            "| Rule | Severity | Title | Affected Component |",
            "| :--- | :---: | :--- | :--- |",
        ])
        for f in findings:
            sev_badge = "🔴 HIGH" if f.get('severity') == "HIGH" else "🟡 MEDIUM"
            lines.append(f"| **{f.get('rule_id')}** | {sev_badge} | {f.get('title')} | `{f.get('affected_component', 'N/A')}` |")

        lines.append("")
        for f in findings:
            lines.extend([
                f"<details><summary>🔍 <b>{f.get('rule_id')} Details:</b> {f.get('title')}</summary>",
                "",
                f"- **Observed Behavior:** {f.get('observed_behavior')}",
                f"- **Possible Consequence:** {f.get('possible_privacy_consequence')}",
                f"- **Investigation:** {f.get('suggested_investigation')}",
                f"- **Evidence Events:** {len(f.get('evidence', []))} recorded",
                "</details>",
                "",
            ])
    else:
        lines.extend([
            "",
            "### ✅ Privacy Evaluation",
            "No violations of the selected rules were observed for the covered scenarios.",
            "",
        ])

    comparison = result.get('baseline_comparison')
    if comparison:
        comp_status = comparison.get('status', 'UNKNOWN')
        lines.extend([
            "### 📊 Baseline Comparison (SC-005)",
            f"- **Comparison Status:** `{comp_status}`",
            f"- **Regressions:** `{comparison.get('regressions', 0)}`",
            f"- **Matching Behavior Groups:** `{comparison.get('unchanged_behaviors', 0)}`",
            "",
        ])

    lines.extend([
        "---",
        "<sub>🛡️ Generated by <a href='https://github.com/0xaje/ShadeCheck-'>ShadeCheck</a> — Privacy CI for Zcash applications</sub>",
    ])
    return "\n".join(lines)

