# Church Office Bearer Election System

A browser-based voting application for conducting Reformed church congregational elections for the offices of Elder and Deacon. Runs on a local Python server with no internet connection required — all data is stored on the meeting laptop and shared in real time across all devices on the local Wi-Fi network.

---

## Features

- Multi-round elections with automatic majority detection
- Separate, independent elections for Elder and Deacon offices
- Either or both offices can be configured — unconfigured offices are skipped automatically
- Digital voting via members' phones/tablets using unique 4-digit token codes
- Paper ballot entry station for members who prefer to vote on paper
- Two separate password-protected areas: admin (setup & control) and results (chairman only)
- Real-time vote count updates on the Round Control screen
- Voter page auto-updates when rounds open, close, or a new office begins
- Token cards with QR codes for easy voter access
- Printable paper ballots
- No internet required — runs entirely on a local network

---

## Files

| File | Purpose |
|---|---|
| `server.py` | Local Python HTTP server — serves the app and stores all shared election state |
| `index.html` | Admin hub — Election Setup, Round Control, Paper Ballot Entry, Election Dashboard |
| `vote.html` | Voter page — token entry, ballot, confirmation |
| `election_state.json` | Shared state file, created automatically on first save |
| `render.yaml` | One-click deployment config for Render.com |
| `requirements.txt` | No external dependencies (Python stdlib only) |
| `build_manual.py` | Generates `manual.docx` (requires `python-docx`) |
| `manual.docx` | Complete Word document user manual |
| `manual.html` | HTML version of the user manual |

---

## Quick Start

**Requirements:** Python 3.8 or later. No packages to install.

```bash
# 1. Start the server
python3 server.py

# 2. Open the admin hub in a browser on the laptop
#    http://localhost:8080/

# 3. Share the voter URL with members (printed on token cards)
#    http://<your-laptop-ip>:8080/vote.html
```

The server prints the voter URL and local IP address on startup.

---

## How It Works

### Screens (index.html — admin)

| Screen | Access | Purpose |
|---|---|---|
| Landing Page | Open | Navigation hub |
| Election Setup | Admin password | Configure nominees, tokens, passwords, voter URL |
| Round Control | Admin password | Open/close voting, monitor ballots, end rounds |
| Paper Ballot Entry | Open | Volunteer enters paper votes in real time |
| Election Dashboard | Results password | Chairman views live status and confidential results |

### Voter Page (vote.html)

Members open the voter URL on their phone, enter their 4-digit token, select candidates, and submit. The page updates automatically when:
- A round opens or closes
- A new round begins
- The election moves to the next office
- The election is complete

### Passwords

| Password | Protects | Default |
|---|---|---|
| Admin password | Election Setup and Round Control | `election2024` |
| Results password | Election Dashboard | `results2024` |

> **Change both passwords before the election** in Election Setup → Settings tab.

---

## Election Flow

```
Election Setup
    ↓
Generate & Print Token Cards
    ↓
Round Control → Start Round 1
    ↓
Voting Open → members vote on phones or paper
    ↓
Close Voting → End Round
    ↓
Round Transition: confirm elected, select who advances
    ↓
Launch Next Round  ─── or ───  Complete This Office
    ↓                                   ↓
(repeat)                        Next office (if configured)
                                        ↓
                               Election Complete screen
                                        ↓
                          Chairman views Election Dashboard
```

---

## Token System

- Each eligible voter receives one token card before the meeting
- Token cards include: congregation name, 4-digit code, QR code, and voter URL
- One token covers both the Elder and Deacon elections and all rounds
- Each token can only be used once per round per office

---

## Cloud Deployment (Render.com)

The app can be hosted publicly so voters access it over the internet instead of a local network.

1. Push this repository to GitHub
2. Go to [render.com](https://render.com) → **New → Blueprint**
3. Connect the repository — Render reads `render.yaml` automatically
4. Click **Apply** (takes ~2 minutes)
5. Your URL appears in the Render dashboard (e.g. `https://church-election.onrender.com`)
6. In Election Setup → Settings, set the voter URL to `https://church-election.onrender.com/vote.html`

**Note:** A persistent disk (Render Starter plan, ~$7/month) is recommended to ensure `election_state.json` survives restarts. The free plan is acceptable for a single election day as long as the service is not redeployed mid-election.

---

## Security

- Passwords are stored as SHA-256 hashes — never as plain text
- `POST /api/state` (full state write) requires the correct `adminPasswordHash` in the payload — random internet users cannot corrupt election data
- `POST /api/ballot` (vote submission) validates the token, office, and round before writing — votes are applied atomically under a thread lock, preventing race conditions when multiple voters submit simultaneously
- `election_state.json` is excluded from version control via `.gitignore`

---

## License

Private — for internal church use only.
