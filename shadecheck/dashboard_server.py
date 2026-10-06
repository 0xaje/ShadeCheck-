"""Loopback-only, read-only dashboard of a validated acceptance artifact snapshot."""
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import zipfile

from .core import canonical
from .suite import verify

RULES = [
    {"id": "SC-001", "title": "Sync Pattern Disclosure", "test": "Block-range size and alignment against the declared policy.", "boundary": "No wallet-history inference; timing and repeated-history analysis are outside coverage."},
    {"id": "SC-002", "title": "Broadcast Linkability", "test": "Connection-to-payload association; HIGH adds accepted submission and exact mempool bytes.", "boundary": "A connection is not a person. Shielded payments can still reveal broadcast linkage."},
    {"id": "SC-003", "title": "Selective Transaction Fetch", "test": "A non-empty proper subset of IDs from a delivered multi-transaction compact block.", "boundary": "Delivery does not prove wallet processing or ownership."},
    {"id": "SC-004", "title": "Transparent Fallback", "test": "Instrumented transparent selection or accepted transparent components under a shielded requirement.", "boundary": "Tests an explicit recipient path, not automatic Unified Address fallback."},
    {"id": "SC-005", "title": "Privacy Regression", "test": "New failures, new behavior categories, and increased severity against a compatible baseline.", "boundary": "Increased severity may reflect stronger observation; code-change causality is not inferred."},
]


def latest_suite(base):
    directories = sorted(p for p in Path(base).glob('*') if p.is_dir())
    return directories[-1] if directories else None


def snapshot(root):
    if root is None:
        return {"suite": None, "reports": [], "rules": RULES, "artifacts": []}, {}
    root = Path(root).resolve()
    verify(root)
    suite = json.loads((root / 'suite.json').read_text())
    files, artifact_list = {}, []
    for entry in suite['artifacts'] + [{"path": 'suite.json'}, {"path": 'suite.html'}]:
        relative = entry['path'].replace('\\', '/')
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Artifact path escapes suite')
        data = path.read_bytes()
        if 'sha256' in entry and hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Artifact changed while loading dashboard')
        key = hashlib.sha256(relative.encode()).hexdigest()
        files[key] = (relative, data)
        artifact_list.append({"id": key, "path": relative, "bytes": len(data)})
    by_path = {path: (key, data) for key, (path, data) in files.items()}
    reports = []
    for entry in suite['reports']:
        path = entry['report'].replace('\\', '/')
        key, raw = by_path[path]
        result = json.loads(raw)
        html_key = by_path.get(str(Path(path).with_suffix('.html')).replace('\\', '/'), (None,))[0]
        events_key = by_path[entry['events'].replace('\\', '/')][0]
        reports.append({"id": key, "path": path, "result": result, "html_id": html_key, "events_id": events_key})
    payload = {"suite": {"name": root.name, "acceptance_status": suite['acceptance_status'],
                          "privacy_status": suite['privacy_status'], "rules_executed": suite['rules_executed'],
                          "steps": suite['steps'], "limitations": suite['limitations'],
                          "loaded_at": datetime.now(timezone.utc).isoformat()},
               "reports": reports, "rules": RULES, "artifacts": artifact_list}
    # Package the exact loaded snapshot, not files re-read after verification.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative, data in files.values():
            archive.writestr(relative, data)
    files['bundle'] = ('shadecheck-' + root.name + '.zip', buffer.getvalue())
    return payload, files


def display_safe(value):
    # JavaScript numbers cannot preserve nanosecond integers above 2**53-1.
    # Only the display API uses strings; all artifact downloads stay byte-exact.
    if type(value) is int and abs(value) > 2**53 - 1:
        return str(value)
    if isinstance(value, dict):
        return {k: display_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [display_safe(v) for v in value]
    return value


def create_server(root=None, port=9070):
    payload, files = snapshot(root)
    assets = Path(__file__).parent / 'dashboard'
    routes = {'/': (assets / 'index.html').read_bytes(), '/app.js': (assets / 'app.js').read_bytes(),
              '/style.css': (assets / 'style.css').read_bytes(), '/api/data': canonical(display_safe(payload)).encode()}
    types = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8',
             '/style.css': 'text/css; charset=utf-8', '/api/data': 'application/json; charset=utf-8'}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}:
                self.send_error(403)
                return
            if self.path in routes:
                body, kind = routes[self.path], types[self.path]
                filename = None
            elif self.path.startswith('/download/') and self.path[10:] in files:
                filename, body = files[self.path[10:]]
                filename = Path(filename).name
                kind = 'application/zip' if filename.endswith('.zip') else 'application/octet-stream'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if filename:
                safe = ''.join(c for c in filename if c.isalnum() or c in '.-_')
                self.send_header('Content-Disposition', f'attachment; filename="{safe}"')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def serve(root=None, port=9070):
    if not 1 <= port <= 65535:
        raise ValueError('Port must be between 1 and 65535')
    server = create_server(root, port)
    print(f'ShadeCheck dashboard: http://127.0.0.1:{server.server_port} (validated artifact snapshot; Ctrl-C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
