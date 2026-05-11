#!/usr/bin/env python3
"""
Voting App Platform — Tenant Server

Serves church or board voting app based on APP_TYPE env var:
  APP_TYPE=church  → serves church/ directory
  APP_TYPE=board   → serves board/ directory

Local usage:
    APP_TYPE=church python3 server.py
    APP_TYPE=board  python3 server.py 9000

Cloud deployment (Render):
    Set APP_TYPE, PORT, and STATE_FILE environment variables.
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

APP_TYPE = os.environ.get('APP_TYPE', 'church')
PORT     = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else 8080))

STATE_FILE = os.environ.get(
    'STATE_FILE',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'election_state.json')
)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
SERVE_DIR = os.path.join(BASE_DIR, APP_TYPE)  # ./church/ or ./board/
lock      = threading.Lock()

MIME = {
    '.html':  'text/html; charset=utf-8',
    '.css':   'text/css; charset=utf-8',
    '.js':    'application/javascript; charset=utf-8',
    '.json':  'application/json; charset=utf-8',
    '.png':   'image/png',
    '.jpg':   'image/jpeg',
    '.ico':   'image/x-icon',
    '.svg':   'image/svg+xml',
    '.woff2': 'font/woff2',
    '.woff':  'font/woff',
}


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

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/api/state':
            with lock:
                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE, 'r', encoding='utf-8') as f:
                        data = f.read().encode('utf-8')
                else:
                    data = b'{}'
            self._send(200, 'application/json; charset=utf-8', data)
            return

        if path == '/':
            path = '/index.html'
        local = os.path.normpath(os.path.join(SERVE_DIR, path.lstrip('/')))
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

    # ── POST ──────────────────────────────────────────────────────────────────
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

                try:
                    os.makedirs(os.path.dirname(STATE_FILE) or '.', exist_ok=True)
                except OSError:
                    pass  # No disk mounted — write will fail gracefully below
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    f.write(body.decode('utf-8'))

            self._send(200, 'application/json; charset=utf-8', b'{"ok":true}')
            return

        # ── /api/ballot — board election ballot (board app) ───────────────────
        if path == '/api/ballot':
            round_num  = payload.get('round')
            token_code = payload.get('tokenCode')
            selections = payload.get('selections', [])

            def err(msg):
                self._send(400, 'application/json; charset=utf-8',
                           json.dumps({'error': msg}).encode())

            with lock:
                if not os.path.exists(STATE_FILE):
                    return err('No election configured')
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                election = state.get('election', {})
                if not election.get('votingOpen'):
                    return err('Voting is closed')
                if election.get('currentRound') != round_num:
                    return err('Round has changed')

                token = next((t for t in state.get('tokens', [])
                              if t.get('code') == token_code), None)
                if not token:
                    return err('Token not found')

                used = token.setdefault('usedRounds', [])
                if round_num in used:
                    return err('Token already used this round')

                valid_names = [c['name'] for c in election.get('candidates', [])]
                valid_sel   = [s for s in selections if s in valid_names]
                if not valid_sel:
                    return err('No valid candidates selected')

                from datetime import datetime, timezone
                election.setdefault('ballots', []).append({
                    'token':     token_code,
                    'votes':     valid_sel,
                    'round':     round_num,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                for candidate in election.get('candidates', []):
                    if candidate['name'] in valid_sel:
                        candidate['votes'] = candidate.get('votes', 0) + 1
                used.append(round_num)

                state['election'] = election
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state, f)

            self._send(200, 'application/json; charset=utf-8', b'{"ok":true}')
            return

        # ── /api/motion-ballot — motion vote (board app) ──────────────────────
        if path == '/api/motion-ballot':
            token_code = payload.get('tokenCode')
            selections = payload.get('selections', [])

            def merr(msg):
                self._send(400, 'application/json; charset=utf-8',
                           json.dumps({'error': msg}).encode())

            with lock:
                if not os.path.exists(STATE_FILE):
                    return merr('No election configured')
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                motion = state.get('motion', {})
                if not motion.get('votingOpen'):
                    return merr('Motion voting is not open')
                if motion.get('complete'):
                    return merr('Motion vote is already complete')

                token = next((t for t in state.get('tokens', [])
                              if t.get('code') == token_code), None)
                if not token:
                    return merr('Token not found')

                ballots = motion.get('ballots', [])
                if any(b.get('token') == token_code for b in ballots):
                    return merr('Token already used for this motion')

                valid_options = motion.get('options', [])
                vpv       = motion.get('votesPerVoter', 1)
                valid_sel = [s for s in selections if s in valid_options][:vpv]
                if not valid_sel:
                    return merr('No valid options selected')

                from datetime import datetime, timezone
                ballots.append({
                    'token':     token_code,
                    'votes':     valid_sel,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                motion['ballots'] = ballots

                results = motion.get('results', {})
                for opt in valid_sel:
                    results[opt] = results.get(opt, 0) + 1
                motion['results'] = results

                state['motion'] = motion
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state, f)

            self._send(200, 'application/json; charset=utf-8', b'{"ok":true}')
            return

        # ── /api/voting-ballot — congregational vote (church app) ─────────────
        if path == '/api/voting-ballot':
            token_code = payload.get('tokenCode')
            answer     = payload.get('answer')

            def cerr(msg):
                self._send(400, 'application/json; charset=utf-8',
                           json.dumps({'error': msg}).encode())

            with lock:
                if not os.path.exists(STATE_FILE):
                    return cerr('No state configured')
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                voting = state.get('voting', {})
                if not voting.get('question'):
                    return cerr('No vote configured')
                if not voting.get('votingOpen'):
                    return cerr('Voting is not open')

                valid_answers = voting.get('answers', [])
                if answer not in valid_answers:
                    return cerr('Invalid answer')

                token = next((t for t in state.get('tokens', [])
                              if t.get('code') == token_code), None)
                if not token:
                    return cerr('Token not found')

                if token.get('votedCurrentRound'):
                    return cerr('Token already used')

                from datetime import datetime, timezone
                voting.setdefault('ballots', []).append({
                    'token':     token_code,
                    'answer':    answer,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                results = voting.get('results', {})
                results[answer] = results.get(answer, 0) + 1
                voting['results'] = results
                token['votedCurrentRound'] = True

                state['voting'] = voting
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state, f)

            self._send(200, 'application/json; charset=utf-8', b'{"ok":true}')
            return

        # ── /api/tinyurl — TinyURL proxy (board app) ──────────────────────────
        if path == '/api/tinyurl':
            import urllib.request, urllib.error

            action = payload.get('action', '')
            alias  = payload.get('alias', '').strip()

            if action == 'check':
                class _NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *a, **kw):
                        return None
                opener = urllib.request.build_opener(_NoRedirect)
                try:
                    opener.open(f'https://tinyurl.com/{alias}', timeout=5)
                    available = False
                except urllib.error.HTTPError as e:
                    available = (e.code == 404)
                except Exception:
                    available = True
                self._send(200, 'application/json; charset=utf-8',
                           json.dumps({'available': available}).encode())
                return

            elif action == 'create':
                url_to_shorten = payload.get('url', '')
                api_key        = payload.get('apikey', '')
                body_data      = {'url': url_to_shorten, 'domain': 'tinyurl.com'}
                if alias:
                    body_data['alias'] = alias
                req = urllib.request.Request(
                    'https://api.tinyurl.com/create',
                    data=json.dumps(body_data).encode(),
                    headers={
                        'Content-Type':  'application/json',
                        'Authorization': f'Bearer {api_key}',
                    },
                    method='POST',
                )
                try:
                    resp   = urllib.request.urlopen(req, timeout=10)
                    result = json.loads(resp.read())
                except urllib.error.HTTPError as e:
                    raw    = e.read()
                    result = json.loads(raw) if raw else {'code': e.code, 'errors': [str(e)]}
                except Exception as e:
                    result = {'code': -1, 'errors': [str(e)]}
                self._send(200, 'application/json; charset=utf-8',
                           json.dumps(result).encode())
                return

            self._send(400, 'application/json; charset=utf-8',
                       b'{"error":"Unknown action"}')
            return

        self._send(404, 'text/plain', b'Not found')


def main():
    state_dir = os.path.dirname(STATE_FILE) or '.'
    try:
        os.makedirs(state_dir, exist_ok=True)
    except OSError:
        print(f'WARNING: Cannot create {state_dir} — no disk mounted. '
              'Election state will not persist across restarts.')

    # Seed initial state on first start (or after ephemeral storage wipe).
    # Includes default password hashes so the app is immediately usable
    # even on free-tier instances without a persistent disk.
    import hashlib
    def _sha256(s):
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    public_url = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    if not os.path.exists(STATE_FILE):
        landing_hash = os.environ.get('LANDING_PASSWORD_HASH', '') or _sha256('votevote2024')
        seed = {
            'appType':              APP_TYPE,
            'landingPasswordHash':  landing_hash,
            'adminPasswordHash':    _sha256('churchvoting' if APP_TYPE == 'church' else 'boardvoting'),
            'electionPasswordHash': _sha256('election2024'),
            'resultsPasswordHash':  _sha256('results2024'),
            'tokensPasswordHash':   _sha256('tokens2024'),
            'paperBallotPasswordHash': _sha256('paperentry2024'),
        }
        if APP_TYPE == 'church':
            seed['votingPasswordHash'] = _sha256('voting2024')
        if public_url:
            seed['customVoteUrl'] = f'{public_url}/vote.html'
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(seed, f)
            print(f'Seeded initial state (appType={APP_TYPE})')
        except OSError:
            pass

    server = HTTPServer(('0.0.0.0', PORT), Handler)

    public_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'

    app_label = 'Church' if APP_TYPE == 'church' else 'Board'
    print('=' * 55)
    print(f'  {app_label} Voting App Server  (APP_TYPE={APP_TYPE})')
    print('=' * 55)
    if public_url:
        print(f'  Public URL:    {public_url}/')
        print(f'  Voter page:    {public_url}/vote.html')
    else:
        print(f'  Admin / local: http://localhost:{PORT}/')
        print(f'  Voter devices: http://{local_ip}:{PORT}/vote.html')
    print(f'  Serving from:  {SERVE_DIR}')
    print(f'  State file:    {STATE_FILE}')
    print('  Press Ctrl+C to stop.')
    print('=' * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')


if __name__ == '__main__':
    main()
