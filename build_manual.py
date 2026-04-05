#!/usr/bin/env python3
"""Generate the Church Election System manual as a .docx file."""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ── Colours ──────────────────────────────────────────────────────────────────
NAVY      = RGBColor(0x1a, 0x27, 0x44)
GOLD      = RGBColor(0xb8, 0x94, 0x2a)
ELDER     = RGBColor(0x7c, 0x3d, 0x12)
DEACON    = RGBColor(0x1a, 0x3a, 0x5c)
GREEN     = RGBColor(0x2d, 0x6a, 0x4f)
RED       = RGBColor(0x9b, 0x23, 0x35)
GREY      = RGBColor(0x66, 0x66, 0x66)
LIGHT_BG  = RGBColor(0xf8, 0xf6, 0xf1)
NOTE_BG   = RGBColor(0xe8, 0xf0, 0xfa)
WARN_BG   = RGBColor(0xff, 0xf4, 0xe0)
DANG_BG   = RGBColor(0xfd, 0xf0, 0xf0)
TIP_BG    = RGBColor(0xf0, 0xfa, 0xf0)
WHITE     = RGBColor(0xff, 0xff, 0xff)

doc = Document()

# ── Page margins ─────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

# ── Styles helper ─────────────────────────────────────────────────────────────
def set_font(run, bold=False, italic=False, size=None, colour=None):
    run.bold   = bold
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    if colour:
        run.font.color.rgb = colour

def para_space(para, before=0, after=6):
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after  = Pt(after)

def shade_cell(cell, hex_colour):
    """Fill a table cell with a solid background colour."""
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

def add_page_break(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_break(docx_breaks.WD_BREAK.PAGE)

# import break type
from docx.enum.text import WD_BREAK
import docx.enum.text as docx_breaks

# ── Heading helpers ───────────────────────────────────────────────────────────
def h1(doc, text):
    """Section heading — large, navy, with top rule."""
    p = doc.add_paragraph()
    para_space(p, before=18, after=6)
    p.paragraph_format.page_break_before = True
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = NAVY
    # bottom border
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

def body(doc, text, bold_parts=None):
    p = doc.add_paragraph()
    para_space(p, before=0, after=5)
    if bold_parts:
        # simple bold splitting — not used heavily
        p.add_run(text)
    else:
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

# ── Callout box (note / tip / warning / danger) ────────────────────────────
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
    # spacer after table
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def note(doc, text):
    callout(doc, 'NOTE:', text, 'E8F0FA', '1A3A5C')

def tip(doc, text):
    callout(doc, 'TIP:', text, 'F0FAF0', '2D6A4F')

def warning(doc, text):
    callout(doc, 'IMPORTANT:', text, 'FFF4E0', 'B8942A')

def danger(doc, text):
    callout(doc, 'ACTION REQUIRED:', text, 'FDF0F0', '9B2335')

# ── Screenshot placeholder ─────────────────────────────────────────────────
def screenshot(doc, label, description):
    tbl = doc.add_table(rows=2, cols=1)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Label row
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

    # Description row
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

    # Header row
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

    # Data rows
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

    # Column widths
    if col_widths:
        for ri2, row2 in enumerate(tbl.rows):
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
para_space(sub, before=6, after=40)
sr = sub.add_run('Complete User Manual')
sr.font.size = Pt(16)
sr.font.color.rgb = GOLD

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

# Page break after cover
pb = doc.add_paragraph()
pb.add_run().add_break(WD_BREAK.PAGE)

# ════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS (manual — auto TOC not easily done in python-docx)
# ════════════════════════════════════════════════════════════════════════
toc_title = doc.add_paragraph()
toc_title.paragraph_format.page_break_before = False
para_space(toc_title, before=0, after=8)
tr2 = toc_title.add_run('Table of Contents')
tr2.bold = True
tr2.font.size = Pt(16)
tr2.font.color.rgb = NAVY

toc_entries = [
    ('1.', 'System Overview'),
    ('2.', 'Technical Requirements'),
    ('3.', 'Passwords & Security'),
    ('4.', 'Before the Meeting — Election Setup'),
    ('   4a.', 'Congregation Details'),
    ('   4b.', 'Elder Election Configuration'),
    ('   4c.', 'Deacon Election Configuration'),
    ('   4d.', 'Tokens — Generating & Printing'),
    ('   4e.', 'Settings — URL, QR Code & Passwords'),
    ('5.', 'During the Meeting — Round Control'),
    ('   5a.', 'Accessing Round Control'),
    ('   5b.', 'Starting Round 1'),
    ('   5c.', 'Opening and Closing Voting'),
    ('   5d.', 'Monitoring Participation'),
    ('   5e.', 'Ending a Round & Round Transition'),
    ('   5f.', 'Confirming Elected Candidates'),
    ('   5g.', 'Configuring the Next Round'),
    ('   5h.', 'Completing an Office'),
    ('6.', 'Paper Ballot Entry'),
    ('7.', 'The Voter Page'),
    ('8.', 'Election Dashboard'),
    ('9.', 'Complete Election Walkthrough'),
    ('10.', 'Troubleshooting'),
    ('11.', 'Quick Reference'),
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
    'connection is required. All election data is stored in a single file on the laptop '
    'and is shared in real time across all devices on the local Wi-Fi network.'
))

