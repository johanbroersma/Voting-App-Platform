# Changelog

All notable changes to the Church Office Bearer Election System are documented here.

---

## [1.1.4] — 2026-04-06
### Added
- Election Dashboard now shows Round 1 pre-round information when the election is configured but voting has not yet started: nominee list, positions to fill, votes per voter, and majority required. Previously showed "No results yet."

---

## [1.1.3] — 2026-04-06
### Changed
- Next round now starts with voting **closed** when the officer clicks "Launch Next Round". The officer must explicitly click Open Voting in Round Control, giving time to announce the new round before votes can be submitted.

---

## [1.1.2] — 2026-04-06
### Fixed
- Election Dashboard was not showing live round results while voting was open. The `isActiveRound` condition was missing — only the post-round "awaiting transition" state was handled. Dashboard now shows the current round results card in all three states: voting open (green tag), voting closed awaiting transition (amber tag), and after transition (committed history).

---

## [1.1.1] — 2026-04-06
### Added
- Election Dashboard status header now shows "Majority required: N" pill next to the round and voting status, using the correct round-aware threshold
- Election Dashboard shows full round results (vote counts, bars, majority badges) immediately when a round is ended, before the election officer processes the transition — labelled "Round N Results — Awaiting transition"

---

## [1.1.0] — 2026-04-06
### Added
- Absentee vote support: enter number of absentee votes in Election Setup → Details tab
- Absentee checkbox on Paper Ballot Entry screen (Round 1 only)
- "Absentee" badge on each absentee ballot in the paper ballot log, with count summary
- Absentee stat box on Round Control screen (Round 1 only)
- Majority threshold is now round-aware: Round 1 uses expected attending voters + absentee count; Round 2 and later use attending voters only
- Details tab majority display shows both thresholds when absentees are configured

---

## [1.0.2] — 2026-04-06
### Fixed
- Token card QR code was blank on the first print attempt; `QRCode.js` renders asynchronously via an internal `setTimeout`, so reading the canvas immediately after construction returned an empty element. `getQrDataUrl()` now returns a Promise with a short delay and `printTokenCards()` is async.

---

## [1.0.1] — 2026-04-06
### Added
- Version number displayed in the footer of the admin hub (`index.html`)

---

## [1.0.0] — 2026-04-06
### Initial release
- Multi-round elections for Elder and Deacon offices with automatic majority detection
- Digital voting via unique 4-digit token codes on members' phones/tablets
- Paper ballot entry station with ballot log, edit, and delete last entry
- Absentee-aware majority calculation (added in v1.1.0; baseline majority used expected voters)
- Round Control with real-time vote count updates (3-second poll)
- Round Transition: auto-suggest elected candidates based on majority, configurable advancing candidates
- Skip unconfigured offices automatically in the election flow
- Election Complete screen showing elected names by office (no vote counts)
- Election Dashboard (results password protected) with delete option after election is complete
- Voter page with full state machine: token → ballot → done/waiting → complete
- Paper Ballot Entry with 4-second auto-refresh and structural change detection
- Two password-protected areas: admin and results (SHA-256 hashed, WebCrypto with pure-JS fallback)
- Token cards with QR codes, printable paper ballots
- Local Python server (`server.py`) with `/api/state` and `/api/ballot` endpoints
- Atomic ballot submission under thread lock — supports concurrent voters
- Cloud deployment support via Render.com (`render.yaml`)
- No internet required for local use; no external dependencies beyond Google Fonts and QRCode.js CDN
