#!/usr/bin/env python3
"""Generate the Church Election System manual as a .docx file."""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import docx.enum.text as docx_breaks

# ── Colours ──────────────────────────────────────────────────────────────────
NAVY      = RGBColor(0x1a, 0x27, 0x44)
GOLD      = RGBColor(0xb8, 0x94, 0x2a)
ELDER     = RGBColor(0x7c, 0x3d, 0x12)
DEACON    = RGBColor(0x1a, 0x3a, 0x5c)
GREEN     = RGBColor(0x2d, 0x6a, 0x4f)
RED       = RGBColor(0x9b, 0x23, 0x35)
GREY      = RGBColor(0x66, 0x66, 0x66)
WHITE     = RGBColor(0xff, 0xff, 0xff)

doc = Document()

# ── Page margins ─────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

# ── Style helpers ─────────────────────────────────────────────────────────────
def set_font(run, bold=False, italic=False, size=None, colour=None):
    run.bold   = bold
    run.italic = italic
    if size:   run.font.size = Pt(size)
    if colour: run.font.color.rgb = colour

def para_space(para, before=0, after=6):
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after  = Pt(after)

def shade_cell(cell, hex_colour):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_colour)
    tcPr.append(shd)

def set_cell_border(cell, top=None, bottom=None, left=None, right=None):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side, val in [('top',top),('bottom',bottom),('left',left),('right',right)]:
        if val:
            el = OxmlElement(f'w:{side}')
            el.set(qn('w:val'),   val.get('val','single'))
            el.set(qn('w:sz'),    val.get('sz','4'))
            el.set(qn('w:space'),'0')
            el.set(qn('w:color'), val.get('color','auto'))
            tcBorders.append(el)
    tcPr.append(tcBorders)

# ── Heading helpers ───────────────────────────────────────────────────────────
def h1(doc, text):
    p = doc.add_paragraph()
    para_space(p, before=18, after=6)
    p.paragraph_format.page_break_before = True
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = NAVY
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bot  = OxmlElement('w:bottom')
    bot.set(qn('w:val'),   'single')
    bot.set(qn('w:sz'),    '8')
    bot.set(qn('w:space'), '4')
    bot.set(qn('w:color'), '1a2744')
    pBdr.append(bot)
    pPr.append(pBdr)
    return p

