# Changelog

All notable changes to the Church Voting App are documented here.

---

## [2.4.1] — 2026-04-13
### Fixed
- Voter page: after the office bearer election completes and the congregational vote opens, the voter no longer has to re-enter their token — the token entered for the election is carried forward automatically
- Voting Control and Voting Dashboard: answer rows now show a green "✓ Majority" badge when the vote count meets or exceeds the configured majority threshold; the progress bar turns green and the threshold is noted below the bar

---

## [2.4.0] — 2026-04-13
### Added
- **Paper Ballot Entry is now password-protected** (default: `paperentry2024`) — the home screen tile now prompts for the paper ballot password before opening the entry station
- **Change Paper Ballot Password** option added to both Election Setup → Settings tab and Voting Setup screen
- **Absentee Voters** field added to Voting Setup — enter the number of absentee votes to include in the majority calculation
- **Majority Threshold** configuration added to Voting Setup — three options: 50%+1 (simple majority), 75% of eligible voters, or a custom percentage. The computed required vote count is shown as a stat in Voting Control and Voting Dashboard

---

## [2.3.0] — 2026-04-13
### Added
- **Paper Ballot Entry** tile added to the home screen — a unified volunteer station that auto-detects whether an office bearer election or a congregational vote is active and shows the appropriate entry form. No password required.
### Changed
- Paper Ballot Entry removed from the Office Bearer Election hub and the Congregational Vote hub — now accessed exclusively from the home screen
- `screen-voting-paper` removed; its content merged into the unified `screen-paper-ballot` screen
- Extracted `updatePBLog()` helper; introduced `renderUnifiedPaperBallot()`, `unifiedPBKey()`, and `startUnifiedPaperBallotPoller()` to coordinate both ballot types

---

## [2.2.2] — 2026-04-13
### Changed
- Voter page: after the office bearer election completes, the thank-you screen now automatically transitions to the congregational vote flow (token entry or waiting screen) when a congregational vote is configured — no manual refresh needed. The election-complete screen polls every 3 s; entering the voting flow resets the token entry so voters authenticate fresh for the vote.

---

## [2.2.1] — 2026-04-13
### Changed
- Voting Page URL setting (custom URL override + QR code) moved from Election Setup → Settings tab into the Voter Tokens screen — it lives alongside token generation and token cards since they all share the same voter URL

---

## [2.2.0] — 2026-04-13
### Changed
- `vote.html` and `motion-vote.html` merged into a single voter page (`vote.html`) — the page auto-detects whether an office bearer election or congregational vote is currently active and presents the appropriate ballot. Voters use one URL for all voting types.
- `motion-vote.html` deleted; `votingVoteUrl()` removed from `index.html` — both the election voter URL and the voting voter URL now point to `vote.html`
### Fixed
- Congregational vote submission was calling `/api/motion-ballot` (which does not exist); corrected to `/api/voting-ballot`

---

## [2.1.2] — 2026-04-13
### Added
- Voter Tokens is now its own password-protected section (accessed via a third home tile using the tokens password), with token generation, stats, token chip grid, Print Token Cards, and a Change Tokens Password form
### Changed
- Purple accent colour removed from all Congregational Vote screens and replaced with navy (`#1a2744` / `#243460`) — affects Voting Control stat numbers, result bars, Voting Dashboard vote counts and bars, ballot card office label, and paper ballot answer selection highlight
- Print Token Cards button (previously its own password prompt) is now simply inside the Voter Tokens screen, which is already behind the tokens password — no double-authentication needed

---

## [2.1.1] — 2026-04-13
### Added
- Print Token Cards button is now password-protected (default: `tokens2024`) — clicking it opens the standard login screen with a new tokens password. A fourth independent password level has been added alongside admin, voting, and results.
### Fixed
- Elder Election and Deacon Election tabs in Election Setup were blank due to a `ReferenceError`: `names` (undefined) was used in the ballot-printing template string instead of `(o.nominees || []).length`. Corrected to use the nominees array from state.

---

## [2.1.0] — 2026-04-13
### Added
- Voter Tokens section moved to main home screen — accessible before choosing a section, with token generation, stats, chip display, and Print Token Cards button
- Tokens are now explicitly shared across both Office Bearer Election and Congregational Vote (description updated on home screen)
- Separate voting password (default: `voting2024`) for Voting Setup and Voting Control, independent of the admin password and the results password
- "Change Voting Password" card added to Voting Setup screen
- Print paper ballots for Elder and Deacon elections moved from the Tokens tab into each office's setup tab (available in both the pre-round setup state and the in-progress state)
- "Print Voting Ballots" button added to Voting Setup screen
- `showHome()` navigation helper that refreshes the token display when returning to the home screen
### Changed
- Default congregational vote answer options changed from "In Favour / Against / Abstain" to **"In favour" / "Not in favour"**
- Voting question placeholder updated to generic wording ("Do you agree with the proposed resolution?")
- Tokens tab removed from Election Setup entirely (moved to home screen)
- Voting Setup and Voting Control now require the voting password instead of the admin password
### Fixed
- `migrateState()` condition was always false (`parsed.voting && !parsed.voting`) — corrected to `parsed.motion && !parsed.voting`
- `updateVPBLog()` referenced an undefined variable `voting` (leftover from the motion→voting rename); corrected to `const voting = state.voting`

---

