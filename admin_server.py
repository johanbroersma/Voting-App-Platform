#!/usr/bin/env python3
"""
Voting App Platform — Admin Management Server

Manages multi-tenant voting app deployments on Render.com.

Environment variables (required in production):
  ADMIN_PASSWORD_HASH   SHA-256 hex of the admin password
  RENDER_API_KEY        Render.com API key
  RENDER_OWNER_ID       Render workspace owner ID
  RESEND_API_KEY        Resend.com API key for welcome emails
  GITHUB_REPO           GitHub repo URL (e.g. https://github.com/user/repo)

Optional:
  EMAIL_FROM            Sender address (default: onboarding@resend.dev)
  PORT                  Server port (injected by Render)
  TENANTS_FILE          Path to tenants JSON (default: ./tenants.json)

Local usage:
    ADMIN_PASSWORD_HASH=<hash> python3 admin_server.py
"""

import json
import os
import sys
import threading
import urllib.request
import urllib.error
import hashlib
import secrets
import string
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT             = int(os.environ.get('PORT', 8090))
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
TENANTS_FILE     = os.environ.get('TENANTS_FILE', os.path.join(BASE_DIR, 'tenants.json'))
SERVE_DIR        = os.path.join(BASE_DIR, 'admin')
ADMIN_PW_HASH    = os.environ.get('ADMIN_PASSWORD_HASH', '')
RENDER_API_KEY   = os.environ.get('RENDER_API_KEY', '')
RENDER_OWNER_ID  = os.environ.get('RENDER_OWNER_ID', 'tea-d79e9vk50q8c73fhoeng')
RESEND_API_KEY   = os.environ.get('RESEND_API_KEY', '')
GITHUB_REPO      = os.environ.get('GITHUB_REPO', 'https://github.com/johanbroersma/Voting-App-Platform')
EMAIL_FROM       = os.environ.get('EMAIL_FROM', 'onboarding@resend.dev')

RENDER_API_BASE  = 'https://api.render.com/v1'
RESEND_API_BASE  = 'https://api.resend.com'

lock         = threading.Lock()
sessions     = {}   # token → {expires: timestamp}
SESSION_TTL  = 8 * 3600  # 8 hours

MIME = {
    '.html':  'text/html; charset=utf-8',
    '.css':   'text/css; charset=utf-8',
    '.js':    'application/javascript; charset=utf-8',
    '.json':  'application/json; charset=utf-8',
    '.png':   'image/png',
    '.ico':   'image/x-icon',
    '.svg':   'image/svg+xml',
}

# ── Tenant DB helpers ─────────────────────────────────────────────────────────

def load_tenants():
    for path in [TENANTS_FILE, os.path.join(BASE_DIR, 'tenants.json')]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return []


def save_tenants(tenants):
    target = TENANTS_FILE
    target_dir = os.path.dirname(target) or '.'
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError:
        # /data not mounted — fall back to app directory so we don't crash.
        # Warn loudly because data won't survive a restart without the disk.
        target = os.path.join(BASE_DIR, 'tenants.json')
        print(f'WARNING: Cannot write to {TENANTS_FILE} — no disk mounted. '
              f'Falling back to {target}. Add a persistent disk to avoid data loss.')
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(tenants, f, indent=2)


# ── Session management ────────────────────────────────────────────────────────

def create_session():
    token = secrets.token_hex(32)
    sessions[token] = time_now() + SESSION_TTL
    return token


def validate_session(token):
    exp = sessions.get(token)
    if exp and time_now() < exp:
        return True
    sessions.pop(token, None)
    return False


def time_now():
    return datetime.now(timezone.utc).timestamp()


# ── Render API ────────────────────────────────────────────────────────────────