def h2(doc, text):
    p = doc.add_paragraph()
    para_space(p, before=12, after=4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = NAVY
    return p

def h3(doc, text):
    p = doc.add_paragraph()
    para_space(p, before=8, after=3)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = GREY
    return p

def body(doc, text):
    p = doc.add_paragraph()
    para_space(p, before=0, after=5)
    p.add_run(text)
    p.runs[0].font.size = Pt(11)
    return p

def bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    para_space(p, before=0, after=3)
    p.paragraph_format.left_indent = Cm(0.5 + level * 0.5)
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p

def numbered(doc, text, level=0):
    p = doc.add_paragraph(style='List Number')
    para_space(p, before=0, after=3)
    p.paragraph_format.left_indent = Cm(0.5 + level * 0.5)
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p

# ── Callout boxes ─────────────────────────────────────────────────────────────
def callout(doc, label, text, bg_hex, border_hex):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.cell(0, 0)
    shade_cell(cell, bg_hex)
    set_cell_border(cell,
        top    ={'val':'single','sz':'12','color':border_hex},
        bottom ={'val':'single','sz':'4', 'color':border_hex},
        left   ={'val':'single','sz':'12','color':border_hex},
        right  ={'val':'single','sz':'4', 'color':border_hex},
    )
    lp = cell.paragraphs[0]
    para_space(lp, before=2, after=2)
    lr = lp.add_run(f'{label}  ')
    lr.bold = True
    lr.font.size = Pt(10)
    tr = lp.add_run(text)
    tr.font.size = Pt(10)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def note(doc, text):    callout(doc, 'NOTE:',             text, 'E8F0FA', '1A3A5C')
def tip(doc, text):     callout(doc, 'TIP:',              text, 'F0FAF0', '2D6A4F')
def warning(doc, text): callout(doc, 'IMPORTANT:',        text, 'FFF4E0', 'B8942A')
def danger(doc, text):  callout(doc, 'ACTION REQUIRED:',  text, 'FDF0F0', '9B2335')

# ── Screenshot placeholder ────────────────────────────────────────────────────
def screenshot(doc, label, description):
    tbl = doc.add_table(rows=2, cols=1)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    label_cell = tbl.cell(0, 0)
    shade_cell(label_cell, 'B8942A')
    set_cell_border(label_cell,
        top={'val':'single','sz':'4','color':'B8942A'},
        left={'val':'single','sz':'4','color':'B8942A'},
        right={'val':'single','sz':'4','color':'B8942A'},
        bottom={'val':'single','sz':'4','color':'B8942A'},
    )
    lp = label_cell.paragraphs[0]
    para_space(lp, before=2, after=2)
    lr = lp.add_run(f'  SCREENSHOT — {label.upper()}')
    lr.bold = True
    lr.font.size = Pt(9)
    lr.font.color.rgb = WHITE
    desc_cell = tbl.cell(1, 0)
    shade_cell(desc_cell, 'FFFBF0')
    set_cell_border(desc_cell,
        top={'val':'single','sz':'4','color':'B8942A'},
        left={'val':'single','sz':'4','color':'B8942A'},
        right={'val':'single','sz':'4','color':'B8942A'},
        bottom={'val':'single','sz':'4','color':'B8942A'},
    )
    dp = desc_cell.paragraphs[0]
    para_space(dp, before=6, after=16)
    dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = dp.add_run(f'[ Insert screenshot here ]\n{description}')
    dr.font.size = Pt(9)
    dr.font.color.rgb = RGBColor(0x7c, 0x5a, 0x00)
    dr.italic = True
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

# ── Data table helper ─────────────────────────────────────────────────────────
def data_table(doc, headers, rows, col_widths=None):
    n = len(headers)
    tbl = doc.add_table(rows=1+len(rows), cols=n)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    hdr_row = tbl.rows[0]
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        shade_cell(cell, '1A2744')
        p = cell.paragraphs[0]
        para_space(p, before=2, after=2)
        run = p.add_run(h)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = WHITE
    for ri, row_data in enumerate(rows):
        row = tbl.rows[ri + 1]
        bg = 'F8F6F1' if ri % 2 == 1 else 'FFFFFF'
        for ci, cell_text in enumerate(row_data):
            cell = row.cells[ci]
            shade_cell(cell, bg)
            p = cell.paragraphs[0]
            para_space(p, before=2, after=2)
            run = p.add_run(str(cell_text))
            run.font.size = Pt(10)
    if col_widths:
        for row2 in tbl.rows:
            for ci2, cell2 in enumerate(row2.cells):
                cell2.width = Cm(col_widths[ci2])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return tbl


# ════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ════════════════════════════════════════════════════════════════════════
cover = doc.add_paragraph()
cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
para_space(cover, before=80, after=6)
cr = cover.add_run('Church Office Bearer\nElection System')
cr.bold = True
cr.font.size = Pt(28)
cr.font.color.rgb = NAVY

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
para_space(sub, before=6, after=10)
sr = sub.add_run('Complete User Manual')
sr.font.size = Pt(16)
sr.font.color.rgb = GOLD

ver = doc.add_paragraph()
ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
para_space(ver, before=0, after=30)
vr = ver.add_run('Version 1.1.5')
vr.font.size = Pt(11)
vr.font.color.rgb = GREY

for line in [
    'Reformed Church Congregational Election Software',
    'For use at Congregational Membership Meetings',
    '',
    'Confidential — For Election Officers & Chairman Use Only',
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para_space(p, before=0, after=4)
    r = p.add_run(line)
    r.font.size = Pt(11)
    if 'Confidential' in line:
        r.bold = True
        r.font.color.rgb = NAVY
    else:
        r.font.color.rgb = GREY

pb = doc.add_paragraph()
pb.add_run().add_break(WD_BREAK.PAGE)


# ════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ════════════════════════════════════════════════════════════════════════
toc_title = doc.add_paragraph()
toc_title.paragraph_format.page_break_before = False
para_space(toc_title, before=0, after=8)
tr2 = toc_title.add_run('Table of Contents')
tr2.bold = True
tr2.font.size = Pt(16)
tr2.font.color.rgb = NAVY

toc_entries = [
    ('1.',    'System Overview'),
    ('2.',    'Technical Requirements & Setup'),
    ('   2a.', 'Running Locally'),
    ('   2b.', 'Cloud / Internet Hosting'),
    ('3.',    'Passwords & Security'),
    ('4.',    'Before the Meeting — Election Setup'),
    ('   4a.', 'Congregation Details'),
    ('   4b.', 'Elder Election Configuration'),
    ('   4c.', 'Deacon Election Configuration'),
    ('   4d.', 'Tokens — Generating & Printing'),
    ('   4e.', 'Settings — URL, QR Code & Passwords'),
    ('5.',    'During the Meeting — Round Control'),
    ('   5a.', 'Accessing Round Control'),
    ('   5b.', 'Starting Round 1'),
    ('   5c.', 'Opening and Closing Voting'),
    ('   5d.', 'Monitoring Participation'),
    ('   5e.', 'Ending a Round & Round Transition'),
    ('   5f.', 'Confirming Elected Candidates (Step 1)'),
    ('   5g.', 'Selecting Who Advances (Step 2)'),
    ('   5h.', 'Next Round Settings (Step 3)'),
    ('   5i.', 'Completing an Office'),
    ('6.',    'Paper Ballot Entry'),
    ('   6a.', 'Dynamic Behaviour'),
    ('   6b.', 'Entering a Paper Ballot'),
    ('   6c.', 'Editing a Submitted Ballot'),
    ('   6d.', 'Deleting the Last Entry'),
    ('   6e.', 'Absentee Votes'),
    ('7.',    'The Voter Page (vote.html)'),
    ('8.',    'Election Dashboard'),
    ('9.',    'Election Complete Screen'),
    ('10.',   'Best Practices & Suggested Workflow'),
    ('11.',   'Complete Election Walkthrough'),
    ('12.',   'Troubleshooting'),
    ('13.',   'Quick Reference'),
]
for num, title in toc_entries:
    p = doc.add_paragraph()
    para_space(p, before=0, after=3)
    indent = len(num) - len(num.lstrip())
    p.paragraph_format.left_indent = Cm(indent * 0.2)
    r1 = p.add_run(num + '  ')
    r1.font.size = Pt(11)
    r1.bold = not num.startswith('   ')
    r1.font.color.rgb = NAVY if not num.startswith('   ') else GREY
    r2 = p.add_run(title)
    r2.font.size = Pt(11)
    r2.font.color.rgb = NAVY if not num.startswith('   ') else GREY

pb2 = doc.add_paragraph()
pb2.add_run().add_break(WD_BREAK.PAGE)


# ════════════════════════════════════════════════════════════════════════
# 1. SYSTEM OVERVIEW
# ════════════════════════════════════════════════════════════════════════
h1(doc, '1.  System Overview')

body(doc, (
    'The Church Office Bearer Election System is a browser-based voting application '
    'designed for conducting Reformed church congregational elections for the offices of '
    'Elder and Deacon. It runs on a local Python server on the meeting laptop — no internet '
    'connection is required. All election data is stored in a single shared file on the laptop '
    'and is accessible in real time by all devices connected to the same network.'
))

h2(doc, 'How the System Works')
body(doc, 'The system consists of three files and a local Python server:')

data_table(doc,
    ['File', 'Purpose', 'Who Uses It'],
    [
        ['server.py',           'Python server — serves the app and stores all election data', 'Must be running throughout the election'],
        ['index.html',          'Administration hub — all setup and control functions',         'Election Officer, Chairman'],
        ['vote.html',           'Voter ballot page — members cast their votes here',            'All eligible voters'],
        ['election_state.json', 'Shared election data file — created automatically',            '(Not opened directly)'],
    ],
    col_widths=[4.0, 8.0, 4.0]
)

h2(doc, 'Key Features')
for feat in [
    'Supports multi-round elections with automatic majority detection',
    'Either or both offices (Elder, Deacon) can be configured — unconfigured offices are skipped',
    'Digital voting via personal devices (phones/tablets) using unique 4-digit token codes',
    'Paper ballot entry station for members who prefer to vote on paper',
    'Two separate passwords: admin (setup & control) and results (chairman only)',
    'Real-time vote count updates on Round Control — refreshes every 3 seconds',
    'Voter page updates automatically when rounds open, close, or a new office begins',
    'Majority threshold calculated from expected voters (floor(n/2) + 1) — Round 1 includes absentee votes',
    'Absentee vote support — enter absentee count in setup; paper ballot volunteer marks ballots as absentee',
    'Auto-suggestion of elected candidates when majority is reached',
    'No internet required — runs entirely on a local Wi-Fi network',
    'Can also be hosted publicly on the internet (e.g. Render.com) for remote voter access',
]:
    bullet(doc, feat)

screenshot(doc, 'Landing Page',
    'The main landing page of index.html showing four navigation cards: Election Setup, '
    'Round Control, Paper Ballot Entry, and Election Dashboard. The Voter Ballot URL is '
    'displayed at the bottom.')


# ════════════════════════════════════════════════════════════════════════
# 2. TECHNICAL REQUIREMENTS & SETUP
# ════════════════════════════════════════════════════════════════════════
h1(doc, '2.  Technical Requirements & Setup')

h2(doc, 'Administrator Device (Laptop/PC)')
for item in [
    'Python 3.8 or later (pre-installed on most Macs)',
    'Any modern web browser (Chrome, Edge, Firefox, or Safari — 2020 or later)',
    'The files server.py, index.html, and vote.html must be in the same folder',
    'The device must be connected to a local Wi-Fi network so voters can reach vote.html',
]:
    bullet(doc, item)

h2(doc, 'Voter Devices (Phones/Tablets)')
for item in [
    'Any device with a modern web browser',
    'Must be connected to the same local Wi-Fi network as the administrator\'s laptop',
    'No app installation required',
]:
    bullet(doc, item)

h2(doc, '2a.  Running Locally')
body(doc, 'Start the server by opening a Terminal in the election folder and running:')
p = doc.add_paragraph()
para_space(p, before=2, after=6)
p.paragraph_format.left_indent = Cm(1.0)
r = p.add_run('python3 server.py')
r.bold = True
r.font.size = Pt(11)
r.font.color.rgb = NAVY

body(doc, 'The server prints the following on startup:')
for line in [
    'Admin / local:   http://localhost:8080/',
    'Voter devices:   http://192.168.x.x:8080/vote.html',
    'State file:      .../election_state.json',
]:
    p = doc.add_paragraph()
    para_space(p, before=0, after=2)
    p.paragraph_format.left_indent = Cm(1.0)
    p.add_run(line).font.size = Pt(10)

doc.add_paragraph().paragraph_format.space_after = Pt(4)

for step in [
    'Open http://localhost:8080/ in the browser on the laptop to access the admin hub.',
    'Enter the voter URL (shown on startup) in Election Setup → Settings tab.',
    'Voters open http://192.168.x.x:8080/vote.html on their phones.',
]:
    numbered(doc, step)

warning(doc, (
    'The server must remain running for the entire duration of the election. '
    'Do not close the Terminal window while the election is in progress.'
))

h2(doc, '2b.  Cloud / Internet Hosting (Render.com)')
body(doc, (
    'The app can be deployed to a public server so voters access it over the internet '
    'instead of a local Wi-Fi network. This is useful for larger congregations or hybrid meetings.'
))
for step in [
    'Push the project folder to a GitHub repository.',
    'Go to render.com → New → Blueprint. Connect the GitHub repository.',
    'Render reads render.yaml automatically and creates the service.',
    'Your public URL appears in the Render dashboard (e.g. https://church-election.onrender.com).',
    'In Election Setup → Settings, set the voter URL to the public /vote.html address.',
]:
    numbered(doc, step)

note(doc, (
    'A persistent disk (Render Starter plan, approx. $7/month) is recommended to ensure '
    'election_state.json survives service restarts. The free plan is acceptable for a '
    'single election day provided the service does not restart mid-election.'
))


# ════════════════════════════════════════════════════════════════════════
# 3. PASSWORDS & SECURITY
# ════════════════════════════════════════════════════════════════════════
h1(doc, '3.  Passwords & Security')

body(doc, 'The system uses two separate passwords to control access to different areas:')

data_table(doc,
    ['Password', 'Protects', 'Default', 'Who Holds It'],
    [
        ['Admin Password',   'Election Setup and Round Control',         'election2024', 'Election Officer only'],
        ['Results Password', 'Election Dashboard (confidential results)', 'results2024',  'Chairman only'],
    ],
    col_widths=[4.0, 6.0, 3.0, 3.5]
)

danger(doc, (
    'Change both passwords before the election. The defaults are publicly known. '
    'Go to Election Setup → Settings tab to update them.'
))

body(doc, (
    'Passwords are stored as SHA-256 cryptographic hashes — the actual password text is '
    'never stored anywhere in the system. Password entry fields on mobile devices have '
    'autocapitalize and autocorrect disabled to prevent common mobile keyboard issues.'
))

warning(doc, (
    'Keep the two passwords separate and confidential. The chairman does not need the '
    'admin password, and the election officer does not need the results password.'
))


# ════════════════════════════════════════════════════════════════════════
# 4. ELECTION SETUP
# ════════════════════════════════════════════════════════════════════════
h1(doc, '4.  Before the Meeting — Election Setup')

body(doc, (
    'All setup must be completed before the congregational meeting begins. '
    'Open index.html in the browser via the server URL, click Election Setup on the landing '
    'page, and enter the admin password. Election Setup is organised into five tabs: '
    'Details, Elder Election, Deacon Election, Tokens, and Settings.'
))

note(doc, (
    'Only configure the offices that are being voted on. If only Elder is being elected, '
    'leave the Deacon tab empty. Unconfigured offices are automatically skipped during '
    'the election.'
))

screenshot(doc, 'Election Setup — Details Tab',
    'Five tab buttons at the top: Details, Elder Election, Deacon Election, Tokens, Settings. '
    'The Details tab is active showing: Congregation Name, Meeting Date, Expected Voters, '
    'and the Majority Required display below the voter count field.')

# 4a
h2(doc, '4a.  Congregation Details')
body(doc, 'Click the Details tab and fill in the following fields:')

data_table(doc,
    ['Field', 'Description', 'Example'],
    [
        ['Congregation Name', 'Full name of the congregation. Appears on token cards, the voter page header, and the election dashboard.', 'First Reformed Church'],
        ['Meeting Date',      'Date of the congregational meeting. Shown on the voter page header and the election complete screen.',        '2026-04-13'],
        ['Expected Voters (attending)', 'Number of eligible male voters expected to attend the meeting in person. Used for Round 2+ majority and participation %.', '80'],
        ['Absentee Votes (Round 1 only)', 'Number of paper ballots received from eligible members who cannot attend the meeting. These are counted only in Round 1.', '5'],
    ],
    col_widths=[4.5, 8.0, 3.5]
)

body(doc, (
    'Below these fields, the system automatically displays the Majority Required threshold(s). '
    'Majority is defined as floor(n / 2) + 1, where n is the total eligible voter count for that round:'
))
bullet(doc, 'Round 1 majority uses Expected Voters + Absentee Votes (e.g. 80 + 5 = 85 voters → majority = 43)')
bullet(doc, 'Round 2 and later use Expected Voters only (e.g. 80 voters → majority = 41), since absentee votes are only valid for Round 1')
body(doc, (
    'When no absentee count is configured (0), a single majority number is displayed. '
    'When absentees are entered, both thresholds are shown side by side.'
))

tip(doc, (
    'Fields save automatically when you move to the next field. '
    'You can also click Save Details to save manually. '
    'A green "Saved" confirmation appears briefly.'
))

warning(doc, (
    'If absentee votes are being cast, enter the absentee count before the meeting begins. '
    'The majority threshold for Round 1 adjusts automatically as soon as the value is saved. '
    'The absentee ballots themselves are entered via Paper Ballot Entry with the Absentee checkbox.'
))

# 4b
h2(doc, '4b.  Elder Election Configuration')
body(doc, 'Click the Elder Election tab and enter the following:')

data_table(doc,
    ['Field', 'Description', 'Example'],
    [
        ['Nominees',                  'One name per line. All men nominated for the office of Elder.',                                   'John Smith\nPeter Johnson\nMichael Williams\nDavid Brown'],
        ['Positions to Fill',         'How many Elders need to be elected in this election.',                                            '2'],
        ['Votes per Voter (Round 1)', 'How many candidates each voter may select in Round 1. Typically equal to positions to fill.',      '2'],
    ],
    col_widths=[4.5, 8.0, 3.5]
)

body(doc, 'Click Save Elder Setup when done. A green confirmation message appears.')

warning(doc, (
    'Saving the setup resets all in-progress election data for that office. '
    'Do not save setup during an active election round unless you intend to start over.'
))

# 4c
h2(doc, '4c.  Deacon Election Configuration')
body(doc, (
    'Click the Deacon Election tab and repeat the same process — enter nominees, '
    'positions to fill, and votes per voter for Round 1. Click Save Deacon Setup.'
))
body(doc, (
    'If no Deacon election is being held this meeting, leave this tab empty. '
    'The system will skip the Deacon office entirely.'
))

# 4d
h2(doc, '4d.  Tokens — Generating & Printing')

h3(doc, 'Generating Tokens')
body(doc, (
    'Tokens are unique 4-digit codes that identify each eligible voter. Each member '
    'receives one token card which covers both the Elder and Deacon elections and all rounds. '
    'A token can only be used once per round per office.'
))
for step in [
    'Enter the number of tokens (equal to the number of eligible voters, e.g. 85).',
    'Click Generate Tokens. The system creates unique 4-digit codes.',
    'The token grid displays all generated codes with usage tracking.',
]:
    numbered(doc, step)

warning(doc, (
    'Generating new tokens replaces all existing ones. Do this only once before the '
    'meeting. Regenerating tokens during an election will invalidate all previously '
    'distributed cards.'
))

h3(doc, 'Printing Token Cards')
body(doc, (
    'Click Print Token Cards. Each card shows the congregation name, the 4-digit code, '
    'a QR code linking to the voter page, and the voter URL. Print on card stock and '
    'distribute one card per eligible voter at the door.'
))

screenshot(doc, 'Token Cards Print Preview',
    '4-column grid of token cards. Each card shows: congregation name at the top, '
    'large 4-digit code, QR code image, and the voter URL at the bottom.')

warning(doc, (
    'Configure the voter URL in the Settings tab BEFORE printing token cards. '
    'The QR code and URL on the cards are generated from the URL saved in Settings.'
))

h3(doc, 'Printing Paper Ballots')
body(doc, (
    'Paper ballots are for members who cannot use a phone or tablet. Set the quantity '
    'for each office and click the corresponding Print button.'
))
bullet(doc, 'Set the number of Elder ballots (e.g. 15) and click Print Elder Ballots.')
bullet(doc, 'Set the number of Deacon ballots (e.g. 15) and click Print Deacon Ballots.')
bullet(doc, 'Each ballot card shows: office name, congregation name, positions to fill, and all nominees with a checkbox next to each name.')

note(doc, (
    'Paper ballots intentionally do not show round information so that the same '
    'printed ballots can be reused across multiple rounds. The chairman verbally '
    'announces which candidates are on the ballot for each round.'
))

# 4e
h2(doc, '4e.  Settings — URL, QR Code & Passwords')

h3(doc, 'Voting Page URL')
body(doc, (
    'Enter the full URL that voters will use to access the ballot page. '
    'For local network: http://192.168.x.x:8080/vote.html. '
    'For internet hosting: https://your-app.onrender.com/vote.html. '
    'Click Save URL. The QR code updates automatically.'
))

h3(doc, 'QR Code')
body(doc, (
    'A QR code is generated from the saved voter URL. Members scan this with their phone '
    'camera to open the voter page without typing the URL. Click Print QR Code to print '
    'a full-page QR code suitable for display on a screen or at the entrance.'
))

h3(doc, 'Change Admin Password')
body(doc, 'Enter your current password, a new password (minimum 4 characters), and confirm. Click Update Admin Password.')

h3(doc, 'Change Results Password')
body(doc, 'Enter the current results password, a new password, and confirm. Click Update Results Password. Share this password only with the chairman.')

h3(doc, 'Reset All Election Data')
body(doc, (
    'The Reset All Election Data button (red, in the Danger Zone section) permanently '
    'erases all nominees, ballots, tokens, results, and resets passwords to defaults. '
    'Two confirmation prompts prevent accidental use.'
))

danger(doc, (
    'Reset All Election Data cannot be undone. All election configuration and results '
    'will be lost. Only use this to start fresh before a new election.'
))

screenshot(doc, 'Settings Tab',
    'Voting Page URL section with current URL display, custom URL input, Save and Clear buttons. '
    'QR Code section showing generated QR code. Change Admin Password card. '
    'Change Results Password card. Danger Zone with red Reset button.')


# ════════════════════════════════════════════════════════════════════════
# 5. ROUND CONTROL
# ════════════════════════════════════════════════════════════════════════
h1(doc, '5.  During the Meeting — Round Control')

body(doc, (
    'Round Control is the central control panel used during the congregational meeting. '
    'It allows the election officer to open and close voting, monitor participation in real '
    'time, end rounds, and transition between rounds and offices.'
))

h2(doc, '5a.  Accessing Round Control')
for step in [
    'From the landing page, click Round Control.',
    'Enter the admin password and click Enter Round Control.',
]:
    numbered(doc, step)

note(doc, (
    'Round Control remains accessible from the landing page at any time during the election. '
    'The election officer does not need to re-enter the password each time if they stay '
    'on the admin hub.'
))

h2(doc, '5b.  Starting Round 1')
body(doc, (
    'When Round Control is opened after completing setup, the system detects the configured '
    'office and displays a "Ready to Start" panel showing the number of nominees, positions '
    'to fill, and votes per voter for Round 1.'
))
body(doc, 'Click Start Round 1 Voting to begin. This immediately opens voting for all eligible voters.')

screenshot(doc, 'Round Control — Ready to Start',
    'Coloured header (warm brown for Elder, deep blue for Deacon). Summary panel showing '
    '"Elder Election — Configured" with nominees count, positions, and votes per voter. '
    'Large "Start Round 1 Voting" button.')

tip(doc, (
    'Do not click Start Round 1 until the chairman has introduced the candidates and '
    'instructed members to begin voting. Once clicked, voters can immediately submit ballots.'
))

h2(doc, '5c.  Opening and Closing Voting')
body(doc, 'Once a round is active, the control bar shows three buttons:')

data_table(doc,
    ['Button', 'Action', 'When to Use'],
    [
        ['Open Voting',  'Opens voting so members can submit ballots',          'At the start of each voting period within a round'],
        ['Close Voting', 'Prevents new ballots from being submitted',           'When sufficient time has passed or all votes are in'],
        ['End Round',    'Finalises the round and opens the Round Transition',  'Only after voting is closed'],
    ],
    col_widths=[3.5, 7.0, 5.5]
)

warning(doc, 'You cannot end a round while voting is open. Close voting first, then click End Round.')

body(doc, (
    'The voting status indicator (green dot = open, grey dot = closed) is visible at all '
    'times. When voting is closed, voters\' screens automatically update within 3 seconds '
    'to show "Voting Round Closed — please wait for further instructions."'
))

screenshot(doc, 'Round Control — Active Round (Voting Open)',
    'Coloured header with office name and round number. Sequence bar showing election '
    'progress. Four stat boxes: Ballots In, Paper Ballots, Expected Voters, Participation %. '
    'Control bar with Open/Close/End buttons and green voting status indicator. '
    'Live Results list below showing candidates ranked by vote count.')

h2(doc, '5d.  Monitoring Participation')
body(doc, 'The four statistics boxes update every 3 seconds automatically:')

data_table(doc,
    ['Statistic', 'Meaning'],
    [
        ['Ballots In',      'Total ballots received this round (digital + paper combined)'],
        ['Paper Ballots',   'Number of ballots entered via the Paper Ballot Entry station this round'],
        ['Absentee',        'Number of paper ballots flagged as absentee this round (Round 1 only — stat box hidden in Round 2+)'],
        ['Expected Voters', 'Total eligible voters for this round: attending + absentee in Round 1; attending only in Round 2+'],
        ['Participation %', 'Ballots In ÷ Expected Voters × 100. Shown in green when ≥ 50%.'],
    ],
    col_widths=[4.5, 11.5]
)

body(doc, (
    'The Live Results section shows all candidates ranked by vote count with a proportional '
    'bar chart. This is for the election officer\'s operational use only — vote counts are '
    'not publicly displayed to voters or congregation.'
))

note(doc, (
    'Confidential results (with vote counts) are only available on the Election Dashboard, '
    'which requires the separate results password.'
))

h2(doc, '5e.  Ending a Round & Round Transition')
body(doc, (
    'Once voting is closed, click End Round. The Round Transition screen opens. '
    'This screen is used to process the results and either launch the next round or '
    'complete the office.'
))
body(doc, 'The screen consists of:')
bullet(doc, 'Final Results — candidates ranked by votes received this round')
bullet(doc, 'Step 1 — Mark as Elected')
bullet(doc, 'Step 2 — Select Who Advances (hidden when all positions are filled)')
bullet(doc, 'Step 3 — Next Round Settings (hidden when all positions are filled)')
bullet(doc, 'Launch Next Round button and Complete This Office button')

screenshot(doc, 'Round Transition Screen',
    'Candidates ranked in Final Results list. Step 1 checkboxes with majority badges. '
    'Step 2 advancing candidates checkboxes. Step 3 votes per voter input with auto-fill hint. '
    'Green "Launch Next Round" and navy "Complete This Office" buttons at the bottom.')

h2(doc, '5f.  Confirming Elected Candidates (Step 1)')
body(doc, (
    'The system automatically detects candidates who received a majority of votes. '
    'The majority threshold is round-aware:'
))
bullet(doc, 'Round 1: floor((Expected Voters + Absentee Votes) / 2) + 1')
bullet(doc, 'Round 2 and later: floor(Expected Voters / 2) + 1')
body(doc, 'Candidates meeting the threshold are pre-checked with a gold "majority" badge.')

data_table(doc,
    ['Action', 'Effect'],
    [
        ['Leave a candidate checked',   'Candidate is confirmed as elected and removed from the next round ballot'],
        ['Uncheck a suggested candidate', 'Override the auto-suggestion — candidate is NOT elected and is restored to the advancing list for the next round'],
        ['Check an unchecked candidate',  'Manually elect a candidate who did not reach the majority threshold'],
    ],
    col_widths=[5.0, 11.0]
)

note(doc, (
    'If the officer unchecks a majority-suggested candidate, Steps 2 and 3 become '
    'visible immediately and the Launch Next Round button activates. This allows a '
    'further round to be conducted even when all positions were initially filled by majority.'
))

h2(doc, '5g.  Selecting Who Advances (Step 2)')
body(doc, (
    'Step 2 shows all non-elected candidates. All are checked (advancing) by default. '
    'Uncheck a candidate to remove them from the next round ballot. This is typically '
    'used to eliminate the lowest-ranked candidate in a tie-breaking situation.'
))
body(doc, (
    'Step 2 is automatically hidden when all positions are already filled in Step 1, '
    'since no next round is needed.'
))

h2(doc, '5h.  Next Round Settings (Step 3)')
body(doc, (
    'Set the number of votes per voter for the next round. The system auto-fills this '
    'as the number of remaining unfilled positions. Adjust manually if needed.'
))
body(doc, (
    'Step 3 is automatically hidden when all positions are filled in Step 1.'
))

h2(doc, '5i.  Completing an Office')
body(doc, (
    'When all positions for an office are filled (either in Step 1 or because a '
    '"All X positions filled" banner appears), click Complete This Office.'
))
body(doc, 'The system will:')
for step in [
    'Record the final elected candidates for this office.',
    'Mark the office as complete.',
    'If the other office is configured and not yet started, show Round Control in "Ready to Start" mode for that office.',
    'If the other office is not configured (no nominees), skip it and go directly to the Election Complete screen.',
    'If both offices are complete, show the Election Complete screen.',
]:
    numbered(doc, step)

screenshot(doc, 'Round Transition — All Positions Filled',
    'Step 1 checkboxes with all positions ticked. Green banner: "All X positions filled. '
    'No further rounds needed." Steps 2 and 3 are hidden. Only the Complete This Office '
    'button is active; Launch Next Round is greyed out.')


# ════════════════════════════════════════════════════════════════════════
# 6. PAPER BALLOT ENTRY
# ════════════════════════════════════════════════════════════════════════
h1(doc, '6.  Paper Ballot Entry')

body(doc, (
    'The Paper Ballot Entry screen is used by a dedicated volunteer to enter votes on '
    'behalf of members who voted on paper. It is accessible from the landing page without '
    'a password and updates dynamically as the election progresses.'
))

warning(doc, (
    'Open Paper Ballot Entry on a separate device or in a separate browser tab on the '
    'admin laptop. This screen is intended for a dedicated volunteer, not the election officer.'
))

h2(doc, '6a.  Dynamic Behaviour')
body(doc, 'The Paper Ballot Entry screen updates automatically every 4 seconds:')

data_table(doc,
    ['Condition', 'What the Screen Shows'],
    [
        ['No election configured',    'Warning: "No voting is currently open"'],
        ['Election configured but voting closed', '"Voting is currently closed" warning with office and round info'],
        ['Voting open',               'Full ballot entry form with candidate list and Submit button'],
        ['Round changes',             'Form resets automatically for the new round and office'],
    ],
    col_widths=[5.5, 10.5]
)

h2(doc, '6b.  Entering a Paper Ballot')
for step in [
    'Wait for the form to appear (voting must be open). The current office and round are shown.',
    'Click each candidate\'s name that was marked on the paper ballot. Selected candidates are highlighted.',
    'Confirm the selections match the paper ballot.',
    '(Round 1 only) If the ballot is from an absentee voter, tick the "This is an absentee vote" checkbox before submitting.',
    'Click Submit Paper Ballot. The vote is recorded immediately and the form resets.',
    'The submitted ballot appears in the log at the bottom of the screen.',
]:
    numbered(doc, step)

screenshot(doc, 'Paper Ballot Entry — Voting Open',
    'Office badge at top showing current office and round. Selectable candidate rows '
    'with highlighted selected candidates. Submit Paper Ballot button in green. '
    'Delete Last Entry button in red below. Log of submitted ballots at the bottom.')

h2(doc, '6c.  Editing a Submitted Ballot')
body(doc, 'Any paper ballot from the current round can be corrected:')
for step in [
    'Find the ballot in the log at the bottom of the screen.',
    'Click the Edit (✏️) button next to it.',
    'An orange "Editing Ballot #X" banner appears and the form repopulates with previous selections.',
    'Make the corrections, then click Update Paper Ballot.',
]:
    numbered(doc, step)

h2(doc, '6d.  Deleting the Last Entry')
body(doc, (
    'A red "Delete Last Entry" button appears at the bottom of the form when at least '
    'one ballot has been submitted in the current round. Clicking it prompts for confirmation, '
    'then removes the most recent paper ballot and reverses its vote counts.'
))

note(doc, 'Only the most recently submitted paper ballot can be deleted this way. To correct an earlier ballot, use the Edit button in the log.')

h2(doc, '6e.  Absentee Votes')
body(doc, (
    'Absentee votes are paper ballots received before the meeting from eligible members '
    'who cannot attend. They are counted only in Round 1 of each office.'
))

data_table(doc,
    ['Step', 'Action'],
    [
        ['Before the meeting', 'Enter the total number of absentee ballots received in Election Setup → Details → "Absentee Votes (Round 1 only)". This adjusts the Round 1 majority threshold automatically.'],
        ['During Round 1 voting', 'Enter each absentee ballot via Paper Ballot Entry. Tick the "This is an absentee vote" checkbox before clicking Submit.'],
        ['In the ballot log', 'Each absentee ballot is tagged with a navy "Absentee" badge. A count summary ("Absentee ballots included: X") appears above the log.'],
        ['Round 2 and later', 'The absentee checkbox is hidden. Absentee votes are not valid and must not be entered in Round 2 or later.'],
    ],
    col_widths=[4.0, 12.0]
)

warning(doc, (
    'Enter absentee ballots during the Round 1 voting period — the same as any other paper ballot. '
    'Do not enter absentee ballots in Round 2 or later rounds. The checkbox is hidden in those rounds '
    'as a safeguard, but the round should still be monitored carefully.'
))

note(doc, (
    'The number entered in "Absentee Votes" in Election Setup is only used to adjust the '
    'majority threshold. The system does not automatically add those votes — each absentee '
    'ballot must still be entered individually via Paper Ballot Entry with the absentee checkbox.'
))


# ════════════════════════════════════════════════════════════════════════
# 7. THE VOTER PAGE
# ════════════════════════════════════════════════════════════════════════
h1(doc, '7.  The Voter Page (vote.html)')

body(doc, (
    'The voter page is what voting members see on their phones or tablets. '
    'It updates automatically every 3 seconds to reflect the current election state — '
    'no manual refreshing is required.'
))

h2(doc, '7a.  Accessing the Voter Page')
bullet(doc, 'QR Code: Scan the QR code on the token card with a phone camera.')
bullet(doc, 'URL: Type the voter URL printed on the token card into the phone\'s browser.')
bullet(doc, 'The page header shows the congregation name, meeting date, and voting status pill (green = open, grey = closed).')

h2(doc, '7b.  Entering a Token')
for step in [
    'The voter opens the voter page — a numeric token input appears.',
    'Type the 4-digit code from the token card.',
    'Tap Submit Token.',
    'If the token is invalid or has already been used this round, a clear error message is shown.',
]:
    numbered(doc, step)

screenshot(doc, 'Voter Page — Token Entry',
    'White card on navy background. Header with church name, meeting date, and "Voting Open" '
    'green pill. "Enter Your Voting Token" heading. Large 4-digit numeric input (telephone '
    'keypad on mobile). Submit Token button.')

h2(doc, '7c.  Casting a Vote')
for step in [
    'The ballot shows the office name, round number, and candidate list.',
    'Tap each candidate to select. A checkmark and coloured highlight confirm selection.',
    'The pip indicators at the top show how many selections have been made versus permitted.',
    'The voter may select up to the permitted number but is not required to use all selections.',
    'Tap Submit My Vote. A confirmation screen appears immediately.',
]:
    numbered(doc, step)

screenshot(doc, 'Voter Ballot Screen',
    '"Office of Elder — Round 1" badge. "Select up to 2 candidates" instruction. '
    'Pip indicators showing 1 of 2 selected. Candidate rows with checkmarks on selected ones. '
    'Submit My Vote button. "Your vote is anonymous" note below.')

warning(doc, (
    'Votes are final once submitted. There is no way for a voter to change their '
    'digital vote after submission. Only paper ballots can be edited via the Paper '
    'Ballot Entry screen.'
))

h2(doc, '7d.  After Voting — Confirmation Screen')
body(doc, (
    'After submitting, the voter sees a "Vote Submitted!" confirmation with a collapsible '
    '"Who you voted for" summary. The page continues to poll every 5 seconds.'
))
bullet(doc, 'If a new round opens for the same office, a notification appears with a "Vote Now →" button.')
bullet(doc, 'If voting moves to a different office, the notification prompts the voter to continue.')
bullet(doc, 'The voter uses the same token card for all rounds and both offices.')

screenshot(doc, 'Vote Submitted — with Next Round Notification',
    '"Vote Submitted!" with green checkmark. Collapsible summary of voted names. '
    'Below: coloured notification card "Round 2 voting is now open — Vote Now →" button.')

h2(doc, '7e.  All Voter Screen States')

data_table(doc,
    ['State', 'When It Appears', 'What the Voter Sees'],
    [
        ['Token Entry',         'Voting is open and member has not yet voted this round',         '4-digit token input and Submit Token button'],
        ['Ballot',              'After a valid token is entered',                                 'Candidate list with selection and Submit My Vote button'],
        ['Vote Submitted',      'After submitting a ballot',                                      'Confirmation with vote summary. Auto-notification when next round/office opens.'],
        ['Voting Round Closed', 'Round controller closes voting while voter is on token screen',  '"Voting Round Closed — please wait for further instructions." Auto-updates within 3 seconds.'],
        ['Voting Not Yet Open', 'Election configured but round not yet started',                  '"Voting has not yet opened." Advances automatically when voting opens.'],
        ['Election Complete',   'All configured offices are done',                                'Plain thank-you message: "Thank you for participating... The chairman will announce the results."'],
        ['No Election Configured', 'No nominees saved or server not responding',                  '"No Election Configured — please check with the chairman."'],
    ],
    col_widths=[4.0, 5.0, 7.0]
)

note(doc, (
    'Token Reuse: One token card covers all rounds and both offices. A member does not '
    'receive a new card for each round. The same code is entered each time.'
))


# ════════════════════════════════════════════════════════════════════════
# 8. ELECTION DASHBOARD
# ════════════════════════════════════════════════════════════════════════
h1(doc, '8.  Election Dashboard')

body(doc, (
    'The Election Dashboard is a password-protected view for the chairman of the meeting. '
    'It shows live election status and confidential results including vote counts. '
    'It refreshes automatically every 3 seconds.'
))

for step in [
    'From the landing page, click Election Dashboard.',
    'Enter the results password (not the admin password) and click View Results.',
]:
    numbered(doc, step)

screenshot(doc, 'Election Dashboard',
    'Navy header with "Election Dashboard" title, congregation name, and meeting date. '
    'Status section showing current office, round, voting status pill, majority required, '
    'votes per voter, and candidate name chips. Election information strip with Expected '
    'Voters, Absentee Votes, and Total Eligible. Results section below for each office '
    'with vote bars, vote counts, and Elected/Not Elected badges.')

h2(doc, 'Election Information')
body(doc, (
    'Below the status section, three stat pills display the voter numbers configured '
    'in Election Setup. These remain visible throughout the entire election:'
))

data_table(doc,
    ['Statistic', 'Description'],
    [
        ['Expected Voters (attending)', 'The number of eligible voters expected to attend the meeting in person, as entered in Election Setup → Details.'],
        ['Absentee Votes',              'The number of absentee ballots received before the meeting, as entered in Election Setup → Details. Counted in Round 1 only.'],
        ['Total Eligible',              'Expected Voters + Absentee Votes. Represents the full electorate for Round 1.'],
    ],
    col_widths=[5.0, 11.0]
)

h2(doc, 'Status Section')
body(doc, 'The status section shows the live state of the active office:')

data_table(doc,
    ['Information', 'Description'],
    [
        ['Office & Round',        'Which office is being voted on and the current round number'],
        ['Status Pill',           'Voting Open (green) / Voting Closed (orange) / Configuring (blue)'],
        ['Majority Required',     'Pill showing the minimum votes needed for election in the current round. Round 1 uses attending + absentee voters; Round 2+ uses attending voters only.'],
        ['Votes per Voter',       'How many candidates each voter may select in the current round'],
        ['Candidates This Round', 'Names of all candidates on the current ballot shown as chips'],
    ],
    col_widths=[4.5, 11.5]
)

h2(doc, 'Results Section')
body(doc, (
    'For each configured office the results section shows all candidates. '
    'The content adapts to the current state of the election:'
))

h3(doc, 'Before Round 1 starts')
body(doc, (
    'When an office is configured but the election officer has not yet started Round 1, '
    'the dashboard shows a pre-round information panel for that office containing:'
))
for item in [
    'A "Round 1 — Not Yet Started" label with a blue "⚙ Configuring" tag and the Round 1 majority required',
    'All nominees listed as chips',
    'Positions to fill and votes per voter for Round 1',
]:
    bullet(doc, item)

h3(doc, 'During an active round (voting open or closed)')
for item in [
    'All candidates listed with vote counts and proportional bars',
    '"✓ Elected · Rd X" badge on previously elected candidates',
    '"Not elected" label on candidates who did not receive enough votes in a completed round',
]:
    bullet(doc, item)

h3(doc, 'Immediately after ending a round (awaiting transition)')
body(doc, (
    'As soon as the election officer clicks End Round, a green "Round N Results — Awaiting transition" '
    'card appears at the top of the office section before the election officer has processed the '
    'Round Transition screen. This card shows:'
))
for item in [
    'All candidates ranked by votes received in that round, with full vote counts and proportional bars',
    'Total ballot count and majority required for that round',
    'A gold "★ majority" badge on any candidate who reached the majority threshold',
    'An orange "Awaiting transition" label indicating the election officer has not yet processed the round',
]:
    bullet(doc, item)

body(doc, (
    'Once the election officer launches the next round or completes the office via the '
    'Round Transition screen, this card disappears and results move into the standard '
    'historical view below, labelled "Previous Rounds".'
))

tip(doc, (
    'The chairman should monitor the dashboard during the round transition. '
    'The "Awaiting transition" card gives the chairman a full view of results '
    'to prepare their announcement before the election officer moves to the next round.'
))

h2(doc, 'Delete All Election Data')
body(doc, (
    'When both offices are complete, a red "Delete All Election Data" button appears '
    'at the bottom of the dashboard. This clears all election data and resets the system '
    'for the next election. Two confirmation prompts prevent accidental deletion.'
))

warning(doc, (
    'The Dashboard shows actual vote counts. Only the chairman should have the results '
    'password. Do not leave the dashboard visible on an unattended or shared screen.'
))


# ════════════════════════════════════════════════════════════════════════
# 9. ELECTION COMPLETE SCREEN
# ════════════════════════════════════════════════════════════════════════
h1(doc, '9.  Election Complete Screen')

body(doc, (
    'After the election officer clicks "Complete This Office" for the last configured office, '
    'the system shows the Election Complete screen. This screen is intended for the election '
    'officer and shows which candidates were elected — without vote counts.'
))

body(doc, 'The screen displays:')
bullet(doc, 'A navy header: "Election Complete" with the meeting date')
bullet(doc, 'A card for each configured office listing the elected candidates by name only')
bullet(doc, 'A "Back to Home" button to return to the landing page')

note(doc, (
    'Vote counts are intentionally not shown on this screen. The election officer may '
    'communicate elected names to the chairman verbally. The chairman then announces '
    'results to the congregation and may view vote counts on the Election Dashboard.'
))

screenshot(doc, 'Election Complete Screen',
    'Navy header "Election Complete" with meeting date. "Office of Elder" card listing '
    'elected names with coloured dot indicators. "Office of Deacon" card below. '
    '"Back to Home" button at the bottom.')

body(doc, (
    'Simultaneously, all voters\' screens automatically update to show a plain thank-you '
    'message: "Thank you for participating in the [Church Name] office bearer election. '
    'The election has been completed. The chairman will announce the results."'
))


# ════════════════════════════════════════════════════════════════════════
# 10. BEST PRACTICES & SUGGESTED WORKFLOW
# ════════════════════════════════════════════════════════════════════════
h1(doc, '10.  Best Practices & Suggested Workflow')

h2(doc, 'Roles & Responsibilities')

data_table(doc,
    ['Role', 'Responsibilities During Election'],
    [
        ['Election Officer',   'Operates Round Control; opens/closes voting; processes round transitions; does not share admin password'],
        ['Chairman',           'Announces candidates and voting instructions; accesses Election Dashboard; announces results verbally'],
        ['Paper Ballot Volunteer', 'Operates Paper Ballot Entry station; collects paper ballots from members; enters them during the voting period'],
        ['Door Steward',       'Distributes token cards to verified eligible voters as they enter'],
    ],
    col_widths=[4.5, 11.5]
)

h2(doc, 'Preparation — At Least 1 Week Before the Meeting')
for item in [
    'Confirm the list of nominees for each office with the consistory.',
    'Confirm the number of eligible voters (communicant male members).',
    'Test the system end-to-end using a laptop and two phones.',
    'Change both passwords from the defaults in Election Setup → Settings.',
    'Record both passwords securely — there is no password recovery option.',
    'Print token cards and cut them. Store securely.',
    'Print paper ballots for each office (recommend 15–20% of expected voter count).',
]:
    bullet(doc, item)

h2(doc, 'Day Before the Meeting')
for item in [
    'Confirm all nominees are entered correctly in Election Setup.',
    'Confirm Expected Voters count and note the Majority Required number.',
    'Test the voter URL on a mobile phone over the network that will be used at the meeting.',
    'Confirm the QR code scans correctly and opens vote.html.',
    'Brief the paper ballot volunteer on their role.',
    'Brief the chairman on the results password and how to access the Election Dashboard.',
]:
    bullet(doc, item)

h2(doc, 'On the Day — Before the Meeting Starts')
for item in [
    'Start the Python server: open Terminal and run python3 server.py',
    'Open http://localhost:8080/ in the admin browser and verify the election configuration.',
    'Set up the paper ballot station with the volunteer and a device or laptop.',
    'Distribute token cards at the door — one per eligible voter.',
    'Have paper ballots available at the paper ballot station.',
    'Verify that voter phones can reach the voter page on the network.',
]:
    numbered(doc, item)

h2(doc, 'During the Meeting — Suggested Order of Events')
for item in [
    'Chairman introduces the nominees for the first office.',
    'Election officer opens Round Control → confirms nominees are correct.',
    'Chairman instructs the congregation: "Please open the voter URL on your phone and enter your token code when prompted."',
    'Election officer clicks Start Round 1 Voting.',
    'Chairman announces: "Voting is now open. Please make your selection and submit your vote."',
    'Paper ballot volunteer enters paper ballots during the voting period.',
    'Election officer monitors Ballots In and Participation % — waits for a satisfactory return.',
    'Election officer clicks Close Voting, then End Round.',
    'Election officer processes the Round Transition screen (Step 1: confirm elected; Step 2: select advancing candidates if needed; Step 3: set votes per voter).',
    'If all positions are filled: click Complete This Office. If not: click Launch Next Round — Round Control opens with voting closed so the chairman can announce the new round first.',
    'Chairman announces which candidates are elected (verbally — does not show dashboard to congregation).',
    'Repeat for next office if configured.',
    'Chairman accesses Election Dashboard with results password to review final vote counts.',
    'Election officer clicks Back to Home or waits. Voters see the thank-you message automatically.',
]:
    numbered(doc, item)

h2(doc, 'After the Meeting')
for item in [
    'The chairman may take a screenshot of the Election Dashboard for the consistory minutes.',
    'When results have been recorded, use the Delete All Election Data button on the dashboard to clear the data.',
    'Stop the Python server (Ctrl+C in the Terminal window).',
    'Store token cards securely or shred them.',
]:
    bullet(doc, item)

h2(doc, 'Best Practice Tips')

tip(doc, (
    'Always run a test election before the actual meeting. Use three people and '
    'verify the full flow: token entry → vote → round transition → complete.'
))

tip(doc, (
    'Set Expected Voters to the actual number of eligible voters, not the total '
    'attendance. This ensures the majority threshold and participation percentage '
    'are calculated correctly.'
))

warning(doc, (
    'Never click Save Elder Setup or Save Deacon Setup during an active election round. '
    'This will reset all ballots and round data for that office.'
))

tip(doc, (
    'If a voter\'s token card is lost, do not generate a new set of tokens — this '
    'invalidates all existing cards. Instead, ask the chairman to note the situation '
    'and handle it procedurally.'
))

tip(doc, (
    'The Paper Ballot Entry screen can be opened on a separate tablet at a dedicated '
    'station. The volunteer does not need the admin password to access this screen.'
))

warning(doc, (
    'Do not run Election Setup and Round Control in the same browser tab as Paper Ballot '
    'Entry. Each function is best operated separately to avoid accidentally navigating away.'
))


# ════════════════════════════════════════════════════════════════════════
# 11. COMPLETE ELECTION WALKTHROUGH
# ════════════════════════════════════════════════════════════════════════
h1(doc, '11.  Complete Election Walkthrough')

body(doc, (
    'This section walks through a realistic election: electing 2 Elders and 1 Deacon '
    'from a congregation with 80 eligible attending voters and 5 absentee ballots received. '
    'Round 1 majority = floor((80+5)/2) + 1 = 43. Round 2+ majority = floor(80/2) + 1 = 41.'
))

h2(doc, 'Example Configuration')
data_table(doc,
    ['Setting', 'Elder', 'Deacon'],
    [
        ['Nominees',                   'John Smith, Peter Johnson, Michael Williams, David Brown', 'Andrew Taylor, James Wilson, Robert Davis'],
        ['Positions',                  '2',  '1'],
        ['Votes per Voter',            '2',  '1'],
        ['Expected Voters (attending)','80', '80'],
        ['Absentee Votes',             '5',  '5'],
        ['Round 1 Majority Required',  '43', '43'],
        ['Round 2+ Majority Required', '41', '41'],
    ],
    col_widths=[4.5, 7.5, 4.0]
)

h2(doc, 'Phase 1 — Setup (Day Before)')
for step in [
    'Run python3 server.py. Open http://localhost:8080/ in Chrome.',
    'Election Setup → Settings → enter voter URL → Save URL.',
    'Change both passwords. Record them securely.',
    'Details tab: enter congregation name, meeting date, Expected Voters = 80, Absentee Votes = 5. Save.',
    'Elder tab: enter four names, Positions = 2, Votes per Voter = 2. Save.',
    'Deacon tab: enter three names, Positions = 1, Votes per Voter = 1. Save.',
    'Tokens tab: enter 80 → Generate Tokens → Print Token Cards. Cut into 80 cards.',
    'Print 15 Elder ballots and 15 Deacon ballots.',
    'Test voter URL on a phone. Confirm token entry screen appears.',
]:
    numbered(doc, step)

h2(doc, 'Phase 2 — Elder Election, Round 1')
for step in [
    'Chairman introduces Elder nominees.',
    'Election officer: Round Control → Start Round 1 Voting.',
    'Voters enter tokens and select up to 2 candidates.',
    'Paper ballot volunteer enters the 5 absentee ballots first (each with the Absentee checkbox ticked), then any remaining paper ballots.',
    'Election officer monitors Participation %. When satisfied: Close Voting → End Round.',
]:
    numbered(doc, step)

body(doc, 'Example results (75 ballots cast incl. 5 absentee; Round 1 majority = 43):')
data_table(doc,
    ['Candidate', 'Votes', 'Majority (≥ 43)?', 'Auto-suggested?'],
    [
        ['John Smith',       '55', 'Yes', 'Yes — pre-checked'],
        ['Peter Johnson',    '48', 'Yes', 'Yes — pre-checked'],
        ['Michael Williams', '30', 'No',  'No'],
        ['David Brown',      '20', 'No',  'No'],
    ],
    col_widths=[4.5, 2.5, 4.5, 4.5]
)

for step in [
    'Both John Smith and Peter Johnson are auto-checked in Step 1. Confirm by leaving them checked.',
    'Green banner appears: "All 2 positions filled." Steps 2 and 3 are hidden.',
    'Click Complete This Office. Elder election is complete.',
    'System automatically shows Round Control in "Ready to Start" mode for Deacon.',
    'Chairman announces: "John Smith and Peter Johnson have been elected as Elders."',
]:
    numbered(doc, step)

h2(doc, 'Phase 3 — Deacon Election, Round 1')
for step in [
    'Chairman introduces Deacon nominees.',
    'Election officer clicks Start Round 1 Voting.',
    'Voters who already voted for Elder enter their token again for Deacon.',
    'After voting period: Close Voting → End Round.',
]:
    numbered(doc, step)

body(doc, 'Example results (72 ballots cast incl. 5 absentee; Round 1 majority = 43):')
data_table(doc,
    ['Candidate', 'Votes', 'Majority (≥ 43)?', 'Auto-suggested?'],
    [
        ['Andrew Taylor', '28', 'No', 'No'],
        ['James Wilson',  '26', 'No', 'No'],
        ['Robert Davis',  '18', 'No', 'No'],
    ],
    col_widths=[4.5, 2.5, 4.5, 4.5]
)

body(doc, 'No majority reached — a second round is needed. Note that Round 2 majority drops to 41 (attending voters only, no absentees).')
for step in [
    'No candidate is auto-suggested in Step 1. All checkboxes are unchecked.',
    'In Step 2, uncheck Robert Davis (lowest votes) to exclude him from Round 2.',
    'Step 3 shows Votes per Voter = 1 (auto-filled; 1 position remaining).',
    'Click Launch Next Round. Round Control opens with voting closed.',
    'Chairman announces the Round 2 candidates. Election officer clicks Open Voting.',
    'Voters on the confirmation screen see: "Round 2 voting is now open — Vote Now →"',
]:
    numbered(doc, step)

h2(doc, 'Phase 4 — Deacon Election, Round 2')
body(doc, 'Example results (70 ballots cast; Round 2 majority = 41 — attending voters only, no absentees):')
data_table(doc,
    ['Candidate', 'Votes', 'Majority (≥ 41)?', 'Auto-suggested?'],
    [
        ['Andrew Taylor', '44', 'Yes', 'Yes — pre-checked'],
        ['James Wilson',  '26', 'No',  'No'],
    ],
    col_widths=[4.5, 2.5, 4.5, 4.5]
)

for step in [
    'Andrew Taylor is auto-suggested. Confirm by leaving him checked.',
    'Green banner: "All 1 position filled." Click Complete This Office.',
    'System shows the Election Complete screen listing John Smith, Peter Johnson (Elder) and Andrew Taylor (Deacon).',
    'Chairman announces Andrew Taylor is elected as Deacon.',
    'Voters\' phones show the plain thank-you message automatically.',
    'Chairman opens Election Dashboard with results password for a full record.',
]:
    numbered(doc, step)


# ════════════════════════════════════════════════════════════════════════
# 12. TROUBLESHOOTING
# ════════════════════════════════════════════════════════════════════════
h1(doc, '12.  Troubleshooting')

data_table(doc,
    ['Problem', 'Likely Cause', 'Solution'],
    [
        ['Voter page shows "No Election Configured"',
         'server.py is not running, or setup was not saved while server was running',
         'Confirm server.py is running in Terminal. Re-open Election Setup and click Save Details, then save each office setup again.'],
        ['Voter devices cannot reach vote.html',
         'Devices not on same Wi-Fi, wrong URL, or server not running',
         'Confirm all devices are on the same network. Check voter URL in Settings. Verify server.py is running.'],
        ['"Failed to record vote" error on phone',
         'Server stopped or phone lost Wi-Fi',
         'Check Terminal — restart server.py if stopped. Ensure phone is still on the correct Wi-Fi network.'],
        ['"Invalid token" error',
         'Code mistyped or tokens were regenerated after printing',
         'Double-check the 4-digit code. If tokens were regenerated, all old cards are invalid — reprint and redistribute.'],
        ['"Token already used" error',
         'Voter already voted this round, or paper ballot was submitted for their token',
         'The voter has already voted for this round. If in error, check with the chairman.'],
        ['Round Control vote counts not updating',
         'Network interruption or server restarted',
         'Refresh the browser. Counts update every 3 seconds when server is reachable.'],
        ['Expected Voters shows wrong number',
         'Details tab was not saved after editing',
         'Go to Election Setup → Details tab → correct the value → click Save Details or tab away.'],
        ['Majority Required shows incorrect number',
         'Expected Voters not saved yet',
         'Save the Expected Voters field — the majority display updates automatically.'],
        ['Paper Ballot Entry form not appearing',
         'Voting is closed or no office is active',
         'Ensure voting is open in Round Control. The screen updates within 4 seconds when voting opens.'],
        ['Voter page stuck on "Voting Not Yet Open"',
         'Round 1 has not been started in Round Control',
         'Go to Round Control → Start Round 1 Voting.'],
        ['Voter sees "Voting Round Closed" during an open round',
         'votingOpen flag is false — may have been closed accidentally',
         'In Round Control, click Open Voting to re-open the round.'],
        ['Login fails on phone or mobile device',
         'Mobile keyboard is autocapitalising or autocorrecting the password',
         'The password fields disable autocapitalize — type the password carefully. Avoid copy-pasting.'],
        ['After completing Elder, Deacon setup does not appear',
         'Deacon nominees were not saved',
         'Go to Election Setup → Deacon Election tab → enter nominees and save.'],
        ['Forgotten admin password',
         'Password changed and lost',
         'No recovery possible. Use Reset All Election Data in Settings — this deletes everything. Always record passwords securely.'],
        ['All election data lost',
         'election_state.json deleted, or wrong folder used for server',
         'The state file must be in the same folder as server.py. If deleted, data cannot be recovered.'],
        ['Delete All Election Data button not working',
         'Server not responding',
         'Confirm server.py is running. Refresh the dashboard and try again.'],
    ],
    col_widths=[4.5, 4.5, 7.0]
)


# ════════════════════════════════════════════════════════════════════════
# 13. QUICK REFERENCE
# ════════════════════════════════════════════════════════════════════════
h1(doc, '13.  Quick Reference')

h2(doc, 'Default Passwords (fill in your custom passwords)')
data_table(doc,
    ['Password', 'Default', 'Your Custom Password'],
    [
        ['Admin Password',   'election2024', '________________________________'],
        ['Results Password', 'results2024',  '________________________________'],
    ],
    col_widths=[5.0, 4.0, 7.0]
)

h2(doc, 'Voter URL')
data_table(doc,
    ['', 'Value'],
    [
        ['Voter Page URL',    '________________________________________________'],
        ['Server IP Address', '________________________________________________'],
    ],
    col_widths=[4.5, 11.5]
)

h2(doc, 'Majority Threshold')
data_table(doc,
    ['Setting', 'Value'],
    [
        ['Expected Voters (attending)',       '________'],
        ['Absentee Votes (Round 1 only)',     '________'],
        ['Round 1 Total Voters',             'Attending + Absentee  =  ________'],
        ['Round 1 Majority Required',        'floor(Round 1 Total / 2) + 1  =  ________'],
        ['Round 2+ Majority Required',       'floor(Attending / 2) + 1  =  ________'],
    ],
    col_widths=[5.5, 10.5]
)

h2(doc, 'Screen Navigation Summary')
data_table(doc,
    ['Screen', 'Who', 'Password Required', 'Purpose'],
    [
        ['Landing Page',          'All',              'None',          'Navigation hub — entry point'],
        ['Election Setup',        'Election Officer', 'Admin',         'Configure nominees, tokens, passwords, URL'],
        ['Round Control',         'Election Officer', 'Admin',         'Open/close voting, monitor ballots, end rounds'],
        ['Paper Ballot Entry',    'Volunteer',        'None',          'Enter paper votes during voting period'],
        ['Election Dashboard',    'Chairman',         'Results',       'View live status and confidential vote counts'],
        ['Election Complete',     'Election Officer', 'None (auto)',   'Shows elected candidates after all offices done'],
        ['Voter Page (vote.html)','All voters',       'None (token)',  'Submit digital votes from personal device'],
    ],
    col_widths=[4.5, 3.5, 3.0, 5.0]
)

h2(doc, 'Election Day Checklist')
checklist = [
    'server.py is running in Terminal',
    'Voter URL confirmed and tested on a phone',
    'Both passwords changed from defaults and recorded securely',
    'Results password shared with chairman only',
    'Congregation name, meeting date, Expected Voters, and Absentee Votes saved',
    'Elder nominees saved with positions and votes per voter (if Elder election is being held)',
    'Deacon nominees saved with positions and votes per voter (if Deacon election is being held)',
    'Tokens generated and token cards printed and cut',
    'Paper ballots printed for each office being voted on',
    'Token cards distributed to eligible voters at the door',
    'Paper ballot station set up with a dedicated volunteer',
    'Paper Ballot Entry opened on volunteer\'s device or laptop tab',
    'Chairman briefed on results password and Election Dashboard access',
]
for item in checklist:
    p = doc.add_paragraph()
    para_space(p, before=0, after=4)
    r = p.add_run('☐   ' + item)
    r.font.size = Pt(11)

# Footer
footer_p = doc.add_paragraph()
para_space(footer_p, before=30, after=0)
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = footer_p.add_run(
    'Church Office Bearer Election System — User Manual  |  Version 1.1.5\n'
    'All data is stored on the local server. No votes leave the meeting network.'
)
fr.font.size = Pt(9)
fr.font.color.rgb = GREY

# ── Save ─────────────────────────────────────────────────────────────────────
output_path = '/Users/johan/Documents/_CLAUDE CODE/Church Election App/manual.docx'
doc.save(output_path)
print(f'Saved: {output_path}')
