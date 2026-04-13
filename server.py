#!/usr/bin/env python3
"""
Church Voting App — HTTP server

Serves the static HTML files and provides two API endpoints so all
devices share the same election state:

  GET  /api/state        — read current state (public)
  POST /api/state        — overwrite state (admin-authenticated)
  POST /api/ballot       — atomic ballot submission (token-authenticated)

Local usage:
    python3 server.py          # port 8080
    python3 server.py 9000     # custom port

Cloud deployment (Render / Railway / Fly.io):
    Set the PORT and STATE_FILE environment variables in your hosting
    dashboard. The server reads PORT automatically; platforms inject it.

Security model for public hosting:
    /api/state POST requires the incoming JSON to contain the correct
    adminPasswordHash. If no state file exists yet (first run), the
    first write is accepted unconditionally. This means only the person
    who knows the admin password can overwrite the election state —
    preventing random internet users from corrupting the data.
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Configuration (override via environment variables) ───────────────────────
# PORT: injected automatically by Render, Railway, Fly.io, etc.
PORT = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else 8080))

# STATE_FILE: set to a persistent-disk path on cloud platforms, e.g.
#   Render:  /data/election_state.json  (add a Disk in the Render dashboard)
#   Railway: /data/election_state.json  (add a Volume in the Railway dashboard)
STATE_FILE = os.environ.get(
    'STATE_FILE',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'election_state.json')
)

SERVE_DIR = os.path.dirname(os.path.abspath(__file__))
lock      = threading.Lock()

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.ico':  'image/x-icon',
    '.svg':  'image/svg+xml',
    '.woff2': 'font/woff2',
    '.woff':  'font/woff',
}


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Print a concise access log instead of the verbose default
        print(f'{self.command} {self.path} → {args[1] if len(args) > 1 else "?"}')

    # ── Common response helper ─────────────────────────────
    def _send(self, code, ctype, body: bytes):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ── GET ───────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split('?')[0]

        # API: read state (public — voters need this)
        if path == '/api/state':
            with lock:
                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE, 'r', encoding='utf-8') as f:
                        data = f.read().encode('utf-8')
                else:
                    data = b'{}'
            self._send(200, 'application/json; charset=utf-8', data)
            return

        # Static file serving
        if path == '/':
            path = '/index.html'
        local = os.path.normpath(os.path.join(SERVE_DIR, path.lstrip('/')))
        # Prevent path traversal attacks
        if not local.startswith(SERVE_DIR):
            self._send(403, 'text/plain', b'Forbidden')
            return
        if os.path.isfile(local):
            ext   = os.path.splitext(local)[1].lower()
            ctype = MIME.get(ext, 'application/octet-stream')
            with open(local, 'rb') as f:
                self._send(200, ctype, f.read())
        else:
            self._send(404, 'text/plain', b'Not found')

    # ── POST ──────────────────────────────────────────────
    def do_POST(self):
        path   = self.path.split('?')[0]
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send(400, 'application/json; charset=utf-8',
                       b'{"error":"Invalid JSON"}')
            return

        # ── /api/state — full state write (admin-authenticated) ──────────────
        if path == '/api/state':
            with lock:
                # Security: if a state file already exists with a non-empty
                # adminPasswordHash, the incoming payload must have the same
                # hash. This prevents unauthenticated writes over the internet.
                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, 'r', encoding='utf-8') as f:
                            existing = json.load(f)
                        stored_hash   = existing.get('adminPasswordHash', '')
                        incoming_hash = payload.get('adminPasswordHash', '')
                        if stored_hash and stored_hash != incoming_hash:
                            self._send(403, 'application/json; charset=utf-8',
                                       b'{"error":"Unauthorized"}')
                            return
                    except (json.JSONDecodeError, OSError):
                        pass  # Corrupt file — allow overwrite to recover

                # Ensure the directory for STATE_FILE exists
                os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    f.write(body.decode('utf-8'))

            self._send(200, 'application/json; charset=utf-8', b'{"ok":true}')
            return

        # ── /api/ballot — atomic ballot submission (token-validated) ─────────
        if path == '/api/ballot':
            office_key = payload.get('office')
            round_num  = payload.get('round')
            token_code = payload.get('tokenCode')
            selections = payload.get('selections', [])

            def err(msg):
                self._send(400, 'application/json; charset=utf-8',
                           json.dumps({'error': msg}).encode())

            if office_key not in ('elder', 'deacon'):
                return err('Invalid office')

            with lock:
                if not os.path.exists(STATE_FILE):
                    return err('No election configured')
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                if state.get('activeOffice') != office_key:
                    return err('Office not active')

                office = state.get(office_key, {})
                if not office.get('votingOpen'):
                    return err('Voting is closed')
                if office.get('currentRound') != round_num:
                    return err('Round has changed')

                # Validate token
                token = next((t for t in state.get('tokens', [])
                              if t.get('code') == token_code), None)
                if not token:
                    return err('Token not found')
                used = token.setdefault('usedRounds', {}) \
                            .setdefault(office_key, [])
                if round_num in used:
                    return err('Token already used this round')

                # Filter to valid candidates only
                valid_names = [c['name'] for c in office.get('candidates', [])]
                valid_sel   = [s for s in selections if s in valid_names]
                if not valid_sel:
                    return err('No valid candidates selected')

                # Record ballot atomically
                from datetime import datetime, timezone
                office.setdefault('ballots', []).append({
                    'token':     token_code,
                    'votes':     valid_sel,
                    'round':     round_num,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                for candidate in office.get('candidates', []):
                    if candidate['name'] in valid_sel:
                        candidate['votes'] = candidate.get('votes', 0) + 1
                used.append(round_num)

                state[office_key] = office
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state, f)

            self._send(200, 'application/json; charset=utf-8', b'{"ok":true}')
            return

        self._send(404, 'text/plain', b'Not found')


def main():
    # Ensure state file directory exists before we start
    state_dir = os.path.dirname(STATE_FILE)
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)

    server = HTTPServer(('0.0.0.0', PORT), Handler)

    # Detect public URL (set automatically by Render)
    public_url = os.environ.get('RENDER_EXTERNAL_URL', '')

    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'

    print('=' * 55)
    print('  Church Election Server')
    print('=' * 55)
    if public_url:
        print(f'  Public URL:      {public_url}/')
        print(f'  Voter page:      {public_url}/vote.html')
    else:
        print(f'  Admin / local:   http://localhost:{PORT}/')
        print(f'  Voter devices:   http://{local_ip}:{PORT}/vote.html')
    print(f'  State file:      {STATE_FILE}')
    print('  Press Ctrl+C to stop.')
    print('=' * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')


if __name__ == '__main__':
    main()
