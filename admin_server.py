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

All variables can be overridden at runtime via the Settings UI (/api/settings).
Settings are stored in settings.json alongside tenants.json and take precedence
over environment variables.

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

PORT          = int(os.environ.get('PORT', 8090))
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
TENANTS_FILE  = os.environ.get('TENANTS_FILE', os.path.join(BASE_DIR, 'tenants.json'))
SETTINGS_FILE = os.path.join(os.path.dirname(TENANTS_FILE) or BASE_DIR, 'settings.json')
SERVE_DIR     = os.path.join(BASE_DIR, 'admin')

RENDER_API_BASE     = 'https://api.render.com/v1'
RESEND_API_BASE     = 'https://api.resend.com'
CLOUDFLARE_API_BASE = 'https://api.cloudflare.com/client/v4'

# Plans that support persistent disks on Render.
PAID_PLANS = frozenset({'starter', 'standard', 'pro'})

lock        = threading.Lock()
sessions    = {}   # token → expiry timestamp
SESSION_TTL = 8 * 3600  # 8 hours

# ── Runtime-configurable settings ─────────────────────────────────────────────
# Values saved via the Settings UI (stored in settings.json) take precedence
# over environment variables. Use get_cfg(key) everywhere.

_ENV_DEFAULTS = {
    'ADMIN_PASSWORD_HASH':  os.environ.get('ADMIN_PASSWORD_HASH', ''),
    'RENDER_API_KEY':       os.environ.get('RENDER_API_KEY', ''),
    'RENDER_OWNER_ID':      os.environ.get('RENDER_OWNER_ID', 'tea-d79e9vk50q8c73fhoeng'),
    'RENDER_PROJECT_ID':     os.environ.get('RENDER_PROJECT_ID', ''),
    'RENDER_ENVIRONMENT_ID': os.environ.get('RENDER_ENVIRONMENT_ID', ''),
    'RESEND_API_KEY':       os.environ.get('RESEND_API_KEY', ''),
    'GITHUB_REPO':          os.environ.get('GITHUB_REPO', 'https://github.com/johanbroersma/Voting-App-Platform'),
    'EMAIL_FROM':           os.environ.get('EMAIL_FROM', 'onboarding@resend.dev'),
    'CUSTOM_DOMAIN':        os.environ.get('CUSTOM_DOMAIN', '').strip().lower().rstrip('/'),
    'CLOUDFLARE_API_TOKEN': os.environ.get('CLOUDFLARE_API_TOKEN', ''),
    'CLOUDFLARE_ZONE_ID':   os.environ.get('CLOUDFLARE_ZONE_ID', ''),
}

_SENSITIVE_KEYS  = {'ADMIN_PASSWORD_HASH', 'RENDER_API_KEY', 'RESEND_API_KEY', 'CLOUDFLARE_API_TOKEN'}
_settings_cache  = {}
_settings_loaded = False
_settings_lock   = threading.Lock()


def _load_settings_disk():
    for path in [SETTINGS_FILE, os.path.join(BASE_DIR, 'settings.json')]:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def get_cfg(key):
    """Return live value: settings.json overrides env var defaults."""
    global _settings_loaded
    with _settings_lock:
        if not _settings_loaded:
            _settings_cache.update(_load_settings_disk())
            _settings_loaded = True
        val = _settings_cache.get(key, '')
    return val if val else _ENV_DEFAULTS.get(key, '')


def save_settings(updates):
    """Persist setting updates to disk and refresh in-memory cache."""
    global _settings_loaded
    with _settings_lock:
        if not _settings_loaded:
            _settings_cache.update(_load_settings_disk())
            _settings_loaded = True
        for k, v in updates.items():
            if v:
                _settings_cache[k] = v
            else:
                _settings_cache.pop(k, None)
        target = SETTINGS_FILE
        try:
            os.makedirs(os.path.dirname(target) or '.', exist_ok=True)
        except OSError:
            target = os.path.join(BASE_DIR, 'settings.json')
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(_settings_cache, f, indent=2)


MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png':  'image/png',
    '.ico':  'image/x-icon',
    '.svg':  'image/svg+xml',
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
    url  = f'{RENDER_API_BASE}{path}'
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(
        url, data=data,
        headers={
            'Authorization': f'Bearer {get_cfg("RENDER_API_KEY")}',
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


_render_project_id_cache     = None
_render_environment_id_cache = None


def generate_landing_password(length=10):
    """Generate a random alphanumeric landing page password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def render_get_placement_ids():
    """Return (project_id, environment_id) for the 'Voting App' project / 'Tenants' environment.
    Uses RENDER_PROJECT_ID / RENDER_ENVIRONMENT_ID settings if configured,
    otherwise auto-discovers via the Render API."""
    global _render_project_id_cache, _render_environment_id_cache

    cfg_project = get_cfg('RENDER_PROJECT_ID')
    cfg_env     = get_cfg('RENDER_ENVIRONMENT_ID')

    # Both manually configured — use directly.
    if cfg_project and cfg_env:
        return cfg_project, cfg_env

    project_id = cfg_project or _render_project_id_cache
    env_id     = cfg_env     or _render_environment_id_cache

    if project_id and env_id:
        return project_id, env_id

    # Auto-discover project "Voting App".
    if not project_id:
        try:
            items = render_request('GET', '/projects')
            print(f'Render /projects response (truncated): {json.dumps(items)[:600]}')
            for item in (items if isinstance(items, list) else []):
                proj = item.get('project', item)
                if proj.get('name') == 'Voting App':
                    pid = proj.get('id', '')
                    if pid:
                        project_id = pid
                        _render_project_id_cache = pid
                        print(f'Found Render project "Voting App": {pid}')
                        break
            if not project_id:
                print('WARNING: Project "Voting App" not found — service will have no project assigned.')
                return None, None
        except Exception as e:
            print(f'render_get_placement_ids error fetching projects: {e}')
            return project_id, env_id

    # Auto-discover "Tenants" environment within the project.
    if not env_id:
        try:
            envs = render_request('GET', f'/projects/{project_id}/environments')
            print(f'Render environments response: {json.dumps(envs)[:400]}')
            for item in (envs if isinstance(envs, list) else []):
                env = item.get('environment', item)
                if env.get('name') == 'Tenants':
                    eid = env.get('id', '')
                    if eid:
                        env_id = eid
                        _render_environment_id_cache = eid
                        print(f'Found Render environment "Tenants": {eid}')
                        break
            if not env_id:
                print('WARNING: Environment "Tenants" not found — service placed in default environment.')
        except Exception as e:
            print(f'render_get_placement_ids error fetching environments: {e}')

    return project_id, env_id


def render_create_service(name, app_type, plan, region, landing_password_hash=''):
    project_id, environment_id = render_get_placement_ids()
    env_vars = [
        {'key': 'APP_TYPE', 'value': app_type},
    ]
    if landing_password_hash:
        env_vars.append({'key': 'LANDING_PASSWORD_HASH', 'value': landing_password_hash})

    body = {
        'type':       'web_service',
        'name':       name,
        'ownerId':    get_cfg('RENDER_OWNER_ID'),
        'repo':       get_cfg('GITHUB_REPO'),
        'branch':     'main',
        'autoDeploy': 'no',
        'serviceDetails': {
            'env':    'python',
            'plan':   plan,
            'region': region,
            'envSpecificDetails': {
                'buildCommand': 'pip install -r requirements.txt',
                'startCommand': 'python3 server.py',
            },
        },
        'envVars': env_vars,
    }
    if project_id:
        body['projectId'] = project_id
        print(f'Assigning new service to project: {project_id}')
    else:
        print('WARNING: Project not configured — set RENDER_PROJECT_ID in Settings.')
    if environment_id:
        body['environmentId'] = environment_id
        print(f'Assigning new service to environment: {environment_id}')
    result = render_request('POST', '/services', body)
    if plan in PAID_PLANS:
        svc = result.get('service', result)
        sid = svc.get('id', '')
        if sid:
            try:
                render_enable_persistence(sid)
                print(f'Persistent disk created for new service {sid}')
            except RuntimeError as e:
                print(f'WARNING: Persistence setup failed for {sid}: {e}')
    return result


def render_delete_service(service_id):
    render_request('DELETE', f'/services/{service_id}')


def render_update_service_plan(service_id, plan):
    # GET the current service so we can echo back the full serviceDetails.
    # Render 500s when the PATCH body omits fields it considers required.
    current    = render_request('GET', f'/services/{service_id}')
    svc        = current.get('service', current)
    current_sd = dict(svc.get('serviceDetails', {}))
    old_plan   = current_sd.get('plan', '?')

    # Strip server-computed fields and maintenanceMode (which Render rejects when
    # upgrading from free — "can only be configured for non-free tier services").
    # Keep everything else so Render has the full context it needs.
    strip = {
        'url', 'sshAddress', 'openPorts', 'runtime',  # computed
        'maintenanceMode', 'ipAllowList',              # enterprise / paid-tier only
        'buildPlan', 'cache', 'previews',              # plan-dependent / not directly writable
    }
    current_sd = {k: v for k, v in current_sd.items() if k not in strip}
    current_sd['plan'] = plan

    print(f'Plan change for {service_id}: {old_plan} → {plan}')
    print(f'PATCH serviceDetails: {json.dumps(current_sd)}')
    result  = render_request('PATCH', f'/services/{service_id}', {'serviceDetails': current_sd})
    applied = (result.get('service', result)
                     .get('serviceDetails', {})
                     .get('plan', '?'))
    print(f'Plan change applied={applied}')
    return result


def render_create_disk(service_id):
    """Attach a 1 GB persistent disk at /data to a Render service."""
    return render_request('POST', '/disks', {
        'serviceId':  service_id,
        'name':       'data',
        'mountPath':  '/data',
        'sizeGB':     1,
    })


def render_enable_persistence(service_id):
    """Create a persistent disk and configure STATE_FILE to use it."""
    render_create_disk(service_id)
    render_update_env_var(service_id, 'STATE_FILE', '/data/election_state.json')


def render_update_env_var(service_id, key, value):
    """Update a single env var on a Render service, preserving all others."""
    current = render_request('GET', f'/services/{service_id}/env-vars')
    env_vars = []
    updated  = False
    for item in (current if isinstance(current, list) else []):
        ev = item.get('envVar', item)
        ev_key = ev.get('key', '')
        if ev_key == key:
            env_vars.append({'key': key, 'value': value})
            updated = True
        elif ev_key:
            env_vars.append({'key': ev_key, 'value': ev.get('value', '')})
    if not updated:
        env_vars.append({'key': key, 'value': value})
    render_request('PUT', f'/services/{service_id}/env-vars', env_vars)


def render_trigger_deploy(service_id):
    return render_request('POST', f'/services/{service_id}/deploys',
                          {'clearCache': 'do_not_clear'})


def render_get_service(service_id):
    return render_request('GET', f'/services/{service_id}')


def render_add_custom_domain(service_id, domain):
    return render_request('POST', f'/services/{service_id}/custom-domains',
                          {'name': domain})


# ── Cloudflare DNS ────────────────────────────────────────────────────────────

def cloudflare_request(method, path, body=None):
    url  = f'{CLOUDFLARE_API_BASE}{path}'
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(
        url, data=data,
        headers={
            'Authorization': f'Bearer {get_cfg("CLOUDFLARE_API_TOKEN")}',
            'Content-Type':  'application/json',
        },
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            detail = json.loads(raw)
        except Exception:
            detail = {'message': raw.decode('utf-8', errors='replace')}
        raise RuntimeError(f'Cloudflare {method} {path} → {e.code}: {detail}')


def cloudflare_create_cname(name, content):
    """Create a DNS-only CNAME record. Returns the Cloudflare record ID."""
    result = cloudflare_request('POST',
        f'/zones/{get_cfg("CLOUDFLARE_ZONE_ID")}/dns_records', {
            'type':    'CNAME',
            'name':    name,
            'content': content,
            'ttl':     1,
            'proxied': False,  # DNS-only — Render needs direct resolution for SSL
        })
    if not result.get('success'):
        raise RuntimeError(f'Cloudflare DNS error: {result.get("errors")}')
    return result['result']['id']


def cloudflare_delete_record(record_id):
    try:
        result = cloudflare_request('DELETE',
            f'/zones/{get_cfg("CLOUDFLARE_ZONE_ID")}/dns_records/{record_id}')
        if not result.get('success'):
            print(f'Cloudflare delete warning: {result.get("errors")}')
    except RuntimeError as e:
        print(f'Cloudflare delete error: {e}')


RENDER_STATUS_MAP = {
    'build_in_progress':      'deploying',
    'update_in_progress':     'deploying',
    'pre_deploy_in_progress': 'deploying',
    'live':                   'live',
    'build_failed':           'failed',
    'update_failed':          'failed',
    'pre_deploy_failed':      'failed',
    'canceled':               'failed',
    'deactivated':            'suspended',
}


def render_get_deploy_status(service_id):
    try:
        result = render_request('GET', f'/services/{service_id}/deploys?limit=1')
        if result and isinstance(result, list) and result:
            raw = result[0].get('deploy', {}).get('status', '')
            return RENDER_STATUS_MAP.get(raw, 'unknown')
    except Exception:
        pass
    return 'unknown'


def _email_when_live(service_id, tenant_id, landing_password):
    """Background thread: poll until the Render service is live, then send welcome email."""
    import time
    for attempt in range(40):          # up to ~20 minutes (40 × 30 s)
        time.sleep(30)
        status = render_get_deploy_status(service_id)
        print(f'[email-thread] tenant={tenant_id} attempt={attempt+1} status={status}')
        if status == 'live':
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
            if tenant and not tenant.get('email_sent') and tenant.get('contact_email'):
                try:
                    send_welcome_email(tenant, landing_password)
                    with lock:
                        tenants = load_tenants()
                        for t in tenants:
                            if t['id'] == tenant_id:
                                t['email_sent'] = True
                        save_tenants(tenants)
                    print(f'[email-thread] Welcome email sent for tenant {tenant_id}')
                except Exception as e:
                    print(f'[email-thread] Email failed for tenant {tenant_id}: {e}')
            return
        if status == 'failed':
            print(f'[email-thread] Deploy failed for tenant {tenant_id} — email not sent')
            return
    print(f'[email-thread] Timed out waiting for tenant {tenant_id} — email not sent')


def enrich_statuses(tenants):
    """Fetch live deploy status from Render for each tenant in parallel."""
    if not tenants or not get_cfg('RENDER_API_KEY'):
        return tenants

    statuses = {}

    def fetch(service_id):
        statuses[service_id] = render_get_deploy_status(service_id)

    threads = [
        threading.Thread(target=fetch, args=(t['render_service_id'],))
        for t in tenants if t.get('render_service_id')
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=8)

    return [
        {**t, 'status': statuses.get(t.get('render_service_id'), t.get('status', 'unknown'))}
        for t in tenants
    ]


# ── Resend email ──────────────────────────────────────────────────────────────

def send_welcome_email(tenant, landing_password):
    app_label = 'Church Voting App' if tenant['app_type'] == 'church' else 'Board Voting App'
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a1a;">
  <h2 style="color: #1e3a5f;">Your {app_label} is Ready</h2>
  <p>Hi {tenant['contact_name']},</p>
  <p>Your voting app has been set up. Use the details below to access it:</p>

  <table style="background:#f8f9fa; border-radius:8px; padding:16px; width:100%; border-collapse:collapse;">
    <tr><td style="padding:6px 12px; font-weight:bold; width:160px;">App URL</td>
        <td style="padding:6px 12px;"><a href="{tenant['url']}">{tenant['url']}</a></td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">Login Password</td>
        <td style="padding:6px 12px; font-family:monospace; font-size:18px; letter-spacing:2px;">{landing_password}</td></tr>
  </table>

  <p style="margin-top:20px;">
    Enter this password when you open the app for the first time.
    Once you are logged in, you can change it and set up all other passwords under <strong>App Settings</strong>.
  </p>

  <h3 style="color:#1e3a5f; margin-top:24px;">Getting Started</h3>
  <ol>
    <li>Open <a href="{tenant['url']}">{tenant['url']}</a> in your browser.</li>
    <li>Enter the login password above.</li>
    <li>Go to <strong>App Settings</strong> and change the password to something you will remember.</li>
    <li>Complete the election setup: add your organisation details, nominees, meeting date, and voter tokens.</li>
    <li>Share the voter URL with your members: <code>{tenant['url']}/vote.html</code></li>
  </ol>

  <p style="color:#666; font-size:13px; margin-top:24px;">
    This app was provisioned by the Voting App Platform administrator.
    Contact your administrator if you need assistance.
  </p>
</body>
</html>
"""
    body = {
        'from':    get_cfg('EMAIL_FROM'),
        'to':      [tenant['contact_email']],
        'subject': f'Your {app_label} is Ready — {tenant["name"]}',
        'html':    html,
    }
    req = urllib.request.Request(
        f'{RESEND_API_BASE}/emails',
        data=json.dumps(body).encode(),
        headers={
            'Authorization': f'Bearer {get_cfg("RESEND_API_KEY")}',
            'Content-Type':  'application/json',
            'User-Agent':    'VotingAppPlatform/1.0',
        },
        method='POST',
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        print(f'Resend HTTP error {e.code}: {raw.decode("utf-8", errors="replace")}')
        raise RuntimeError(f'Resend {e.code}: {raw.decode("utf-8", errors="replace")}')
    except Exception as e:
        print(f'Resend network error: {e}')
        raise


def send_plan_change_email(tenant, old_plan, new_plan):
    plan_labels = {
        'free':     'Free',
        'starter':  'Starter',
        'standard': 'Standard',
        'pro':      'Pro',
    }
    old_label = plan_labels.get(old_plan, old_plan.capitalize())
    new_label = plan_labels.get(new_plan, new_plan.capitalize())
    app_label = 'Church Voting App' if tenant['app_type'] == 'church' else 'Board Voting App'
    is_upgrade = new_plan in PAID_PLANS and old_plan not in PAID_PLANS

    persistence_note = ''
    if is_upgrade:
        persistence_note = """
  <p style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px 16px;margin-top:16px;">
    <strong style="color:#166534;">Persistent storage enabled.</strong>
    Your election configuration and state are now stored on a dedicated disk
    and will be preserved across restarts and redeployments.
  </p>"""
    elif new_plan == 'free':
        persistence_note = """
  <p style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:14px 16px;margin-top:16px;">
    <strong style="color:#92400e;">Note:</strong>
    On the Free plan, election data is not persisted to disk.
    Configuration may be lost if the service restarts.
  </p>"""

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a1a;">
  <h2 style="color: #1e3a5f;">Plan Updated — {tenant['name']}</h2>
  <p>Hi {tenant['contact_name']},</p>
  <p>Your <strong>{app_label}</strong> plan has been updated:</p>

  <table style="background:#f8f9fa; border-radius:8px; padding:16px; width:100%; border-collapse:collapse;">
    <tr><td style="padding:6px 12px; font-weight:bold; width:160px;">Previous Plan</td>
        <td style="padding:6px 12px;">{old_label}</td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">New Plan</td>
        <td style="padding:6px 12px; font-weight:bold; color:#1e3a5f;">{new_label}</td></tr>
    <tr><td style="padding:6px 12px; font-weight:bold;">App URL</td>
        <td style="padding:6px 12px;"><a href="{tenant['url']}">{tenant['url']}</a></td></tr>
  </table>
  {persistence_note}
  <p style="margin-top:20px;">
    A redeployment has been triggered to apply the plan change.
    Your app will be briefly unavailable (~1 minute) while it restarts.
  </p>

  <p style="color:#666; font-size:13px; margin-top:24px;">
    This change was made by the Voting App Platform administrator.
    Contact your administrator if you have any questions.
  </p>
</body>
</html>
"""
    body = {
        'from':    get_cfg('EMAIL_FROM'),
        'to':      [tenant['contact_email']],
        'subject': f'{app_label} Plan Updated: {old_label} → {new_label} — {tenant["name"]}',
        'html':    html,
    }
    req = urllib.request.Request(
        f'{RESEND_API_BASE}/emails',
        data=json.dumps(body).encode(),
        headers={
            'Authorization': f'Bearer {get_cfg("RESEND_API_KEY")}',
            'Content-Type':  'application/json',
            'User-Agent':    'VotingAppPlatform/1.0',
        },
        method='POST',
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        print(f'Resend HTTP error {e.code}: {raw.decode("utf-8", errors="replace")}')
        raise RuntimeError(f'Resend {e.code}: {raw.decode("utf-8", errors="replace")}')
    except Exception as e:
        print(f'Resend network error: {e}')
        raise


# ── Slug / name helpers ───────────────────────────────────────────────────────

def make_slug(org_name):
    slug = org_name.lower()
    slug = ''.join(c if c.isalnum() else '-' for c in slug)
    return '-'.join(part for part in slug.split('-') if part)[:40]


def make_service_name(org_name, app_type):
    slug   = make_slug(org_name)[:30]
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
                tenants = list(load_tenants())
            tenants = enrich_statuses(tenants)
            return self._json(200, tenants)

        # /api/tenants/{id}/render-info — raw Render service details for diagnostics
        parts = path.split('/')
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'tenants' and parts[4] == 'render-info':
            if not self._auth():
                return self._err(401, 'Unauthorized')
            tenant_id = parts[3]
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
            if not tenant:
                return self._err(404, 'Tenant not found')
            try:
                data = render_request('GET', f'/services/{tenant["render_service_id"]}')
                return self._json(200, data)
            except RuntimeError as e:
                return self._err(502, str(e))

        if path == '/api/config':
            resend_key = get_cfg('RESEND_API_KEY')
            email_from = get_cfg('EMAIL_FROM')
            return self._json(200, {
                'emailConfigured':  bool(resend_key and email_from != 'onboarding@resend.dev'),
                'renderConfigured': bool(get_cfg('RENDER_API_KEY')),
            })

        if path == '/api/settings':
            if not self._auth():
                return self._err(401, 'Unauthorized')
            result = {}
            for key in _ENV_DEFAULTS:
                val = get_cfg(key)
                result[key] = '****' if (val and key in _SENSITIVE_KEYS) else val
            return self._json(200, result)

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
            incoming    = payload.get('passwordHash', '')
            stored_hash = get_cfg('ADMIN_PASSWORD_HASH')
            if not stored_hash:
                return self._err(503, 'Admin password not configured on server')
            if incoming != stored_hash:
                return self._err(401, 'Wrong password')
            token = create_session()
            return self._json(200, {'token': token})

        if not self._auth():
            return self._err(401, 'Unauthorized')

        # ── /api/settings/password — change admin password ────────────────────
        if path == '/api/settings/password':
            payload = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            current_hash = payload.get('currentHash', '')
            new_hash     = payload.get('newHash', '')
            if not current_hash or not new_hash:
                return self._err(400, 'currentHash and newHash required')
            stored = get_cfg('ADMIN_PASSWORD_HASH')
            if stored and current_hash != stored:
                return self._err(403, 'Current password is incorrect')
            save_settings({'ADMIN_PASSWORD_HASH': new_hash})
            return self._json(200, {'ok': True})

        # ── /api/settings/test-email — send a test email ──────────────────────
        if path == '/api/settings/test-email':
            payload    = self._read_json() or {}
            to_address = payload.get('to', '').strip()
            if not to_address:
                return self._err(400, 'to address required')
            resend_key = get_cfg('RESEND_API_KEY')
            email_from = get_cfg('EMAIL_FROM')
            if not resend_key:
                return self._err(503, 'RESEND_API_KEY is not configured')
            body = {
                'from':    email_from,
                'to':      [to_address],
                'subject': 'Voting App Platform — Test Email',
                'html':    '<p>This is a test email from the Voting App Platform admin portal. '
                           'If you received this, email sending is working correctly.</p>'
                           f'<p style="color:#666;font-size:12px">Sent from: {email_from}</p>',
            }
            req = urllib.request.Request(
                f'{RESEND_API_BASE}/emails',
                data=json.dumps(body).encode(),
                headers={
                    'Authorization': f'Bearer {resend_key}',
                    'Content-Type':  'application/json',
                    'User-Agent':    'VotingAppPlatform/1.0',
                },
                method='POST',
            )
            try:
                resp   = urllib.request.urlopen(req, timeout=15)
                result = json.loads(resp.read())
                return self._json(200, {'ok': True, 'resend': result,
                                        'from': email_from, 'to': to_address})
            except urllib.error.HTTPError as e:
                raw = e.read().decode('utf-8', errors='replace')
                return self._json(200, {'ok': False, 'error': f'Resend HTTP {e.code}',
                                        'detail': raw, 'from': email_from, 'to': to_address})
            except Exception as e:
                return self._json(200, {'ok': False, 'error': str(e),
                                        'from': email_from, 'to': to_address})

        # ── /api/settings — update configuration ──────────────────────────────
        if path == '/api/settings':
            payload = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            updates    = payload.get('settings', {})
            valid_keys = set(_ENV_DEFAULTS.keys()) - {'ADMIN_PASSWORD_HASH'}
            clean = {k: str(v).strip() for k, v in updates.items()
                     if k in valid_keys and v is not None}
            if clean:
                save_settings(clean)
            return self._json(200, {'ok': True})

        # ── /api/tenants — provision new tenant ───────────────────────────────
        if path == '/api/tenants':
            payload = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')

            required = ['name', 'slug', 'app_type', 'contact_name', 'contact_email', 'plan', 'region']
            missing  = [f for f in required if not payload.get(f)]
            if missing:
                return self._err(400, f'Missing fields: {", ".join(missing)}')

            if payload['app_type'] not in ('church', 'board'):
                return self._err(400, 'app_type must be church or board')

            service_name      = make_service_name(payload['name'], payload['app_type'])
            landing_password  = generate_landing_password()
            landing_pw_hash   = hashlib.sha256(landing_password.encode('utf-8')).hexdigest()

            try:
                result = render_create_service(
                    name                  = service_name,
                    app_type              = payload['app_type'],
                    plan                  = payload['plan'],
                    region                = payload['region'],
                    landing_password_hash = landing_pw_hash,
                )
            except RuntimeError as e:
                return self._err(502, str(e))

            svc        = result.get('service', result)
            service_id = svc.get('id', '')
            render_url = (svc.get('serviceDetails', {}).get('url')
                          or f'https://{service_name}.onrender.com')

            slug              = payload['slug']
            custom_domain     = ''
            custom_domain_url = ''
            dns_cname_name    = ''
            dns_cname_value   = f'{service_name}.onrender.com'
            cf_record_id      = ''

            custom_domain_base = get_cfg('CUSTOM_DOMAIN').strip().lower().rstrip('/')
            if custom_domain_base and service_id:
                custom_domain     = f'{slug}.{custom_domain_base}'
                custom_domain_url = f'https://{custom_domain}'
                dns_cname_name    = slug
                try:
                    render_add_custom_domain(service_id, custom_domain)
                    render_update_env_var(service_id, 'CANONICAL_URL', custom_domain_url)
                except RuntimeError as e:
                    print(f'Custom domain registration failed: {e}')
                    custom_domain     = ''
                    custom_domain_url = ''

            if custom_domain and get_cfg('CLOUDFLARE_API_TOKEN') and get_cfg('CLOUDFLARE_ZONE_ID'):
                try:
                    cf_record_id = cloudflare_create_cname(custom_domain, dns_cname_value)
                    print(f'Cloudflare CNAME created: {custom_domain} → {dns_cname_value}')
                except RuntimeError as e:
                    print(f'Cloudflare DNS creation failed: {e}')

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
                'render_url':       render_url,
                'url':              custom_domain_url or render_url,
                'custom_domain':    custom_domain,
                'dns_cname_name':   dns_cname_name,
                'dns_cname_value':  dns_cname_value,
                'cf_record_id':     cf_record_id,
                'plan':             payload['plan'],
                'region':           payload['region'],
                'has_disk':         payload['plan'] in PAID_PLANS,
                'status':           'deploying',
                'provisioned_at':   datetime.now(timezone.utc).isoformat(),
                'last_deployed_at': datetime.now(timezone.utc).isoformat(),
                'landing_password': landing_password,
                'email_sent':       False,
            }

            with lock:
                tenants = load_tenants()
                tenants.append(tenant)
                save_tenants(tenants)

            # Send welcome email only after the service is live (background thread).
            if get_cfg('RESEND_API_KEY') and tenant['contact_email']:
                th = threading.Thread(
                    target=_email_when_live,
                    args=(service_id, tenant['id'], landing_password),
                    daemon=True,
                )
                th.start()
                print(f'Email thread started for tenant {tenant["id"]} — will send when live')

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
            # Ensure CANONICAL_URL is set so server.py uses the custom domain
            # for the voter ballot URL, not the internal onrender.com address.
            canonical = tenant.get('url', '').rstrip('/')
            if canonical and 'onrender.com' not in canonical:
                try:
                    render_update_env_var(tenant['render_service_id'], 'CANONICAL_URL', canonical)
                except RuntimeError as e:
                    print(f'WARNING: Could not set CANONICAL_URL for {tenant_id}: {e}')
            try:
                render_trigger_deploy(tenant['render_service_id'])
            except RuntimeError as e:
                return self._err(502, str(e))
            with lock:
                tenants = load_tenants()
                for t in tenants:
                    if t['id'] == tenant_id:
                        t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                        t['status'] = 'deploying'
                save_tenants(tenants)
            return self._json(200, {'ok': True})

        # ── /api/tenants/{id}/reset-password — generate new landing password ───
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'tenants' and parts[4] == 'reset-password':
            tenant_id = parts[3]
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
            if not tenant:
                return self._err(404, 'Tenant not found')
            new_password  = generate_landing_password()
            new_pw_hash   = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
            try:
                render_update_env_var(tenant['render_service_id'], 'LANDING_PASSWORD_HASH', new_pw_hash)
                render_trigger_deploy(tenant['render_service_id'])
            except RuntimeError as e:
                return self._err(502, str(e))
            with lock:
                tenants = load_tenants()
                for t in tenants:
                    if t['id'] == tenant_id:
                        t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                        t['status'] = 'deploying'
                        t['landing_password'] = new_password
                save_tenants(tenants)
            return self._json(200, {'ok': True, 'password': new_password})

        # ── /api/tenants/{id}/update-contact — edit contact details ─────────────
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'tenants' and parts[4] == 'update-contact':
            tenant_id = parts[3]
            payload   = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            new_name  = payload.get('contact_name', '').strip()
            new_email = payload.get('contact_email', '').strip()
            new_phone = payload.get('contact_phone', '').strip()
            if not new_name or not new_email:
                return self._err(400, 'contact_name and contact_email are required')
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
                if not tenant:
                    return self._err(404, 'Tenant not found')
                for t in tenants:
                    if t['id'] == tenant_id:
                        t['contact_name']  = new_name
                        t['contact_email'] = new_email
                        t['contact_phone'] = new_phone
                save_tenants(tenants)
            return self._json(200, {'ok': True})

        # ── /api/tenants/{id}/set-canonical-url — update app/voter URL ─────────
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'tenants' and parts[4] == 'set-canonical-url':
            tenant_id = parts[3]
            payload   = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            new_url = payload.get('url', '').strip().rstrip('/')
            if not new_url.startswith('https://'):
                return self._err(400, 'URL must start with https://')
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
            if not tenant:
                return self._err(404, 'Tenant not found')
            sid = tenant.get('render_service_id', '')
            try:
                render_update_env_var(sid, 'CANONICAL_URL', new_url)
                render_trigger_deploy(sid)
            except RuntimeError as e:
                return self._err(502, str(e))
            with lock:
                tenants = load_tenants()
                for t in tenants:
                    if t['id'] == tenant_id:
                        t['url']              = new_url
                        t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                        t['status']           = 'deploying'
                save_tenants(tenants)
            return self._json(200, {'ok': True, 'url': new_url})

        # ── /api/tenants/{id}/upgrade — change Render plan ───────────────────
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'tenants' and parts[4] == 'upgrade':
            tenant_id = parts[3]
            payload   = self._read_json()
            if not payload:
                return self._err(400, 'Invalid JSON')
            new_plan = payload.get('plan', '').strip().lower()
            valid_plans = ('free', 'starter', 'standard', 'pro')
            if new_plan not in valid_plans:
                return self._err(400, f'Invalid plan — must be one of: {", ".join(valid_plans)}')
            with lock:
                tenants = load_tenants()
                tenant  = next((t for t in tenants if t['id'] == tenant_id), None)
            if not tenant:
                return self._err(404, 'Tenant not found')
            if tenant.get('plan') == new_plan:
                return self._err(400, 'Tenant is already on that plan')
            sid = tenant.get('render_service_id', '')
            try:
                render_update_service_plan(sid, new_plan)
            except RuntimeError as e:
                return self._err(502, str(e))
            # Enable persistent storage if moving onto a paid plan for the first time.
            disk_created = tenant.get('has_disk', False)
            if new_plan in PAID_PLANS and not disk_created:
                try:
                    render_enable_persistence(sid)
                    disk_created = True
                    print(f'Persistent disk created for upgraded service {sid}')
                except RuntimeError as e:
                    print(f'WARNING: Persistence setup failed for {sid}: {e}')
            try:
                render_trigger_deploy(sid)
            except RuntimeError as e:
                print(f'WARNING: Redeploy failed after plan change for {sid}: {e}')
            old_plan = tenant.get('plan', 'free')
            with lock:
                tenants = load_tenants()
                for t in tenants:
                    if t['id'] == tenant_id:
                        t['plan']             = new_plan
                        t['has_disk']         = disk_created
                        t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                        t['status']           = 'deploying'
                save_tenants(tenants)
            if get_cfg('RESEND_API_KEY') and tenant.get('contact_email'):
                def _send_plan_email():
                    try:
                        send_plan_change_email(tenant, old_plan, new_plan)
                        print(f'Plan change email sent for tenant {tenant_id}')
                    except Exception as e:
                        print(f'Plan change email failed for tenant {tenant_id}: {e}')
                threading.Thread(target=_send_plan_email, daemon=True).start()
            return self._json(200, {'ok': True, 'plan': new_plan, 'has_disk': disk_created})

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
                            canonical = t.get('url', '').rstrip('/')
                            if canonical and 'onrender.com' not in canonical:
                                render_update_env_var(t['render_service_id'], 'CANONICAL_URL', canonical)
                            render_trigger_deploy(t['render_service_id'])
                            t['last_deployed_at'] = datetime.now(timezone.utc).isoformat()
                            t['status'] = 'deploying'
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

                if tenant.get('render_service_id'):
                    try:
                        render_delete_service(tenant['render_service_id'])
                    except RuntimeError as e:
                        print(f'Render delete error for {tenant_id}: {e}')

                if tenant.get('cf_record_id') and get_cfg('CLOUDFLARE_ZONE_ID'):
                    cloudflare_delete_record(tenant['cf_record_id'])

                tenants = [t for t in tenants if t['id'] != tenant_id]
                save_tenants(tenants)

            return self._json(200, {'ok': True})

        self._err(404, 'Not found')


def main():
    if not get_cfg('ADMIN_PASSWORD_HASH'):
        print('WARNING: ADMIN_PASSWORD_HASH not configured — all logins will fail.')
    if not get_cfg('RENDER_API_KEY'):
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
    print(f'  Settings:  {SETTINGS_FILE}')
    print('  Press Ctrl+C to stop.')
    print('=' * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')


if __name__ == '__main__':
    main()