## [2.0.0] — 2026-04-13
### Added
- Home landing screen with two tiles: **Office Bearer Election** and **Congregational Vote** — replaces the old single-section landing page
- Full **Congregational Vote** feature:
  - Voting Hub with status overview card and navigation to all voting screens
  - Voting Setup — configure question text, answer options (add/remove), and expected voters
  - Voting Control — open/close voting, live vote counts with bar chart, mark complete, reset
  - Voting Dashboard (results-password protected) — chairman read-only results view, auto-refreshes every 3 s
  - Voting Paper Ballot Entry — volunteer station for members who cannot use the digital system; 4 s auto-refresh log
  - Voter page (`motion-vote.html`) — token entry, answer selection, done/waiting/already-voted/complete states with 3 s polling
  - Server endpoint `/api/voting-ballot` — atomic, token-authenticated vote submission under thread lock
- Token system extended: each token now covers both election rounds and congregational votes via a `votingVoted` flag; saving a new vote setup resets all `votingVoted` flags for a fresh vote
### Changed
- App renamed from **Church Office Bearer Election** to **Church Voting App**
- All internal code identifiers renamed from `motion`/`Motion` to `voting`/`Voting` across `index.html`, `motion-vote.html`, and `server.py`
- `migrateState()` added in `load()` for backward compatibility with existing `election_state.json` files that still use the old `motion` key or `motionVoted` token flag
### Infrastructure
- `README.md` fully rewritten for "Church Voting App" covering both feature sets, the motion vote flow diagram, and all four API endpoints

---

## [1.2.5] — 2026-04-08
### Changed
- Election Dashboard: replaced the small "Delete All Election Data" ghost button with a full Danger Zone section (matching the one in Election Setup → Settings tab) — includes a red heading, explanatory text, and a prominent red "Reset All Election Data" button. Only shown after the election is complete.

---

## [1.2.4] — 2026-04-07
### Fixed
- Voter page: when a new round opened, authenticated voters (token already entered) were sent straight to the ballot without any confirmation prompt. The waiting screen now shows the same "Vote Now" notification button used on the done screen — the voter must tap it to proceed to the ballot. `determineView()` reverted to always returning `'token'` when voting is open; the `waitingPoller` intercepts the case where `enteredToken` is set and calls `checkForNextBallot()` to inject the prompt instead.

---

## [1.2.3] — 2026-04-07
### Fixed
- Voter page: when a new round opened after the voter had already authenticated, they were shown the token entry screen instead of the ballot. `determineView()` always returned `'token'` when voting was open, ignoring that `enteredToken` was already set. It now returns `'ballot'` directly when the voter's token is known and they haven't yet voted in the current round. `selectedCandidates` is also cleared when the `waitingPoller` transitions to ballot, preventing stale selections carrying over.

---

## [1.2.2] — 2026-04-07
### Fixed
- Voter page: after submitting a vote, closing the round left the voter stuck on the "Vote Submitted" confirmation screen instead of switching to "Voting Round Closed". `checkForNextBallot()` was returning early when `!office.votingOpen`, doing nothing. It now transitions to the `waiting` state when voting closes (so the voter sees the round-closed screen) and to the `complete` state when the election finishes entirely.

---

## [1.2.1] — 2026-04-07
### Fixed
- Voter page: ballot screen still switched back to token entry because the `waitingPoller` started during the token state was never stopped before `view = 'ballot'` was set. The `if (!waitingPoller)` guard in the ballot branch then prevented the ballot-specific poller from starting, so the old token-state poller fired, called `determineView()`, got `'token'`, and switched the view back. Fixed by explicitly clearing `waitingPoller` before setting `view = 'ballot'` in both `handleTokenSubmit()` and `goToNextBallot()`.

---

## [1.2.0] — 2026-04-07
### Fixed
- Voter page: after entering a token the ballot screen was immediately replaced by the token entry screen. The v1.1.9 fix added 'ballot' to the general waitingPoller which calls `determineView()` — that function correctly returns 'token' (voting open, not yet done), causing the switch back. Fixed by giving the ballot state its own dedicated poller that only watches for `votingOpen` going false, never calling `determineView()`.

---

## [1.1.9] — 2026-04-07
### Fixed
- Voter page: voters on the ballot screen (after entering their token, while selecting candidates) were not automatically redirected to the "Voting Round Closed" screen when the officer closed voting. The `ballot` state is now included in the `waitingPoller` so all active screens update within 3 seconds when voting status changes.

---

## [1.1.8] — 2026-04-07
### Fixed
- Election Setup: "▶ Round Control" button was not appearing after saving an office setup because `saveOfficeSetup()` only called `renderOfficeSetup()`, not the full `renderSetup()` which contains the button visibility logic. Button now shown immediately on save.

---

## [1.1.7] — 2026-04-07
### Added
- Election Setup header: "▶ Round Control" shortcut button appears as soon as at least one office is configured, allowing the officer to switch directly to Round Control without going back to the landing page.
### Fixed
- Voter page: voters who had already submitted a ballot were being shown the "Voting Round Closed" waiting screen when the round closed. The `done` state check in `determineView()` now runs before the `votingOpen` check, so voted voters stay on the confirmation screen regardless of round status.

---

## [1.1.6] — 2026-04-06
### Changed
- Election Dashboard info strip: removed "Total Eligible" pill; updated "Absentee Votes" label to include "(Round 1 only)"
### Added
- Election Dashboard: current round card (active + awaiting transition) now shows ballot counters — Ballots In, Paper, Absentee (Round 1 only), Expected, and Turnout %
- Election Dashboard: each committed round in Round History now shows full counters — total ballots, paper, absentee, turnout %, majority required, and all candidate vote counts

---

## [1.1.5] — 2026-04-06
### Added
- Election Dashboard: new election information strip showing Expected Voters (attending), Absentee Votes, and Total Eligible — displayed between the status section and the results.

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