h2(doc, 'How the System Works')
body(doc, 'The system consists of three files and a local server:')

data_table(doc,
    ['File', 'Purpose', 'Who Uses It'],
    [
        ['server.py',      'Local Python server — serves the app and stores all election data', 'Must be running throughout the election'],
        ['index.html',     'Administration hub — all setup and control functions',              'Election Officer, Chairman'],
        ['vote.html',      'Voter ballot page — members cast their votes here',                 'All voting members'],
        ['election_state.json', 'Shared election data file — created automatically by the server', '(Not opened directly)'],
    ],
    col_widths=[4.0, 8.0, 4.0]
)

h2(doc, 'Key Features')
for feat in [
    'Supports multi-round elections with automatic majority detection',
    'Separate elections for the offices of Elder and Deacon',
    'Digital voting via personal devices (phones/tablets) using unique token codes',
    'Paper ballot entry for members who prefer to vote on paper',
    'Password-protected administration and confidential results',
    'Real-time participation monitoring — round control updates every 3 seconds',
    'Automatic voter page updates — voters are notified when new rounds open',
    'No internet required; all data stays on the meeting laptop',
    'Atomic vote submission — concurrent votes from multiple devices are handled safely',
]:
    bullet(doc, feat)

note(doc, (
    'All election data is stored in election_state.json on the laptop. This file is created '
    'automatically when the first save occurs. Do not delete it during an election. '
    'If the server is stopped and restarted, all data is preserved in this file.'
))

screenshot(doc, 'Landing Page',
    'The main landing page of index.html showing navigation buttons: Election Setup, '
    'Round Control, Paper Ballot Entry, Election Dashboard, and the Voter Ballot URL at the bottom.')


# ════════════════════════════════════════════════════════════════════════
# 2. TECHNICAL REQUIREMENTS
# ════════════════════════════════════════════════════════════════════════
h1(doc, '2.  Technical Requirements')