def render_request(method, path, body=None):
    url = f'{RENDER_API_BASE}{path}'
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(
        url, data=data,
        headers={
            'Authorization': f'Bearer {RENDER_API_KEY}',
            'Content-Type':  'application/json',
            'Accept':        'application/json',
        },
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        raw  = resp.read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            detail = json.loads(raw)
        except Exception:
            detail = {'message': raw.decode('utf-8', errors='replace')}
        raise RuntimeError(f'Render API {method} {path} → {e.code}: {detail}')


def render_create_service(name, app_type, plan, region):
    body = {
        'type':       'web_service',
        'name':       name,
        'ownerId':    RENDER_OWNER_ID,
        'repo':       GITHUB_REPO,
        'branch':     'main',
        'autoDeploy': 'yes',
        'serviceDetails': {
            'env':    'python',
            'plan':   plan,
            'region': region,
            'envSpecificDetails': {
                'buildCommand': 'pip install -r requirements.txt',
                'startCommand': 'python3 server.py',
            },
        },
        'envVars': [
            {'key': 'APP_TYPE',    'value': app_type},
            {'key': 'STATE_FILE',  'value': '/data/election_state.json'},
        ],
    }
    return render_request('POST', '/services', body)


def render_delete_service(service_id):
    render_request('DELETE', f'/services/{service_id}')


def render_trigger_deploy(service_id):
    return render_request('POST', f'/services/{service_id}/deploys',
                          {'clearCache': 'do_not_clear'})


def render_get_service(service_id):
    return render_request('GET', f'/services/{service_id}')


# ── Resend email ──────────────────────────────────────────────────────────────

def send_welcome_email(tenant):
    app_label = 'Church Voting App' if tenant['app_type'] == 'church' else 'Board Voting App'
    plan_note = (
        'Your instance runs on the free plan. Voting data is preserved while '
        'the service stays active but may be lost if the service restarts. '
        'For persistent data across restarts, upgrade to the Starter plan and '
        'add a persistent disk in the Render dashboard.'
        if tenant['plan'] == 'free'
        else 'Your instance runs on the Starter plan with a persistent disk. '
             'Add the disk in the Render dashboard under your service settings '
             'if you have not done so already.'
    )
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a1a;">
  <h2 style="color: #1e3a5f;">Your {app_label} is Ready</h2>
  <p>Hi {tenant['contact_name']},</p>
  <p>Your voting app instance has been provisioned. Here are your access details:</p>

  <table style="background:#f8f9fa; border-radius:8px; padding:16px; width:100%; border-collapse:collapse;">
    <tr><td style="padding:6px 12px; font-weight:bold; width:160px;">App URL</td>
        <td style="padding:6px 12px;"><a href="{tenant['url']}">{tenant['url']}</a></td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">Admin Password</td>
        <td style="padding:6px 12px; font-family:monospace;">election2024</td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">Results Password</td>
        <td style="padding:6px 12px; font-family:monospace;">results2024</td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">App Type</td>
        <td style="padding:6px 12px;">{app_label}</td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">Plan</td>
        <td style="padding:6px 12px; text-transform:capitalize;">{tenant['plan']}</td></tr>
  </table>

  <h3 style="color:#1e3a5f; margin-top:24px;">Getting Started</h3>
  <ol>
    <li>Open <a href="{tenant['url']}">{tenant['url']}</a> in your browser.</li>
    <li>Enter the Admin Password above to access the Setup screen.</li>
    <li><strong>Change both passwords immediately</strong> under App Settings.</li>
    <li>Complete the election setup: add nominees, set the meeting date, and generate voter tokens.</li>
    <li>Share the voter URL (<code>{tenant['url']}/vote.html</code>) with your voters.</li>
  </ol>

  <div style="background:#fff3cd; border-left:4px solid #ffc107; padding:12px 16px; margin:16px 0; border-radius:4px;">
    <strong>Note:</strong> {plan_note}
  </div>

  <p style="color:#666; font-size:14px;">
    This instance was provisioned by the Voting App Platform administrator.
    Contact your administrator if you need assistance.
  </p>
</body>
</html>
"""
    body = {
        'from':    EMAIL_FROM,
        'to':      [tenant['contact_email']],
        'subject': f'Your {app_label} is Ready — {tenant["name"]}',
        'html':    html,
    }
    req = urllib.request.Request(
        f'{RESEND_API_BASE}/emails',
        data=json.dumps(body).encode(),
        headers={
            'Authorization': f'Bearer {RESEND_API_KEY}',
            'Content-Type':  'application/json',
        },
        method='POST',
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        print(f'Resend error {e.code}: {raw.decode("utf-8", errors="replace")}')
        return None


# ── Slug / name helpers ───────────────────────────────────────────────────────

def make_service_name(org_name, app_type):
    slug = org_name.lower()
    slug = ''.join(c if c.isalnum() else '-' for c in slug)
    slug = '-'.join(part for part in slug.split('-') if part)[:30]
    suffix = 'c' if app_type == 'church' else 'b'
    return f'vap-{slug}-{suffix}'


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f'{self.command} {self.path} → {args[1] if len(args) > 1 else "?"}')

    def _send(self, code, ctype, body: bytes):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        self._send(code, 'application/json; charset=utf-8',
                   json.dumps(data).encode())

    def _err(self, code, msg):
        self._json(code, {'error': msg})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _auth(self):
        header = self.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return False
        token = header[7:]
        return validate_session(token)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def handle_error(self, exc):
        import traceback
        traceback.print_exc()
        try:
            self._err(500, f'Internal server error: {exc}')
        except Exception:
            pass  # Response may have already started

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        try:
            self._do_GET()
        except Exception as e:
            self.handle_error(e)

    def _do_GET(self):
        path = self.path.split('?')[0]

        if path == '/api/tenants':
            if not self._auth():
                return self._err(401, 'Unauthorized')
            with lock:
                tenants = load_tenants()
            return self._json(200, tenants)

        if path == '/api/config':
            return self._json(200, {
                'emailConfigured': bool(RESEND_API_KEY and EMAIL_FROM != 'onboarding@resend.dev'),
                'renderConfigured': bool(RENDER_API_KEY),
            })

        if path == '/':
            path = '/index.html'
        local = os.path.normpath(os.path.join(SERVE_DIR, path.lstrip('/')))
        if not local.startswith(SERVE_DIR):
            return self._err(403, 'Forbidden')
        if os.path.isfile(local):
            ext   = os.path.splitext(local)[1].lower()
            ctype = MIME.get(ext, 'application/octet-stream')
            with open(local, 'rb') as f:
                self._send(200, ctype, f.read())
        else:
            self._err(404, 'Not found')

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        try:
            self._do_POST()
        except Exception as e:
            self.handle_error(e)

    def _do_POST(self):
        path = self.path.split('?')[0]

        # ── /api/auth — password verification ────────────────────────────────
        if path == '/api/auth':
            payload = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            incoming = payload.get('passwordHash', '')
            if not ADMIN_PW_HASH:
                return self._err(503, 'Admin password not configured on server')
            if incoming != ADMIN_PW_HASH:
                return self._err(401, 'Wrong password')
            token = create_session()
            return self._json(200, {'token': token})

        if not self._auth():
            return self._err(401, 'Unauthorized')

        # ── /api/tenants — provision new tenant ───────────────────────────────
        if path == '/api/tenants':
            payload = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')

            required = ['name', 'app_type', 'contact_name', 'contact_email', 'plan', 'region']
            missing  = [f for f in required if not payload.get(f)]
            if missing:
                return self._err(400, f'Missing fields: {", ".join(missing)}')

            if payload['app_type'] not in ('church', 'board'):
                return self._err(400, 'app_type must be church or board')

            service_name = make_service_name(payload['name'], payload['app_type'])

            # Create Render service
            try:
                result = render_create_service(
                    name     = service_name,
                    app_type = payload['app_type'],
                    plan     = payload['plan'],
                    region   = payload['region'],
                )
            except RuntimeError as e:
                return self._err(502, str(e))

            svc = result.get('service', result)
            service_id = svc.get('id', '')
            url = (svc.get('serviceDetails', {}).get('url')
                   or f'https://{service_name}.onrender.com')

            tenant = {
                'id':               secrets.token_hex(8),
                'name':             payload['name'],
                'app_type':         payload['app_type'],
                'contact_name':     payload['contact_name'],
                'contact_email':    payload['contact_email'],
                'contact_phone':    payload.get('contact_phone', ''),
                'notes':            payload.get('notes', ''),
                'render_service_id':   service_id,
                'render_service_name': service_name,
                'url':              url,
                'plan':             payload['plan'],
                'region':           payload['region'],
                'provisioned_at':   datetime.now(timezone.utc).isoformat(),
                'last_deployed_at': datetime.now(timezone.utc).isoformat(),
            }

            with lock:
                tenants = load_tenants()
                tenants.append(tenant)
                save_tenants(tenants)

            # Send welcome email (non-blocking; failure doesn't abort provisioning)
            if RESEND_API_KEY and tenant['contact_email']:
                try:
                    send_welcome_email(tenant)
                except Exception as e:
                    print(f'Email send failed: {e}')

            return self._json(201, tenant)

        # ── /api/tenants/{id}/redeploy — trigger single redeploy ──────────────
        parts = path.split('/')
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'tenants' and parts[4] == 'redeploy':
            tenant_id = parts[3]
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
            if not tenant:
                return self._err(404, 'Tenant not found')
            try:
                render_trigger_deploy(tenant['render_service_id'])
            except RuntimeError as e:
                return self._err(502, str(e))
            with lock:
                tenants = load_tenants()
                for t in tenants:
                    if t['id'] == tenant_id:
                        t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                save_tenants(tenants)
            return self._json(200, {'ok': True})

        # ── /api/tenants/bulk-redeploy — redeploy selected tenants ────────────
        if path == '/api/tenants/bulk-redeploy':
            payload = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            ids = payload.get('ids', [])
            if not ids:
                return self._err(400, 'No tenant ids provided')

            errors  = []
            updated = []
            with lock:
                tenants = load_tenants()
                for t in tenants:
                    if t['id'] in ids:
                        try:
                            render_trigger_deploy(t['render_service_id'])
                            t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                            updated.append(t['id'])
                        except RuntimeError as e:
                            errors.append({'id': t['id'], 'error': str(e)})
                save_tenants(tenants)

            return self._json(200, {'updated': updated, 'errors': errors})

        self._err(404, 'Not found')

    # ── DELETE ────────────────────────────────────────────────────────────────
    def do_DELETE(self):
        try:
            self._do_DELETE()
        except Exception as e:
            self.handle_error(e)

    def _do_DELETE(self):
        path = self.path.split('?')[0]

        if not self._auth():
            return self._err(401, 'Unauthorized')

        # /api/tenants/{id}
        parts = path.split('/')
        if len(parts) == 4 and parts[1] == 'api' and parts[2] == 'tenants':
            tenant_id = parts[3]
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
                if not tenant:
                    return self._err(404, 'Tenant not found')

                # Delete Render service
                if tenant.get('render_service_id'):
                    try:
                        render_delete_service(tenant['render_service_id'])
                    except RuntimeError as e:
                        # Log but continue — remove from our DB regardless
                        print(f'Render delete error for {tenant_id}: {e}')

                tenants = [t for t in tenants if t['id'] != tenant_id]
                save_tenants(tenants)

            return self._json(200, {'ok': True})

        self._err(404, 'Not found')


def main():
    if not ADMIN_PW_HASH:
        print('WARNING: ADMIN_PASSWORD_HASH env var not set — all logins will fail.')
    if not RENDER_API_KEY:
        print('WARNING: RENDER_API_KEY not set — provisioning will fail.')

    server = HTTPServer(('0.0.0.0', PORT), Handler)

    public_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'

    print('=' * 55)
    print('  Voting App Platform — Admin Server')
    print('=' * 55)
    if public_url:
        print(f'  Admin UI:  {public_url}/')
    else:
        print(f'  Admin UI:  http://localhost:{PORT}/')
        print(f'  Network:   http://{local_ip}:{PORT}/')
    print(f'  Tenants:   {TENANTS_FILE}')
    print('  Press Ctrl+C to stop.')
    print('=' * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')


if __name__ == '__main__':
    main()