h2(doc, 'Administrator Device (Laptop/PC)')
for item in [
    'Any modern web browser (Chrome, Edge, Firefox, or Safari — 2020 or later)',
    'The two files index.html and vote.html must be in the same folder',
    'JavaScript must be enabled in the browser',
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

h2(doc, 'Starting the Server')
body(doc, (
    'The system requires the included server.py to be running throughout the election. '
    'This serves the HTML files to all devices and stores all election data in one shared file.'
))
for step in [
    'Open a Terminal in the folder containing server.py, index.html, and vote.html.',
    'Run the command:  python3 server.py',
    'The terminal will display the local IP address and voter URL, for example:',
]:
    numbered(doc, step)

body(doc, '          Admin / local:   http://localhost:8080/')
body(doc, '          Voter devices:   http://192.168.1.45:8080/vote.html')
body(doc, '          State file:      .../election_state.json')

for step in [
    'Open http://localhost:8080/ in the browser on the laptop to access the admin hub.',
    'Enter the voter URL (e.g. http://192.168.1.45:8080/vote.html) in the Settings tab.',
]:
    numbered(doc, step, level=0)

warning(doc, (
    'The server must remain running for the entire duration of the election. '
    'If it is stopped, voters will be unable to access the ballot page and votes cannot be submitted. '
    'Do not close the Terminal window while the election is in progress.'
))

tip(doc, 'Test the voter URL on a phone before the meeting to confirm connectivity. Voters can also scan the QR code printed on their token card.')


# ════════════════════════════════════════════════════════════════════════
# 3. PASSWORDS & SECURITY
# ════════════════════════════════════════════════════════════════════════
h1(doc, '3.  Passwords & Security')

body(doc, 'The system uses two separate passwords to protect different areas:')

data_table(doc,
    ['Password', 'Protects', 'Default'],
    [
        ['Admin Password',   'Election Setup and Round Control',      'election2024'],
        ['Results Password', 'Election Dashboard (confidential results)', 'results2024'],
    ],
    col_widths=[4.5, 7.5, 4.0]
)

danger(doc, (
    'Change both passwords before the election. Default passwords are publicly known. '
    'Use the Settings tab in Election Setup to update them.'
))

body(doc, (
    'Passwords are stored as SHA-256 cryptographic hashes — the actual password text is '
    'never saved anywhere in the system.'
))

h2(doc, 'Who Has Which Password')
bullet(doc, 'Admin password — Election officer only (used to configure and run the election)')
bullet(doc, 'Results password — Chairman of the meeting only (used to view results on the Election Dashboard)')

warning(doc, 'Keep these passwords separate and confidential. The chairman does not need the admin password.')


# ════════════════════════════════════════════════════════════════════════
# 4. ELECTION SETUP
# ════════════════════════════════════════════════════════════════════════
h1(doc, '4.  Before the Meeting — Election Setup')

body(doc, (
    'All setup should be completed before the congregational meeting. Open index.html '
    'in the browser, click Election Setup on the landing page, and enter the admin password. '
    'Election Setup is organised into five tabs: Details, Elder, Deacon, Tokens, and Settings.'
))

screenshot(doc, 'Login Screen',
    'The password login screen with a single password field and "Enter Setup" button.')

# 4a
h2(doc, '4a.  Congregation Details')
body(doc, 'Click the Details tab and fill in the following fields:')

data_table(doc,
    ['Field', 'Description', 'Example'],
    [
        ['Congregation Name', 'Full name of the congregation. Appears on ballots, token cards, and the voter page.', 'First Reformed Church'],
        ['Meeting Date',      'Date of the congregational meeting.',                                                  '2025-11-09'],
        ['Expected Voters',   'Total number of eligible male voters. Used to calculate participation percentages.',   '85'],
    ],
    col_widths=[4.0, 8.5, 3.5]
)

body(doc, 'Fields auto-save when you move to the next field. You can also click Save Details to save manually.')

screenshot(doc, 'Details Tab',
    'Three form fields: Congregation Name, Meeting Date (date picker), and Expected Voters (number input), with a Save Details button.')

# 4b
h2(doc, '4b.  Elder Election Configuration')
body(doc, 'Click the Elder tab and enter the following:')

data_table(doc,
    ['Field', 'Description', 'Example'],
    [
        ['Nominees',                 'One name per line. All men nominated for the office of Elder.',                              'John Smith\nPeter Johnson\nMichael Williams\nDavid Brown'],
        ['Positions to Fill',        'How many Elders need to be elected in this election.',                                      '2'],
        ['Votes per Voter (Round 1)','How many candidates each voter may vote for in Round 1. Typically equal to positions.',      '2'],
    ],
    col_widths=[4.5, 8.0, 3.5]
)

body(doc, 'Click Save Elder Setup when done. A green confirmation message will appear.')

screenshot(doc, 'Elder Tab',
    'Multi-line nominees text area, positions number input, votes per voter input, and Save Elder Setup button.')

warning(doc, 'Saving the setup resets any in-progress election data for that office. Do not save setup during an active election round unless you intend to restart.')

# 4c
h2(doc, '4c.  Deacon Election Configuration')
body(doc, (
    'Click the Deacon tab and repeat the same process — enter nominees, positions to fill, '
    'and votes per voter for Round 1. Click Save Deacon Setup.'
))

screenshot(doc, 'Deacon Tab',
    'Identical layout to the Elder tab but with the Deacon office branding (deep blue colour scheme).')

# 4d
h2(doc, '4d.  Tokens — Generating & Printing')

h3(doc, 'Generating Tokens')
body(doc, (
    'Tokens are unique 4-digit codes that identify each eligible voter. Each voter receives '
    'one token card which is used for both the Elder and Deacon elections.'
))
for step in [
    'Enter the number of tokens to generate (equal to the number of eligible voters, e.g. 85).',
    'Click Generate Tokens. The system creates unique 4-digit codes.',
    'Review the list to confirm the correct number was generated.',
]:
    numbered(doc, step)

screenshot(doc, 'Tokens Tab',
    'Token generation controls (number input + Generate button), list of generated codes, and print buttons at the bottom right.')

h3(doc, 'Printing Token Cards')
body(doc, (
    'Click Print Token Cards. The system formats all tokens as a 4-column grid of cards. '
    'Each card includes the congregation name, the 4-digit token code, a QR code linking '
    'to the voter page, and the voting URL. Print on card stock if possible and distribute '
    'one card per eligible voter at the door.'
))

screenshot(doc, 'Token Cards Print Preview',
    '4-column grid of token cards. Each card shows: church name, large 4-digit code, QR code, and the voter URL.')

warning(doc, (
    'The QR code on token cards comes from the URL configured in the Settings tab. '
    'Configure the voter URL in Settings BEFORE printing token cards.'
))

h3(doc, 'Printing Paper Ballots')
body(doc, (
    'For members who prefer to vote on paper, the system can print ballot cards. '
    'Each ballot shows all candidates with a checkbox next to each name.'
))
for item in [
    'Set the desired quantity (e.g. 20) in the Elder ballots quantity field.',
    'Click Print Elder Ballots — a page with ballot cards in a 2-column grid is printed.',
    'Repeat for Deacon ballots.',
    'Cut the ballots and have them available at a paper ballot station.',
]:
    bullet(doc, item)

note(doc, (
    'Paper ballots do not include round information or the number of votes per round — '
    'this is intentional so that the same printed ballots can be reused across multiple '
    'rounds. Verbally inform voters which candidates are valid for each round and how many '
    'they may select.'
))

screenshot(doc, 'Paper Ballot Print Preview',
    '2-column grid of ballot cards. Each card shows office name, church name, positions to fill, and candidate names with checkboxes.')

# 4e
h2(doc, '4e.  Settings — URL, QR Code & Passwords')

h3(doc, 'Voter URL')
body(doc, (
    'Enter the full URL that voters will use to access the ballot page, e.g. '
    'http://192.168.1.45:8080/vote.html. Click Save URL. This URL will appear on token '
    'cards, the QR code, and the landing page.'
))

h3(doc, 'QR Code')
body(doc, (
    'Once the URL is saved, a QR code is automatically generated. Voters scan this code '
    'with their phone camera to open the voter page instantly. Click Print QR Code to print '
    'a full-page QR code for display in the meeting room.'
))

h3(doc, 'Change Admin Password')
body(doc, (
    'Enter your current password (default: election2024), then a new password (minimum '
    '4 characters), and confirm it. Click Update Admin Password.'
))

h3(doc, 'Change Results Password')
body(doc, (
    'Enter the current results password (default: results2024), a new password, and '
    'confirm. Click Update Results Password. Share this new password only with the chairman.'
))

screenshot(doc, 'Settings Tab',
    'Voter URL section; QR Code section with generated QR code image; Change Admin Password card; Change Results Password card.')

danger(doc, (
    'The Reset All Election Data button at the bottom of Settings permanently erases ALL '
    'nominees, ballots, tokens, and results. Two confirmation prompts prevent accidental use. '
    'Only use this to start fresh before a new election.'
))


# ════════════════════════════════════════════════════════════════════════
# 5. ROUND CONTROL
# ════════════════════════════════════════════════════════════════════════
h1(doc, '5.  During the Meeting — Round Control')

body(doc, (
    'Round Control is used during the meeting to manage all aspects of the voting process. '
    'It is the central control panel for the election officer.'
))

h2(doc, '5a.  Accessing Round Control')
for step in [
    'From the landing page of index.html, click Round Control.',
    'Enter the admin password and click Enter Round Control.',
]:
    numbered(doc, step)

screenshot(doc, 'Round Control Login',
    'Login screen with subtitle "Enter the admin password to access Round Control" and "Enter Round Control" button.')

h2(doc, '5b.  Starting Round 1')
body(doc, (
    'When you first enter Round Control after completing setup, the system detects the '
    'configured Elder election and shows a "Ready to Start" panel confirming the number '
    'of nominees, positions to fill, and votes per voter in Round 1.'
))
body(doc, 'Click Start Round 1 Voting to begin. This immediately opens voting for all voters.')

screenshot(doc, 'Round Control — Ready to Start',
    'Header in dark brown (Elder colour). Panel shows "Elder Election — Configured" with number of nominees, positions, and votes per voter. Large "Start Round 1 Voting" button.')

tip(doc, 'Do not click Start Round 1 until the chairman has introduced the candidates and is ready for voting to begin.')

h2(doc, '5c.  Opening and Closing Voting')
body(doc, 'Once a round is active, the Round Control screen shows the control bar:')

data_table(doc,
    ['Button', 'Action', 'When to Use'],
    [
        ['Open Voting',  'Opens voting so members can submit ballots',     'At the start of each voting round'],
        ['Close Voting', 'Stops new votes from being submitted',           'When sufficient time has passed or all votes are in'],
        ['End Round',    'Finalises the round and opens the transition screen', 'Only after voting is closed'],
    ],
    col_widths=[4.0, 7.0, 5.0]
)

warning(doc, 'You cannot end a round while voting is open. Always close voting first.')

screenshot(doc, 'Round Control — Active (Voting Open)',
    'Coloured header with office and round; sequence bar (Elder → Deacon → Complete); four stat boxes; control bar with Open/Close/End buttons and voting status indicator; candidate results list below.')

h2(doc, '5d.  Monitoring Participation')
body(doc, 'The four statistics boxes update automatically every 3 seconds:')

data_table(doc,
    ['Stat', 'Meaning'],
    [
        ['Ballots In',       'Total number of ballots received (digital + paper) for the current round'],
        ['Paper Ballots',    'Number of ballots entered via the Paper Ballot Entry station'],
        ['Expected Voters',  'The number entered in Election Setup — used as the denominator for percentage'],
        ['Participation %',  'Ballots In ÷ Expected Voters × 100. Shown in green when ≥ 50%.'],
    ],
    col_widths=[4.5, 11.5]
)

note(doc, (
    'The vote counts per candidate visible in Round Control are for the election officer\'s '
    'operational use only. They are not shared publicly. Confidential results are only '
    'available on the Election Dashboard.'
))

h2(doc, '5e.  Ending a Round & Round Transition')
body(doc, (
    'Once voting is closed, click End Round. The Round Transition screen opens, showing '
    'the final results for the round and four steps to manage the transition.'
))

screenshot(doc, 'Round Transition Screen',
    'Final Results section (candidates ranked by position); Step 1 — elected checkboxes with majority badges; Step 2 — advancing candidates; Step 3 — next ballot preview with Remove buttons; Step 4 — votes per voter for next round; Launch or Complete button at bottom.')

h2(doc, '5f.  Confirming Elected Candidates (Step 1)')
body(doc, (
    'The system automatically detects candidates who received a majority of votes '
    '(strictly more than 50% of all ballots cast) and pre-checks them with a "majority" badge.'
))
bullet(doc, 'Check the box to mark a candidate as elected in this round.')
bullet(doc, 'Uncheck to override the auto-suggestion if necessary.')

note(doc, (
    'Majority Rule: A candidate must receive strictly more than half the total ballots cast '
    '(floor(n/2) + 1 or more votes) to be automatically suggested as elected.'
))

h2(doc, '5g.  Configuring the Next Round (Steps 2–4)')
body(doc, 'Step 2 — Candidates Advancing: All non-elected candidates are listed to advance to the next round. Uncheck any candidate you wish to remove.')
body(doc, 'Step 3 — Next Ballot Preview: Shows which candidates will appear on the next ballot. Use the Remove button to remove individuals (Restore to undo).')
body(doc, 'Step 4 — Votes Per Voter: Set how many candidates each voter may select in the next round. The system auto-fills this as the number of remaining positions. Adjust if needed.')

screenshot(doc, 'Round Transition Steps 2–4',
    'Advancing candidates checkboxes; next ballot list with Remove buttons; votes per voter input with auto-fill hint; "Launch Round 2 Voting" button.')

h2(doc, '5h.  Completing an Office')
body(doc, (
    'When all positions for an office have been filled, the system shows a '
    '"Complete This Office" button instead of a next-round button.'
))

screenshot(doc, 'All Positions Filled Banner',
    'Gold banner reading "All X positions filled" above the Complete This Office button.')

body(doc, 'Click Complete This Office. The system:')
for step in [
    'Records the final election results for that office.',
    'Automatically moves to Round Control for the Deacon election in "Ready to Start" mode.',
]:
    numbered(doc, step)

body(doc, 'Repeat the entire Round Control process for the Deacon election. When the Deacon election is also complete, clicking Complete This Office returns to the landing page.')


# ════════════════════════════════════════════════════════════════════════
# 6. PAPER BALLOT ENTRY
# ════════════════════════════════════════════════════════════════════════
h1(doc, '6.  Paper Ballot Entry')

body(doc, (
    'The Paper Ballot Entry screen is used by a dedicated volunteer to enter votes on '
    'behalf of members who voted on paper. It is accessible from the landing page without '
    'a password.'
))

warning(doc, 'Only open Paper Ballot Entry on the administrator\'s laptop. Ensure voting is open before entering paper ballots.')

h2(doc, '6a.  Entering a Paper Ballot')
for step in [
    'The current office and round are shown automatically. If voting is closed, a warning is displayed.',
    'Click on each candidate\'s name that appears on the paper ballot. Selected candidates are highlighted.',
    'Optionally enter a member identifier in the Member ID field for tracking.',
    'Click Submit Paper Ballot. The vote is recorded and the form resets.',
    'The submitted ballot appears in the log at the bottom of the screen.',
]:
    numbered(doc, step)

screenshot(doc, 'Paper Ballot Entry Screen',
    'Current office and round at top; selectable candidate rows; optional Member ID field; Submit Paper Ballot button; log of previously entered ballots at the bottom.')

h2(doc, '6b.  Editing a Submitted Ballot')
body(doc, 'If a mistake is made, any paper ballot from the current round can be corrected:')
for step in [
    'Find the ballot in the log at the bottom of the screen.',
    'Click the Edit button next to the ballot entry.',
    'The form re-populates with the previous selections. An "Editing Ballot #X" banner appears.',
    'Make the necessary corrections.',
    'Click Update Paper Ballot to save, or Cancel to discard changes.',
]:
    numbered(doc, step)

screenshot(doc, 'Paper Ballot Edit Mode',
    'Edit mode showing orange "Editing Ballot #X" banner, previously selected candidates highlighted, Update and Cancel buttons.')

h2(doc, '6c.  Printing Paper Ballots')
body(doc, 'Paper ballots are printed from the Tokens tab in Election Setup (before the meeting). Each ballot card shows:')
bullet(doc, 'Office name (Office of Elder or Office of Deacon)')
bullet(doc, 'Congregation name')
bullet(doc, 'Number of positions to be filled')
bullet(doc, 'All nominees with a checkbox next to each name')

note(doc, (
    'Because round information is not printed on the ballots, the same printed ballots '
    'can be reused across multiple rounds. The chairman verbally announces which candidates '
    'are valid for each round and how many votes each member may cast.'
))


# ════════════════════════════════════════════════════════════════════════
# 7. THE VOTER PAGE
# ════════════════════════════════════════════════════════════════════════
h1(doc, '7.  The Voter Page')

body(doc, (
    'The voter page (vote.html) is what voting members see on their phones or tablets. '
    'It automatically updates every few seconds to reflect the current election state.'
))

h2(doc, '7a.  Accessing the Voter Page')
bullet(doc, 'QR Code: Scan the QR code on the token card with a phone camera.')
bullet(doc, 'URL: Type the URL printed on the token card into the phone\'s browser.')

h2(doc, '7b.  Entering a Token')
for step in [
    'The voter opens the voter page URL or scans the QR code on their token card.',
    'They type their 4-digit token code into the input field.',
    'Tap Submit Token.',
]:
    numbered(doc, step)

body(doc, 'If the token is invalid or has already been used for the current round, an error message is shown.')

screenshot(doc, 'Voter Page — Token Entry',
    'White card on dark navy background. Header shows congregation name and "Voting Open" pill. Large 4-digit numeric input and Submit Token button.')

h2(doc, '7c.  Casting a Vote')
for step in [
    'The voter reads the list of candidates. The number they may select is shown.',
    'Tap each candidate\'s name to select them. A checkmark appears next to selected candidates.',
    'The voter may select up to the permitted number but is not required to use all selections.',
    'Tap Submit Vote. A confirmation screen appears.',
]:
    numbered(doc, step)

screenshot(doc, 'Voter Ballot Screen',
    'Office badge (e.g. "ELDER · ROUND 1"), candidate list as tappable rows with circle checkboxes, vote counter, and Submit Vote button.')

warning(doc, (
    'Votes are final once submitted. There is no way for the voter to change their vote '
    'after submission. Digital votes cannot be edited — only paper ballots can be corrected '
    'via the Paper Ballot Entry screen.'
))

h2(doc, '7d.  Voter Screen States')

data_table(doc,
    ['State', 'When It Appears', 'What the Voter Sees'],
    [
        ['Token Entry',         'Voting is open and member has not yet voted this round',              '4-digit token input and Submit button'],
        ['Ballot',              'After a valid token is submitted',                                    'Candidate list with checkboxes and Submit Vote button'],
        ['Vote Submitted',      'After the voter has submitted their ballot',                          '"Vote Submitted!" confirmation with names they voted for. Auto-notification when next round opens.'],
        ['Voting Round Closed', 'Round controller closes voting while voter is on token entry screen', '"Voting Round Closed — please wait for the chairman\'s instructions." Auto-updates within 3 seconds.'],
        ['Voting Not Yet Open', 'Election is configured but round has not started',                    '"Voting Not Yet Open." Automatically advances when voting opens.'],
        ['Election Complete',   'Both offices have been filled and election concluded',                '"Election Complete — Thank you for participating."'],
    ],
    col_widths=[4.5, 5.5, 6.0]
)

screenshot(doc, 'Vote Submitted — with Next Round Notification',
    '"Vote Submitted!" screen with green checkmark. Below, a coloured notification card: "Office of Deacon voting is now open — Vote Now →" button.')

screenshot(doc, 'Voting Round Closed State',
    'Hourglass icon, "Voting Round Closed" heading, "please wait for the chairman\'s instructions" subtext, and Check Again button.')

screenshot(doc, 'Election Complete State',
    'Green checkmark icon, "Election Complete" heading, "Thank you for participating" message.')

note(doc, (
    'Token Reuse: Each token can be used once per round per office. A member uses the same '
    'token card for both the Elder and Deacon elections and for each new round. They do not '
    'receive a new token for subsequent rounds.'
))


# ════════════════════════════════════════════════════════════════════════
# 8. ELECTION DASHBOARD
# ════════════════════════════════════════════════════════════════════════
h1(doc, '8.  Election Dashboard')

body(doc, (
    'The Election Dashboard is a read-only, password-protected view designed for the '
    'chairman of the meeting. It shows the current election status and confidential results.'
))

for step in [
    'From the landing page of index.html, click Election Dashboard.',
    'Enter the results password (not the admin password) and click View Results.',
]:
    numbered(doc, step)

screenshot(doc, 'Election Dashboard',
    'White card on navy background. "Election Dashboard" heading with church name and date. Status section with coloured status box showing office, round, status pill, votes per voter, and candidate chips. Results sections below for Elder and Deacon with vote bars and elected/not-elected badges.')

h2(doc, 'Status Section')
body(doc, 'The status section updates automatically every 3 seconds and shows:')

data_table(doc,
    ['Information', 'Description'],
    [
        ['Office & Round',    'Which office is currently being voted on and the round number'],
        ['Status Pill',       'Voting Open (green) / Voting Closed (orange) / Configuring (blue)'],
        ['Votes per Voter',   'How many candidates each voter may select in the current round'],
        ['Candidates This Round', 'The names of all candidates on the current ballot'],
    ],
    col_widths=[5.0, 11.0]
)

h2(doc, 'Results Section')
body(doc, 'For each office, all candidates are listed with:')
bullet(doc, 'Their total vote count')
bullet(doc, 'A relative bar chart showing vote proportion')
bullet(doc, '"Elected · Rd X" badge if elected, or "Not elected" if they were not')

warning(doc, (
    'Confidentiality: The Dashboard shows actual vote counts. Only share the results '
    'password with the chairman. Do not leave the dashboard visible on an unattended screen.'
))


# ════════════════════════════════════════════════════════════════════════
# 9. COMPLETE ELECTION WALKTHROUGH
# ════════════════════════════════════════════════════════════════════════
h1(doc, '9.  Complete Election Walkthrough')

body(doc, (
    'This section walks through a complete election using a realistic example: '
    'electing 2 Elders and 1 Deacon from a congregation of 70 voters.'
))

h2(doc, 'Example Setup')
data_table(doc,
    ['', 'Elder', 'Deacon'],
    [
        ['Nominees',          'John Smith, Peter Johnson, Michael Williams, David Brown', 'Andrew Taylor, James Wilson, Robert Davis'],
        ['Positions',         '2',  '1'],
        ['Votes per Voter',   '2',  '1'],
        ['Expected Voters',   '70', '70'],
    ],
    col_widths=[4.0, 8.0, 4.0]
)

h2(doc, 'Phase 1 — Before the Meeting')
for step in [
    'Open a Terminal in the election folder and run:  python3 server.py',
    'Open http://localhost:8080/ in Chrome on the meeting laptop.',
    'Go to Election Setup → Settings tab → enter voter URL → Save URL. The QR code updates.',
    'Change both passwords in Settings. Record them securely.',
    'Go to Details tab. Enter congregation name, meeting date, and 70 as expected voters.',
    'Go to Elder tab. Enter four nominee names, Positions = 2, Votes per Voter = 2. Save.',
    'Go to Deacon tab. Enter three nominee names, Positions = 1, Votes per Voter = 1. Save.',
    'Go to Tokens tab. Enter 70 → Generate Tokens → Print Token Cards. Cut and prepare 70 cards.',
    'Print paper ballots: 15 Elder ballots and 15 Deacon ballots from the Tokens tab.',
    'Test the voter URL on a phone — confirm the token entry screen appears.',
    'Distribute token cards to eligible voters as they arrive at the meeting.',
]:
    numbered(doc, step)

h2(doc, 'Phase 2 — Elder Election, Round 1')
for step in [
    'Chairman announces the start of Elder voting.',
    'Election officer: Round Control → Start Round 1 Voting. Voting is now open.',
    'Voters open the voter URL, enter their token, and select up to 2 candidates.',
    'Paper ballot volunteers distribute ballots, collect them, and enter them via Paper Ballot Entry.',
    'When satisfied, election officer clicks Close Voting then End Round.',
]:
    numbered(doc, step)

body(doc, 'Example results after Round 1 (70 ballots cast, majority threshold = 36 votes):')
data_table(doc,
    ['Candidate', 'Votes', 'Majority (> 35)?'],
    [
        ['John Smith',       '42', 'Yes — auto-suggested as elected'],
        ['Peter Johnson',    '38', 'Yes — auto-suggested as elected'],
        ['Michael Williams', '22', 'No'],
        ['David Brown',      '18', 'No'],
    ],
    col_widths=[5.0, 3.0, 8.0]
)

for step in [
    'Both John Smith and Peter Johnson are auto-checked with "majority" badges in Step 1. Confirm by leaving them checked.',
    'Since 2 positions are now filled, the Complete This Office button appears.',
    'Click Complete This Office. The Elder election is done.',
]:
    numbered(doc, step)

h2(doc, 'Phase 3 — Deacon Election, Round 1')
for step in [
    'The system automatically shows Round Control for the Deacon election in "Ready to Start" mode.',
    'Chairman announces the start of Deacon voting. The voter page updates automatically.',
    'Election officer clicks Start Round 1 Voting.',
    'After voting, click Close Voting → End Round.',
]:
    numbered(doc, step)

body(doc, 'Example results after Deacon Round 1 (68 ballots cast, majority threshold = 35 votes):')
data_table(doc,
    ['Candidate', 'Votes', 'Majority (> 34)?'],
    [
        ['Andrew Taylor', '28', 'No'],
        ['James Wilson',  '25', 'No'],
        ['Robert Davis',  '15', 'No'],
    ],
    col_widths=[5.0, 3.0, 8.0]
)
body(doc, 'No majority — a second round is needed.')

h2(doc, 'Phase 4 — Deacon Election, Round 2')
for step in [
    'In the Round Transition screen, no candidate is auto-suggested. All checkboxes in Step 1 are unchecked.',
    'In Step 2, uncheck Robert Davis (lowest-ranked) to remove him from the next round.',
    'Step 3 shows the next ballot: Andrew Taylor and James Wilson. Votes per voter = 1 (auto-filled).',
    'Click Launch Round 2 Voting. Voters on the "Vote Submitted" screen see a "Round 2 is now open" notification.',
    'After Round 2: Andrew Taylor receives 40 votes (majority). He is auto-suggested as elected.',
    'Confirm Andrew Taylor in Step 1. Click Complete This Office.',
]:
    numbered(doc, step)

h2(doc, 'Phase 5 — Election Conclusion')
for step in [
    'After completing the Deacon election, the system returns to the landing page.',
    'Voters\' screens automatically show "Election Complete — Thank you for participating."',
    'The chairman opens the Election Dashboard with the results password and announces the elected officers.',
]:
    numbered(doc, step)


# ════════════════════════════════════════════════════════════════════════
# 10. TROUBLESHOOTING
# ════════════════════════════════════════════════════════════════════════
h1(doc, '10.  Troubleshooting')

data_table(doc,
    ['Problem', 'Likely Cause', 'Solution'],
    [
        ['Voters cannot reach the voter page',
         'server.py is not running, devices not on the same Wi-Fi, or wrong URL',
         'Confirm server.py is running in Terminal. Confirm all devices are on the same Wi-Fi. Check the URL in Settings.'],
        ['Voter page shows "No Active Election" even after setup',
         'server.py was not running when setup was saved, so data was not written to the shared file',
         'Ensure server.py is running, then re-save the election setup. The data will now be shared across devices.'],
        ['"Failed to record vote" error on voter\'s phone',
         'server.py stopped, or phone lost Wi-Fi connection',
         'Check that server.py is still running in Terminal and that the phone is still on the same Wi-Fi.'],
        ['"Invalid token" error',
         'Code mistyped, or tokens were regenerated after printing',
         'Double-check the 4-digit code. If regenerated, print and redistribute new cards.'],
        ['"Token already used" error',
         'Voter already voted this round, or a duplicate entry was made',
         'Check the Paper Ballot log. Contact the voter to verify.'],
        ['Round Control vote counts are not updating',
         'server.py was recently restarted or network interruption',
         'Refresh the Round Control screen. Counts update every 3 seconds from the shared state file.'],
        ['Expected Voters shows 100',
         'Expected Voters field was not saved in Election Setup',
         'Go to Election Setup → Details tab → correct the value and tab away.'],
        ['Voter page stuck on "Voting Not Yet Open"',
         'Round 1 has not been started in Round Control',
         'Go to Round Control and click Start Round 1 Voting.'],
        ['Percentage stays at 0%',
         'Expected Voters is set to 0',
         'Update Expected Voters in Election Setup Details tab.'],
        ['Forgotten admin password',
         'Password was changed and lost',
         'No recovery possible. Use Reset All Election Data in Settings — this deletes everything. Keep the password written down securely.'],
        ['After completing Elder, Deacon candidates do not appear',
         'Deacon nominees were not saved in Election Setup',
         'Go to Election Setup → Deacon tab → add nominees and save. Then go to Round Control.'],
        ['All data was lost after restarting',
         'election_state.json was deleted or the wrong folder was used',
         'The state file election_state.json must remain in the same folder as server.py. Do not delete it during an election.'],
    ],
    col_widths=[4.5, 5.0, 6.5]
)


# ════════════════════════════════════════════════════════════════════════
# 11. QUICK REFERENCE
# ════════════════════════════════════════════════════════════════════════
h1(doc, '11.  Quick Reference')

h2(doc, 'Default Passwords (Fill in your custom passwords below)')
data_table(doc,
    ['Password', 'Default Value', 'Changed To'],
    [
        ['Admin Password',   'election2024', '________________________________'],
        ['Results Password', 'results2024',  '________________________________'],
    ],
    col_widths=[5.0, 4.5, 6.5]
)

h2(doc, 'Voter URL')
data_table(doc,
    ['Field', 'Value'],
    [
        ['Voter Page URL',    '________________________________________________'],
        ['Laptop IP Address', '________________________________________________'],
    ],
    col_widths=[5.0, 11.0]
)

h2(doc, 'Election Day Checklist')
for item in [
    'Passwords changed from defaults',
    'Voter URL entered and tested on a phone',
    'Congregation details saved (name, date, expected voters)',
    'Elder nominees saved with positions and votes per voter',
    'Deacon nominees saved with positions and votes per voter',
    'Tokens generated and token cards printed',
    'Paper ballots printed (Elder and Deacon)',
    'Results password shared with chairman only',
    'Token cards distributed to voters at the door',
    'Paper ballot station set up with a dedicated volunteer',
]:
    p = doc.add_paragraph()
    para_space(p, before=0, after=4)
    r = p.add_run('☐   ' + item)
    r.font.size = Pt(11)

h2(doc, 'Screen Navigation Summary')
data_table(doc,
    ['Screen', 'Who', 'Password', 'Purpose'],
    [
        ['Landing Page',        'All',             'None',    'Navigation hub'],
        ['Election Setup',      'Election Officer','Admin',   'Configure nominees, tokens, settings'],
        ['Round Control',       'Election Officer','Admin',   'Manage voting rounds'],
        ['Paper Ballot Entry',  'Volunteer',       'None',    'Enter paper votes'],
        ['Election Dashboard',  'Chairman',        'Results', 'Monitor status and view results'],
        ['Voter Page (vote.html)', 'All voters',   'None (token)', 'Cast digital votes'],
    ],
    col_widths=[5.0, 4.0, 3.0, 4.0]
)

# Footer
footer_p = doc.add_paragraph()
para_space(footer_p, before=30, after=0)
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = footer_p.add_run('Church Office Bearer Election System — User Manual\nAll data is stored locally in the browser. No votes leave the device.')
fr.font.size = Pt(9)
fr.font.color.rgb = GREY

# ── Save ─────────────────────────────────────────────────────────────────────
output_path = '/Users/johan/Documents/_CLAUDE CODE/Church Election App/manual.docx'
doc.save(output_path)
print(f'Saved: {output_path}')
