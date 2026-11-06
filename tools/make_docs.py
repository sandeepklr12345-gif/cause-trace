"""Build the CauseTrace PDFs (User Manual + Interview Guide) with reportlab.

    backend\\.venv\\Scripts\\python.exe tools\\make_docs.py
Output: docs/CauseTrace_User_Manual.pdf, docs/CauseTrace_Interview_Guide.pdf
Only plain WinAnsi characters are used (no arrows/checkmarks) so the built-in fonts render everything.
"""
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)

OUT = Path(__file__).resolve().parent.parent / "docs"
OUT.mkdir(exist_ok=True)

TEAL = colors.HexColor("#0f6e6e")
TEAL_SOFT = colors.HexColor("#e0f2f1")
INK = colors.HexColor("#17212f")
MUTED = colors.HexColor("#647489")
LINE = colors.HexColor("#d5dce6")
AMBER = colors.HexColor("#a15c00")
AMBER_SOFT = colors.HexColor("#fff1d6")
BLUE = colors.HexColor("#1d5fd1")
BLUE_SOFT = colors.HexColor("#e6eefc")
GREEN = colors.HexColor("#17783c")
GREEN_SOFT = colors.HexColor("#e0f5e8")
RED = colors.HexColor("#b3261e")
RED_SOFT = colors.HexColor("#fde8e6")

W, H = A4
MARGIN = 18 * mm
CONTENT_W = W - 2 * MARGIN

base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.6, leading=14, textColor=INK, alignment=TA_LEFT)
S = {
    "p": base,
    "small": ParagraphStyle("small", parent=base, fontSize=8.4, leading=11.5, textColor=MUTED, spaceAfter=5),
    "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=TEAL,
                         spaceBefore=4, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=INK,
                         spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "h3": ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=TEAL,
                         spaceBefore=6, spaceAfter=2, keepWithNext=1),
    "cell": ParagraphStyle("cell", parent=base, fontSize=8.5, leading=11.2),
    "cellb": ParagraphStyle("cellb", parent=base, fontName="Helvetica-Bold", fontSize=8.5, leading=11.2),
    "th": ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white),
    "bul": ParagraphStyle("bul", parent=base, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=7.8, leading=10.2, textColor=INK),
}


def P(t, s="p"):
    return Paragraph(t, S[s])


def bullets(items, style="bul"):
    return [Paragraph(t, S[style], bulletText="•") for t in items]


def table(rows, widths, head=True, zebra=True):
    data = []
    for ri, row in enumerate(rows):
        r = []
        for ci, c in enumerate(row):
            if isinstance(c, str):
                st = "th" if (head and ri == 0) else ("cellb" if ci == 0 else "cell")
                r.append(Paragraph(c, S[st]))
            else:
                r.append(c)
        data.append(r)
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), TEAL)]
    if zebra:
        for i in range(1 if head else 0, len(data)):
            if (i % 2) == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f8fa")))
    t.setStyle(TableStyle(style))
    return t


def callout(text, fg=TEAL, bg=TEAL_SOFT, title=None):
    inner = []
    if title:
        inner.append(Paragraph(f"<b>{title}</b>", ParagraphStyle("ct", parent=base, textColor=fg, fontSize=9.6)))
    inner.append(Paragraph(text, ParagraphStyle("cb", parent=base, fontSize=9.2, leading=13)))
    t = Table([[inner]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, fg),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def code(text):
    t = Table([[Preformatted(text.strip("\n"), S["code"])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f4f8")), ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ----------------------------------------------------------------- diagram helpers

def box(d, x, y, w, h, lines, fill=TEAL_SOFT, stroke=TEAL, size=7.6, bold_first=True, text=INK):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=stroke, strokeWidth=0.9))
    n = len(lines)
    step = size + 2.2
    top = y + h / 2 + (n - 1) * step / 2 - size * 0.32
    for i, ln in enumerate(lines):
        f = "Helvetica-Bold" if (i == 0 and bold_first) else "Helvetica"
        d.add(String(x + w / 2, top - i * step, ln, fontName=f, fontSize=size, fillColor=text, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, color=MUTED, dashed=False, head=4.5):
    import math
    ln = Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1)
    if dashed:
        ln.strokeDashArray = [3, 2]
    d.add(ln)
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - 0.45), y2 - head * math.sin(a - 0.45))
    p2 = (x2 - head * math.cos(a + 0.45), y2 - head * math.sin(a + 0.45))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=color, strokeColor=color, strokeWidth=0.5))


def polyline(d, pts, color=MUTED, dashed=False):
    for (a, b), (c, e) in zip(pts, pts[1:-1]):
        ln = Line(a, b, c, e, strokeColor=color, strokeWidth=1)
        if dashed:
            ln.strokeDashArray = [3, 2]
        d.add(ln)
    (a, b), (c, e) = pts[-2], pts[-1]
    arrow(d, a, b, c, e, color, dashed)


def label(d, x, y, t, size=6.6, color=MUTED, anchor="middle"):
    d.add(String(x, y, t, fontName="Helvetica", fontSize=size, fillColor=color, textAnchor=anchor))


def diagram_business():
    d = Drawing(CONTENT_W, 118)
    bw, bh, y = 140, 46, 56
    xs = [0, 168, 336]
    texts = [["1  Deviation", "identified and recorded"], ["2  Root Cause Analysis", "5 Whys, fishbone, evidence"],
             ["3  CAPA", "correct, prevent, verify"]]
    fills = [(AMBER_SOFT, AMBER), (BLUE_SOFT, BLUE), (GREEN_SOFT, GREEN)]
    for x, t, (f, s) in zip(xs, texts, fills):
        box(d, x, y, bw, bh, t, fill=f, stroke=s, size=8.4)
    arrow(d, xs[0] + bw, y + bh / 2, xs[1], y + bh / 2)
    arrow(d, xs[1] + bw, y + bh / 2, xs[2], y + bh / 2)
    sub = ["Ingest tool: report, email or text", "Hypothesize + critic + gap radar", "Plan node: linked CAPA + checks"]
    sub2 = ["fills the form, logs evidence", "AI suggests, a person confirms", "owner and due date set by people"]
    for x, a, b in zip(xs, sub, sub2):
        label(d, x + bw / 2, 38, a, 7, INK)
        label(d, x + bw / 2, 28, b, 7, MUTED)
    label(d, CONTENT_W / 2, 6, "What the quality team does (top) and what CauseTrace automates at each step (below)", 7, MUTED)
    label(d, CONTENT_W / 2, 108, "Real-world workflow", 8.4, TEAL)
    return d


def diagram_architecture():
    d = Drawing(CONTENT_W, 190)
    bw, bh = 100, 50
    ytop = 120
    xs = [0, 131, 262, 393]
    top = [(["Browser", "React + Redux Toolkit"], BLUE_SOFT, BLUE), (["FastAPI", "REST + SSE + uploads"], TEAL_SOFT, TEAL),
           (["LangGraph", "workflow + state"], TEAL_SOFT, TEAL), (["Groq", "gpt-oss-120b / 20b"], AMBER_SOFT, AMBER)]
    for x, (t, f, s) in zip(xs, top):
        box(d, x, ytop, bw, bh, t, fill=f, stroke=s, size=8.4)
    for i in range(3):
        arrow(d, xs[i] + bw, ytop + bh / 2 + 6, xs[i + 1], ytop + bh / 2 + 6)
        arrow(d, xs[i + 1], ytop + bh / 2 - 6, xs[i] + bw, ytop + bh / 2 - 6)
    for i, t in enumerate(["HTTP+SSE", "state", "JSON"]):
        label(d, xs[i] + bw + 15.5, ytop + bh / 2 + 12, t, 6, MUTED)
    box(d, xs[1], 30, bw, bh, ["PostgreSQL", "investigation (JSONB)", "audit, snapshots, chat"], fill=GREEN_SOFT, stroke=GREEN, size=7.6)
    box(d, xs[0], 30, bw, bh, ["pdfplumber", "PDF / .eml / .txt -> text"], fill=colors.HexColor("#f1f4f8"), stroke=MUTED, size=7.6)
    arrow(d, xs[1] + bw / 2, ytop, xs[1] + bw / 2, 30 + bh)
    arrow(d, xs[0] + bw / 2, 30 + bh, xs[1] + 18, ytop)
    label(d, xs[1] + bw / 2 + 4, 100, "read / write", 6.2, MUTED, "start")
    label(d, CONTENT_W / 2, 6, "Every AI change is validated, audited and stored in PostgreSQL before the UI shows it as saved", 7, MUTED)
    label(d, CONTENT_W / 2, 180, "System architecture", 8.4, TEAL)
    return d


def diagram_graph():
    d = Drawing(CONTENT_W, 232)
    # coordinates in a 480-wide frame
    bw, bh = 62, 22
    route = (4, 105, 50, 30)
    branches = {"ingest": 196, "edit": 160, "analyze": 124, "challenge": 88, "question": 52}
    bx = 92
    box(d, *route, ["route"], fill=BLUE_SOFT, stroke=BLUE, size=8)
    for name, cy in branches.items():
        box(d, bx, cy - bh / 2, bw, bh, [name], fill=colors.HexColor("#f1f4f8"), stroke=MUTED, size=7.6, bold_first=False)
        arrow(d, route[0] + route[2], route[1] + route[3] / 2, bx, cy)
    main_y = 160
    hx, cx, px, fx = 196, 292, 372, 442
    box(d, hx, main_y - 16, 78, 32, ["hypothesize", "5 Whys + 6M"], size=7.6)
    box(d, cx, main_y - 16, 62, 32, ["critic", "2nd model"], fill=AMBER_SOFT, stroke=AMBER, size=7.6)
    box(d, px, main_y - 16, 52, 32, ["plan", "gaps+CAPA"], size=7.2)
    box(d, fx, main_y - 16, 38, 32, ["finalize"], fill=GREEN_SOFT, stroke=GREEN, size=7.2)
    arrow(d, bx + bw, 196, hx, main_y + 6)
    arrow(d, bx + bw, 160, hx, main_y)
    arrow(d, bx + bw, 124, hx, main_y - 6)
    arrow(d, hx + 78, main_y, cx, main_y)
    arrow(d, cx + 62, main_y, px, main_y)
    arrow(d, px + 52, main_y, fx, main_y)
    # challenge shortcut: challenge -> critic (bottom), critic -> finalize
    polyline(d, [(bx + bw, 88), (cx + 31, 88), (cx + 31, main_y - 16)], color=AMBER, dashed=True)
    polyline(d, [(cx + 50, main_y - 16), (cx + 50, 112), (fx + 28, 112), (fx + 28, main_y - 16)], color=AMBER, dashed=True)
    label(d, 238, 78, "challenge: critic only", 6.4, AMBER)
    # question -> answer -> finalize
    box(d, 292, 40, 56, 22, ["answer"], fill=colors.HexColor("#f1f4f8"), stroke=MUTED, size=7.4, bold_first=False)
    arrow(d, bx + bw, 52, 292, 51)
    polyline(d, [(348, 51), (fx + 10, 51), (fx + 10, main_y - 16)])
    label(d, 240, 232 - 12, "LangGraph workflow (8 nodes)", 8.4, TEAL)
    label(d, 240, 8, "Solid = normal path. Dashed = challenge shortcut. An edit that only changes an identifier (e.g. batch number) goes straight to finalize.", 6.6, MUTED)
    return d


def diagram_ui():
    d = Drawing(CONTENT_W, 205)
    L = (0, 20, 300, 160)
    R = (312, 20, 162, 160)
    d.add(Rect(*L, rx=5, ry=5, fillColor=colors.HexColor("#f8fafc"), strokeColor=LINE))
    d.add(Rect(*R, rx=5, ry=5, fillColor=colors.HexColor("#f8fafc"), strokeColor=LINE))
    label(d, 150, 188, "LEFT: investigation form (the AI fills it)", 8, TEAL)
    label(d, 393, 188, "RIGHT: copilot", 8, TEAL)
    secs = [("1  Deviation details", 138, AMBER_SOFT, AMBER), ("2  Batch and process context", 118, AMBER_SOFT, AMBER),
            ("3  Investigation: 5 Whys / fishbone", 98, BLUE_SOFT, BLUE), ("4  Hypotheses + evidence chips", 78, BLUE_SOFT, BLUE),
            ("5  Evidence + gap radar", 58, colors.HexColor("#f1f4f8"), MUTED), ("6  CAPA plan (owner, due, accept)", 38, GREEN_SOFT, GREEN)]
    for t, y, f, s in secs:
        d.add(Rect(10, y, 280, 16, rx=3, ry=3, fillColor=f, strokeColor=s, strokeWidth=0.7))
        d.add(String(18, y + 5, t, fontName="Helvetica", fontSize=7.6, fillColor=INK))
    d.add(Rect(320, 128, 146, 44, rx=4, ry=4, fillColor=TEAL_SOFT, strokeColor=TEAL))
    d.add(String(393, 158, "Investigation health", fontName="Helvetica-Bold", fontSize=7.6, fillColor=INK, textAnchor="middle"))
    d.add(String(393, 146, "evidence sufficiency 62%", fontName="Helvetica", fontSize=7, fillColor=INK, textAnchor="middle"))
    d.add(Rect(330, 135, 126, 5, rx=2, ry=2, fillColor=colors.white, strokeColor=TEAL, strokeWidth=0.5))
    d.add(Rect(330, 135, 78, 5, rx=2, ry=2, fillColor=TEAL, strokeColor=TEAL, strokeWidth=0.5))
    d.add(Rect(320, 58, 146, 62, rx=4, ry=4, fillColor=colors.white, strokeColor=LINE))
    d.add(String(393, 100, "chat + live progress", fontName="Helvetica", fontSize=7.4, fillColor=MUTED, textAnchor="middle"))
    d.add(String(393, 88, "Extracting... Hypothesizing...", fontName="Helvetica", fontSize=6.8, fillColor=MUTED, textAnchor="middle"))
    d.add(String(393, 76, "Critiquing... Scoring...", fontName="Helvetica", fontSize=6.8, fillColor=MUTED, textAnchor="middle"))
    d.add(Rect(320, 28, 146, 24, rx=4, ry=4, fillColor=colors.white, strokeColor=LINE))
    d.add(String(393, 37, "[attach]  type a message...  [Send]", fontName="Helvetica", fontSize=6.8, fillColor=MUTED, textAnchor="middle"))
    label(d, 240, 6, "Amber = AI value waiting for your review. Green = confirmed or edited by a person. Dashed amber border = unreviewed.", 6.8, MUTED)
    return d


# ----------------------------------------------------------------- page templates

def make_doc(path, title, subtitle, kicker):
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=20 * mm,
                          bottomMargin=18 * mm, title=title, author="CauseTrace project", subject=subtitle)

    def cover(c, d):
        c.saveState()
        c.setFillColor(TEAL)
        c.rect(0, H - 118 * mm, W, 118 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN, H - 26 * mm, kicker.upper())
        c.setFont("Helvetica-Bold", 34)
        c.drawString(MARGIN, H - 56 * mm, "CauseTrace")
        c.setFont("Helvetica-Bold", 17)
        c.drawString(MARGIN, H - 70 * mm, title)
        c.setFont("Helvetica", 11)
        y = H - 82 * mm
        for ln in subtitle.split("\n"):
            c.drawString(MARGIN, y, ln)
            y -= 6 * mm
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8.5)
        c.drawString(MARGIN, 16 * mm, "Prepared 6 November 2026. Private to the project owner: the assignment forbids sharing code, samples or videos publicly.")
        c.restoreState()

    def later(c, d):
        c.saveState()
        c.setStrokeColor(LINE)
        c.line(MARGIN, H - 14 * mm, W - MARGIN, H - 14 * mm)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(TEAL)
        c.drawString(MARGIN, H - 11 * mm, "CauseTrace")
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawRightString(W - MARGIN, H - 11 * mm, title)
        c.drawRightString(W - MARGIN, 10 * mm, f"Page {d.page}")
        c.drawString(MARGIN, 10 * mm, "AI-assisted Root Cause Analysis for API manufacturing")
        c.restoreState()

    frame = Frame(MARGIN, 18 * mm, CONTENT_W, H - 38 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    cover_frame = Frame(MARGIN, 24 * mm, CONTENT_W, H - 150 * mm, id="c", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="cover", frames=[cover_frame], onPage=cover, autoNextPageTemplate="body"),
                          PageTemplate(id="body", frames=[frame], onPage=later)])
    return doc


# ================================================================= USER MANUAL

def build_manual():
    story = []
    # ---- cover content (sits below the teal band)
    story += [Spacer(1, 4), P("<b>What this document covers</b>", "h2")]
    story += bullets([
        "The problem statement CauseTrace answers, in plain words",
        "How to start the app and what every part of the screen does",
        "A minute-by-minute walkthrough of the product demo (Video 1)",
        "The workflow: the real-world quality process and the LangGraph pipeline that automates it",
        "The tech stack and what each piece contributes to the problem",
        "Troubleshooting and known limits",
    ])
    story += [Spacer(1, 8), callout(
        "CauseTrace is a working AI-assisted Root Cause Analysis (RCA) module for a pharmaceutical Active Pharmaceutical "
        "Ingredient (API) manufacturer. You give it an incident report or a chat message. The AI fills the investigation "
        "form, proposes evidence-backed causes, points out what evidence is missing, and drafts CAPA. A qualified person "
        "reviews, edits and confirms before anything is saved.", title="One-paragraph summary"), PageBreak()]

    # ---- 1 Problem statement
    story += [P("1. The problem statement", "h1")]
    story += [callout(
        "Pharmaceutical API manufacturers investigate quality incidents slowly and inconsistently. Evidence is scattered "
        "across PDFs and emails, causes are often written up as \"operator error\" without proof, and CAPA does not always "
        "trace back to a real root cause. Build an AI-powered RCA module where quality professionals feed in an incident "
        "document or text, the AI fills the investigation form and proposes evidence-backed causes, flags missing evidence "
        "and recommends CAPA, and the human reviews, edits and confirms before saving.",
        title="In three lines")]
    story += [P("What the assignment asks for", "h2")]
    story += [table([
        ["Requirement from the assignment", "How CauseTrace meets it"],
        ["Accept an incident document (PDF), pasted text or email",
         "Attach button and drag-and-drop for PDF, .eml and .txt, or paste text into the chat."],
        ["Use AI to extract information and populate the RCA form",
         "Ingest tool: the LLM returns structured JSON that fills the 20 form fields (10 deviation, 10 batch) and logs evidence, each with its source quote."],
        ["Support 5 Whys or fishbone analysis",
         "One causal model with two views: a 5 Whys chain and a fishbone grouped by the 6M categories (toggle in the UI)."],
        ["Identify potential root causes and contributing factors",
         "Hypotheses across the 6M categories, each linked to the evidence that supports or contradicts it."],
        ["Highlight missing evidence or information",
         "Gap radar: a prioritized list of missing records, and a live evidence-sufficiency score."],
        ["Provide CAPA recommendations with a short explanation",
         "Correction, Corrective and Preventive actions, each linked to a hypothesis with a rationale and an effectiveness check."],
        ["Let the user review and edit AI output before saving",
         "Every value is editable; accept one or all; confirm a root cause by name; save is blocked until a person confirms."],
        ["Do not fill the form manually as the primary workflow",
         "The form has no empty text boxes to type into. Data enters through the copilot panel only."],
        ["AI causes are suggestions until evidenced and confirmed",
         "Enforced in code: the AI can only mark a hypothesis suggested or supported. Only a named person can confirm."],
    ], [CONTENT_W * 0.38, CONTENT_W * 0.62])]
    story += [Spacer(1, 6), P("What the assignment does <b>not</b> ask for", "h3"),
              P("The demo video belongs to a Customer Complaint module. The assignment says not to build the Customer "
                "Complaint, Deviation or Change Control modules. The video is only a reference for the interaction "
                "pattern: a split screen where the AI panel on the right extracts, fills and edits the form on the left. "
                "No UI template is provided, so the screen design in this project is our own."), PageBreak()]

    # ---- 2 Quick start
    story += [P("2. Starting the app", "h1")]
    story += [P("You need Docker (for the database), Python 3.11 and Node. Run these from the project folder "
                "<font face='Courier'>CauseTrace</font>. Open three terminals.")]
    story += [P("Step 1: database", "h3"), code("docker compose up -d"),
              P("This starts PostgreSQL on port 5433 with the user, password and database already set in <font face='Courier'>backend/.env</font>.", "small")]
    story += [P("Step 2: backend (port 8000)", "h3"),
              code("cd backend\n.venv\\Scripts\\python -m uvicorn app.main:app --port 8000"),
              P("The tables are created automatically on first start. Check <font face='Courier'>http://localhost:8000/api/health</font>: "
                "it shows <b>mock</b> or the Groq model name.", "small")]
    story += [P("Step 3: frontend (port 5173)", "h3"), code("cd frontend\nnpm install\nnpm run dev"),
              P("Open <font face='Courier'>http://localhost:5173</font>.", "small")]
    story += [P("Mock AI or real AI", "h2")]
    story += [table([
        ["Mode", "How to switch", "When to use it"],
        ["Mock AI", "backend/.env: <b>MOCK_LLM=true</b>, restart the backend", "Rehearsing the demo, UI work, saving tokens. Answers are canned and tuned to the sample residual-solvent report."],
        ["Real AI (Groq)", "backend/.env: <b>MOCK_LLM=false</b> and your key in GROQ_API_KEY, restart the backend", "Recording the demo video and showing real extraction and reasoning."],
    ], [CONTENT_W * 0.17, CONTENT_W * 0.38, CONTENT_W * 0.45])]
    story += [Spacer(1, 6), callout(
        "Your Groq key allows 8,000 tokens per minute and 200,000 tokens per day for each model. One full analysis turn "
        "costs about 5 to 7 thousand tokens, so one model covers roughly 35 turns a day. Rehearse in mock mode and record "
        "with the real model. Leave about 30 seconds between turns on camera.", fg=AMBER, bg=AMBER_SOFT, title="Token budget")]

    # ---- 3 Screen guide
    story += [P("3. A tour of the screen", "h1"), diagram_ui(), Spacer(1, 6)]
    story += [P("The form on the left is read-only for typing. You do not type into empty boxes. You can click a value to "
                "correct it during review, and every correction is recorded.")]
    story += [table([
        ["Element", "What it means"],
        ["Amber badge: \"From document - review\"", "The AI took this value from your document (hover the badge to see the quote it came from). It waits for your review."],
        ["Amber badge: \"AI suggestion - review\"", "The AI inferred this (for example the Major classification). It is not stated in the source."],
        ["Green badge: \"Edited by you\"", "A person set or changed this value."],
        ["Tick button next to a value", "Accept this one AI value. \"Accept all N AI values\" accepts a whole section."],
        ["Pencil / click on a value", "Edit it. The change is saved and logged in the audit trail."],
        ["Highlight flash", "A field the AI just changed pulses briefly so you can see exactly what moved."],
        ["Investigation health card", "Evidence sufficiency (0 to 100), a readiness label, the open-gap summary and warnings from the AI reviewer."],
        ["Hypothesis status pills", "suggested (amber): no or weak evidence. supported (blue): more evidence for than against. confirmed (green): signed off by a named person."],
        ["Evidence chips (E1, E2...)", "The evidence items linked to a hypothesis or a why-step. Hover to read them. \"Not yet evidenced\" means nothing on file backs that step."],
        ["Top bar: Undo, Save investigation", "Undo reverses the last change, AI or manual. Save needs at least one person-confirmed root cause."],
    ], [CONTENT_W * 0.34, CONTENT_W * 0.66])]

    story += [P("The copilot panel", "h2")]
    story += bullets([
        "<b>Attach</b> a PDF, email (.eml) or text file, or drag it onto the panel. The text is extracted and sent through the same pipeline as a typed message.",
        "<b>Type</b> an incident description, a correction, or a new finding. The assistant decides whether it is a new report, an edit, or a question.",
        "<b>Quick buttons</b>: Analyze root cause, Challenge the reasoning, What's missing?, Suggest CAPA.",
        "<b>Live progress</b> shows each step as it runs, and the form updates after every step, not only at the end.",
    ])

    # ---- 4 Demo
    story += [P("4. The product demo, step by step", "h1")]
    story += [P("This is the script for Video 1 (5 to 8 minutes). Sample files are in the <font face='Courier'>samples</font> folder: "
                "<font face='Courier'>DEV-2026-0412_residual_solvent.pdf</font> (main demo) and "
                "<font face='Courier'>assay_low_email.eml</font> (optional second case). Create a new investigation with <b>+ New</b> first.")]
    steps = [
        ["Time", "You do", "What the viewer sees", "Say"],
        ["0:00", "Show the empty screen", "Split screen: empty form, copilot on the right", "The form cannot be typed into. The AI fills it."],
        ["0:30", "Attach the PDF report", "Progress: understanding, extracting, hypothesizing, critiquing, finding gaps. Fields fill in stages with a flash and amber badges.", "It extracted the form fields it found and logged the evidence. Hover a badge to see the source quote."],
        ["1:45", "Open the Investigation card, toggle 5 Whys and Fishbone", "A causal chain ending in a system-level cause, then the same causes grouped by Man, Machine, Material, Method, Measurement, Environment", "One model, two views. Steps with no evidence are marked."],
        ["2:45", "Scroll to Hypotheses and Gap radar", "Hypotheses with status pills and evidence chips. A prioritized list of missing records.", "Nothing is a conclusion yet. Each cause is a suggestion until it has evidence and a person confirms it."],
        ["3:30", "Type: \"Correction: the batch number is ATC260915B.\"", "Only the batch number flashes. The reply arrives in a couple of seconds because an identifier-only change skips the analysis steps.", "An edit patches only what you named and keeps everything else."],
        ["4:15", "Type: \"The dryer audit trail shows vacuum rose to 300 mbar about 3 hours into the cycle.\"", "New evidence appears, the vacuum hypothesis gains support, the vacuum-trend gap closes, the score goes up.", "Telling the AI what you found closes the gap."],
        ["5:00", "Click Challenge the reasoning", "The reviewer pass reports whether the chain stops at human error and extends it if so", "Operator error is a symptom. The AI must find the system cause."],
        ["5:45", "Review: Accept all AI values, edit one field, accept one CAPA, set owner and due date", "Badges turn green. CAPA shows type, linked hypothesis, rationale, effectiveness check.", "The person stays in control of every value."],
        ["6:45", "Confirm a hypothesis with your name and role, then Save investigation", "Status pill changes to Saved", "Only a named person can confirm. Save is blocked until then."],
        ["7:15", "Click Undo once", "The last change reverses", "Every AI and manual change is snapshotted and audited."],
    ]
    story += [table(steps, [CONTENT_W * 0.07, CONTENT_W * 0.27, CONTENT_W * 0.33, CONTENT_W * 0.33])]
    story += [Spacer(1, 6), callout(
        "Rehearse once in mock mode, then record with the real model. Keep at least 30 seconds between AI turns "
        "(talk while you wait) so the 8,000 tokens-per-minute limit never forces a visible pause. If the 5 Whys already "
        "reaches a system cause, the Challenge result will say so, and that is a valid demonstration too.",
        fg=AMBER, bg=AMBER_SOFT, title="Recording tip")]
    story += [P("Optional second case: email intake", "h3"),
              P("Attach <font face='Courier'>assay_low_email.eml</font> (a Metformin Hydrochloride API assay result). It shows that the same pipeline handles "
                "a different product, an email format, and a different process step (blending).")]
    story += [PageBreak()]

    # ---- 5 Workflow
    story += [P("5. The workflow", "h1"), P("5.1 The real-world process", "h2"), diagram_business(), Spacer(1, 4)]
    story += [P("A quality incident in API manufacturing is first recorded as a <b>deviation</b>. An investigation then looks for the "
                "<b>root cause</b> using evidence (batch records, logs, test data, interviews). The outcome drives <b>CAPA</b>: "
                "a correction for the affected batch, a corrective action that removes the cause, and a preventive action that stops it "
                "recurring elsewhere, each with a check that it worked. CauseTrace automates the paperwork at each step and keeps the "
                "judgment with the quality professional.")]
    story += [P("5.2 The AI pipeline (LangGraph)", "h2"), diagram_graph(), Spacer(1, 4)]
    story += [table([
        ["Node", "Job", "Model"],
        ["route", "Decides what the message is: new report, edit, analyze, challenge, or a question. Uses simple rules first, the model only when needed.", "gpt-oss-20b"],
        ["ingest", "Extracts the deviation and batch fields plus evidence items, with a quote for each field.", "gpt-oss-20b"],
        ["edit", "Returns only the fields you mentioned, new evidence, and which open gaps your message answers. Code applies the patch.", "gpt-oss-20b"],
        ["hypothesize", "Builds hypotheses across the 6M categories with evidence links and the 5 Whys chain.", "gpt-oss-120b"],
        ["critic", "Acts as a skeptical reviewer. If the chain stops at human error it rewrites it to system-level causes.", "gpt-oss-20b"],
        ["plan", "Lists missing evidence (gap radar) and drafts CAPA in one call.", "gpt-oss-120b"],
        ["finalize", "Computes the evidence-sufficiency score in code and writes the reply.", "no model"],
    ], [CONTENT_W * 0.14, CONTENT_W * 0.70, CONTENT_W * 0.16])]
    story += [P("5.3 The three tools from the assignment, as built", "h2")]
    story += [table([
        ["Assignment tool", "In CauseTrace", "What it guarantees"],
        ["Log (intake from a prompt)", "Ingest: pasted text or chat message becomes form fields, evidence, hypotheses, gaps, CAPA and a health score.", "Fields not in the text stay empty. Nothing is invented."],
        ["Edit (contextual update)", "Edit: a natural-language correction changes only the named fields, then the analysis is refreshed if the change matters.", "Other fields and human-confirmed items are preserved. Undo is available."],
        ["Document extraction", "Upload a PDF or email, extract text with pdfplumber, run Ingest, then keep editing by chat.", "Each value keeps the quote it came from."],
    ], [CONTENT_W * 0.22, CONTENT_W * 0.48, CONTENT_W * 0.30])]
    story += [P("5.4 Safety rules that live in code, not only in prompts", "h2")]
    story += bullets([
        "The AI can only set a hypothesis to <b>suggested</b> or <b>supported</b>. \"Supported\" means more supporting than contradicting evidence. Only a named person can set <b>confirmed</b>.",
        "A chain that ends at \"operator error\" or \"training\" is challenged by the critic and pushed to the system conditions behind it.",
        "AI-filled values stay amber until accepted. A person's values are never overwritten by a later AI pass.",
        "Evidence sufficiency is calculated in code: 40 percent from the amount of evidence (capped at 8 items), 30 percent from hypotheses that have evidence, 30 percent from closing high-priority gaps.",
        "Save is refused until at least one root cause is confirmed by a person.",
    ])

    # ---- 6 Tech stack
    story += [P("6. Tech stack and what each part contributes", "h1"), diagram_architecture(), Spacer(1, 6)]
    story += [table([
        ["Technology", "Role in the project", "Contribution to the problem"],
        ["React + Redux Toolkit", "The split-screen UI. Redux holds the investigation, per-field provenance and chat. A small thunk reads the server-sent event stream.",
         "Makes the AI's work visible: fields fill step by step, changed values flash, and review actions (accept, edit, confirm) are one click."],
        ["FastAPI (Python)", "REST endpoints for investigations, upload, review actions, save and undo, plus the streaming /chat endpoint.",
         "Keeps the AI behind a validated API, streams progress, and enforces rules such as \"save needs a confirmed root cause\"."],
        ["LangGraph", "Runs the multi-step workflow with a shared state, conditional routing and per-node updates.",
         "Turns one big prompt into small, checkable steps: extract, hypothesize, critique, plan. Lets the UI show each step and lets edits skip steps that are not needed."],
        ["Groq (gpt-oss-120b and 20b)", "Fast inference for the language model calls.",
         "Delivers structured JSON for extraction, causal reasoning and CAPA in seconds. Two models share the load because of Groq's per-model limits."],
        ["PostgreSQL (JSONB)", "Stores the investigation document, chat messages, field-level audit rows and undo snapshots.",
         "Gives traceability: who or what changed each field, from which source, and a way back."],
        ["Pydantic", "Schemas for the form and for every LLM output.",
         "Rejects malformed model output and lets the code clean and retry it."],
        ["pdfplumber and email parser", "Turn PDFs and .eml files into plain text.",
         "Makes unstructured incident documents usable by the extractor."],
    ], [CONTENT_W * 0.20, CONTENT_W * 0.38, CONTENT_W * 0.42])]
    story += [P("Why these choices were forced or made", "h3")]
    story += bullets([
        "React + Redux, FastAPI, LangGraph + Groq, and PostgreSQL or MySQL are mandatory in the assignment.",
        "The brief names llama-3.3-70b-versatile, but Groq no longer serves it to this key, so the app uses gpt-oss models (the brief allows any reliable supported model).",
        "PostgreSQL was chosen over MySQL for its JSONB column, which suits a document that is patched field by field.",
    ])

    # ---- 7 Troubleshooting
    story += [P("7. Troubleshooting", "h1")]
    story += [table([
        ["Symptom", "Likely cause", "Fix"],
        ["Red banner: cannot reach the backend on :8000", "Backend not running", "Start it (step 2). Check /api/health."],
        ["Backend crashes on start with a database error", "Postgres container not running", "docker compose up -d, then restart the backend."],
        ["Health shows \"mock\" but you wanted the real model", "MOCK_LLM is true or the key is empty", "Set MOCK_LLM=false, check the key is in backend/.env, restart the backend."],
        ["A turn takes 30 to 60 seconds", "Groq per-minute token limit", "Wait. Space turns by 30 seconds. The app retries automatically."],
        ["Error: daily token limit reached on every model", "200,000 tokens/day per model used", "Switch to mock mode, wait for the window to reset, or use another key."],
        ["Upload says no text found", "Scanned, image-only PDF", "Use a text PDF, an email, or paste the text. OCR is not included."],
        ["Save investigation is greyed out or refused", "No confirmed root cause yet", "Confirm a hypothesis with your name and role first."],
        ["Port 5173 or 8000 already in use", "Old server still running", "Stop the old process or change the port."],
    ], [CONTENT_W * 0.33, CONTENT_W * 0.27, CONTENT_W * 0.40])]
    story += [P("8. Known limits (said plainly)", "h1")]
    story += bullets([
        "One user, no login, no electronic signature. A real GMP system would need access control and audit-grade e-signatures (for example 21 CFR Part 11). Here, confirmation records a name and role only.",
        "The recurrence check against past deviations is not built.",
        "No OCR for scanned PDFs. Tables inside PDFs are read as text.",
        "Database tables are created at start-up, with no migration tool. Fine for this scope.",
        "Mock mode returns canned answers tuned to the sample report. It proves the pipeline, not the reasoning.",
        "AI output can still be wrong. That is why every cause is a suggestion until a person confirms it.",
    ])
    doc = make_doc(OUT / "CauseTrace_User_Manual.pdf", "User Manual", "AI-assisted Root Cause Analysis for API manufacturing\nProblem, demo, workflow and tech stack", "AI Product Engineer Challenge")
    doc.build(story)


# ================================================================= INTERVIEW GUIDE

def qa(q, a):
    return KeepTogether([P(f"<b>Q. {q}</b>", "p"), P(a, "p"), Spacer(1, 4)])


def build_interview():
    s = []
    s += [Spacer(1, 4), P("<b>How to use this guide</b>", "h2")]
    s += bullets([
        "Read the 60-second pitch out loud until it feels natural.",
        "Learn the eight focus areas in order. Each one lists what to explain, where the code is, and likely questions with short answers.",
        "Practice the live-change drills. The brief says you must be able to explain or modify the code in the interview.",
        "Be ready to say what is not built. Saying it first sounds confident, not weak.",
    ])
    s += [Spacer(1, 6), callout(
        "\"I built CauseTrace, an AI RCA module for API manufacturing. You give it an incident report and the AI fills the "
        "investigation form, proposes root-cause hypotheses linked to evidence, shows what evidence is missing, and drafts "
        "CAPA. The key design idea is trust: the AI can only suggest, every value shows where it came from, a second "
        "model pass challenges 'operator error' conclusions, and only a named person can confirm a root cause. "
        "It runs on React and Redux, FastAPI, LangGraph with Groq, and PostgreSQL.\"", title="Your 60-second pitch"), PageBreak()]

    s += [P("Focus areas, ranked by how likely they are to come up", "h1")]
    s += [table([
        ["#", "Area", "Why interviewers care", "Your headline"],
        ["1", "LangGraph design", "It is the core of the mandatory stack", "Small nodes with one job, a router, conditional edges, streamed updates"],
        ["2", "Trust and safety in code", "Pharma: wrong answers have consequences", "Guardrails are enforced by code, not by hoping the prompt works"],
        ["3", "Structured output reliability", "LLMs break JSON in practice", "Pydantic schemas, cleaning, one corrective retry"],
        ["4", "Rate limits and cost", "Real constraint you hit and solved", "8k tokens/min, 200k/day: model split, fallback, token budgeting"],
        ["5", "Data model and audit", "Traceability is a GMP idea", "JSONB document, field-level audit, snapshots for undo"],
        ["6", "Streaming UX and Redux", "Frontend half of the stack", "SSE over fetch, node events, state diff drives highlights"],
        ["7", "Domain knowledge", "Shows you researched the workflow", "Deviation, RCA, CAPA, 5 Whys, 6M, human error is not a root cause"],
        ["8", "Limits and next steps", "Judgment and honesty", "No auth or e-signature, no recurrence check, no OCR"],
    ], [CONTENT_W * 0.05, CONTENT_W * 0.22, CONTENT_W * 0.30, CONTENT_W * 0.43])]

    # 1
    s += [P("1. LangGraph design", "h1")]
    s += [P("<b>Explain:</b> a graph of eight nodes shares one state (the investigation, the message, the intent). "
            "<font face='Courier'>route</font> picks a path. Ingest and edit feed the analysis chain "
            "<font face='Courier'>hypothesize, critic, plan, finalize</font>. Challenge runs only the critic. A question goes to "
            "<font face='Courier'>answer</font>. The chat endpoint streams each node's update so the UI can show progress and "
            "fill the form step by step."),
          P("<b>Where:</b> <font face='Courier'>backend/app/ai/graph.py</font> (wiring), <font face='Courier'>nodes.py</font> (node code), "
            "<font face='Courier'>routers/chat.py</font> (streaming).", "small")]
    s += [qa("Why a graph and not one big prompt?",
             "Small steps are easier to validate, retry, test and explain. Each step has its own schema and model. The user sees real progress, "
             "and shortcuts are possible: a corrected batch number skips the three analysis calls, and Challenge runs only the critic.")]
    s += [qa("How does the edit tool keep the other fields intact?",
             "The model never returns the whole form. It returns an EditPlan with only the changed paths, new evidence and any gaps it answers. "
             "Code checks each path against an allowlist and applies it with <font face='Courier'>set_field</font>. Everything else is untouched. "
             "The change is diffed into audit rows and a snapshot is taken first, so it can be undone.")]
    s += [qa("How does routing work?",
             "Rules first: a document means ingest, a quick-action button means that action, an empty investigation means ingest. Only otherwise does a small "
             "model classify the message. If the investigation already exists, an \"ingest\" answer is coerced to \"edit\", because new facts typed in chat are edits.")]
    s += [qa("What state does the graph carry, and where is it stored?",
             "The state holds the investigation JSON, the user message, the optional document text, the intent and a reply. It is rebuilt for each request from the "
             "database. After the graph finishes, the final JSON is validated, diffed against the original and saved. There is no hidden state between turns.")]

    # 2
    s += [PageBreak(), P("2. Trust and safety enforced in code", "h1")]
    s += [P("<b>Explain:</b> prompts tell the model the rules, but code does not trust the model. "
            "<font face='Courier'>merge.sanitize</font> runs after every AI step."),
          P("<b>Where:</b> <font face='Courier'>backend/app/ai/merge.py</font>, <font face='Courier'>prompts.py</font>, "
            "<font face='Courier'>routers/investigations.py</font>.", "small")]
    s += [table([
        ["Rule", "How it is enforced"],
        ["The AI cannot confirm a root cause", "sanitize derives status itself: supported only if evidence for > evidence against, otherwise suggested. Confirmed is only reachable through the confirm endpoint, which needs a name."],
        ["No invented evidence links", "Evidence ids the model returns that do not exist are dropped."],
        ["Human work is never overwritten", "Confirmed, rejected and user-edited hypotheses and accepted CAPA are protected during re-analysis. A person's field values are not overwritten by an AI pass."],
        ["Operator error is not a root cause", "The critic (a separate call, by a different model from the one that wrote the chain) rewrites chains ending in human error or training."],
        ["Unverified steps are labeled", "The prompt requires evidence ids per why-step or a \"Possible:\" prefix; the UI shows \"Not yet evidenced\"."],
        ["Score is explainable", "Evidence sufficiency is a code formula, not a number the model makes up."],
        ["Saving needs a person", "The save endpoint returns an error until a hypothesis is confirmed by a named person."],
    ], [CONTENT_W * 0.30, CONTENT_W * 0.70])]
    s += [Spacer(1, 4), qa("How do you stop the AI from hallucinating a root cause?",
                           "I cannot stop the model from guessing, so the design assumes it will. Causes start as suggestions. A claim needs evidence ids that exist. "
                           "Support is counted by code. A skeptical second pass challenges weak chains. And a person must confirm before anything is saved. "
                           "I also found one real case: the model called a hypothesis \"supported\" because evidence mentioned the vacuum <i>specification</i>, "
                           "so I tightened the prompt to say a parameter mention is not support.")]
    s += [qa("Why does a different model act as critic?",
             "A model reviewing its own text tends to agree with it. Using a separate call with a reviewer prompt, and a different model where available, "
             "gives a more independent check. It is also cheap: the critic usually returns a few hundred tokens.")]

    # 3
    s += [P("3. Structured output reliability", "h1")]
    s += [P("<b>Explain:</b> every model call goes through one function, <font face='Courier'>structured_call</font>. It sends the prompt plus a compact "
            "JSON Schema, asks for JSON mode, validates with Pydantic, and retries once with the validation error if it fails."),
          P("<b>Where:</b> <font face='Courier'>backend/app/ai/llm.py</font>, <font face='Courier'>schemas.py</font>.", "small")]
    s += bullets([
        "<b>Cleaning:</b> gpt-oss sometimes leaves stray empty strings or fragments inside arrays of objects. The parser drops them instead of spending a retry.",
        "<b>Tolerant fields:</b> validators turn \"H1 (Method)\" or [\"H1\",\"H2\"] into a clean id, so a small format drift does not fail the whole call.",
        "<b>Lenient then strict:</b> the model fills lenient shapes (for example evidence without an id). Code converts them to strict records and assigns ids.",
        "<b>Mock mode:</b> the same function returns canned data when no key is set, so the pipeline can be tested without the model.",
    ])
    s += [qa("Tell me about a bug you found while integrating the model.",
             "The title and description fields came back empty. The cause was my own schema-compaction helper, which removed every key named title or "
             "description to save tokens, including the <i>field names</i> of the form. The model never saw those fields. I fixed it by keeping keys under "
             "<font face='Courier'>properties</font>. A good lesson in checking raw model output, not only final results.")]
    s += [qa("Why JSON mode with a schema in the prompt rather than function calling?",
             "It worked reliably with the gpt-oss models on Groq, kept one code path for all models, and let me measure and trim the schema tokens. "
             "With more time I would test Groq's strict JSON-schema mode.")]

    # 4
    s += [PageBreak(), P("4. Rate limits, cost and model strategy", "h1")]
    s += [P("<b>Explain:</b> this is the engineering story that makes you credible, because you measured it."),
          P("<b>Where:</b> <font face='Courier'>config.py</font> (model tiers), <font face='Courier'>llm.py</font> (fallback), "
            "<font face='Courier'>tools/rate_limits.py</font>, <font face='Courier'>tools/model_bench.py</font>.", "small")]
    s += [table([
        ["Finding", "What I did"],
        ["llama-3.3-70b-versatile returned model_not_found for this key", "Listed available models, benchmarked the candidates, chose gpt-oss-120b and gpt-oss-20b."],
        ["Every model: 8,000 tokens per minute. First full run took about 117 seconds", "Measured per-call tokens, merged gaps and CAPA into one call, trimmed prompts and context, now about 15 to 20 seconds."],
        ["qwen: 1,000 output tokens/min. safeguard: 2,000 tokens/min", "Rejected both as too small."],
        ["200,000 tokens per day per model", "Automatic fallback to the other model on a daily-limit error, and a clear error if both are used up."],
        ["Back-to-back turns wait for the minute window", "Skip re-analysis when only an identifier changes. Use two models so two buckets share the load. Space turns when recording."],
        ["reasoning models are slow by default", "Set reasoning effort to low: about 1 to 3 seconds per call instead of 9 or more."],
    ], [CONTENT_W * 0.42, CONTENT_W * 0.58])]
    s += [Spacer(1, 4), qa("How would you scale this beyond a free tier?",
                           "Paid tier for higher limits, a request queue with per-model budgets, caching of unchanged stages, and running the critic only when the chain or evidence changed. "
                           "The tier setting means models can be swapped from configuration without code changes.")]

    # 5
    s += [P("5. Data model and auditability", "h1")]
    s += [P("<b>Explain:</b> four tables. <font face='Courier'>investigations</font> holds the whole investigation as one JSONB document; "
            "<font face='Courier'>messages</font> the chat; <font face='Courier'>audit_entries</font> one row per changed field or item (old value, new value, source, actor, tool, version); "
            "<font face='Courier'>snapshots</font> a full copy before each change for undo. Provenance (document, chat, AI inference, user) is stored per field inside the document."),
          P("<b>Where:</b> <font face='Courier'>models.py</font>, <font face='Courier'>services/persist.py</font>, <font face='Courier'>routers/investigations.py</font>.", "small")]
    s += [qa("Why one JSONB document instead of normalized tables?",
             "The investigation is read and written as one unit, and patch-style edits map naturally onto it. It kept the schema small for a 48-hour build. "
             "The cost is weaker cross-investigation queries. For recurrence search I would add a normalized hypotheses table or a search index.")]
    s += [qa("How does undo work?",
             "Before each AI action or manual change, a snapshot of the previous document is stored. Undo restores the latest snapshot, writes an audit entry for the reversal, "
             "and sets the status back to draft.")]

    # 6
    s += [PageBreak(), P("6. Streaming UX and Redux", "h1")]
    s += [P("<b>Explain:</b> the chat endpoint is a POST that streams server-sent events: <i>node</i> (a step started), <i>state</i> (the investigation after that step), "
            "<i>message</i> (the reply), <i>done</i>, <i>error</i>. EventSource cannot POST, so the client reads the stream with fetch and a small parser. "
            "A Redux slice holds the investigation; another holds the chat and progress."),
          P("<b>Where:</b> <font face='Courier'>frontend/src/api.js</font> (stream reader), <font face='Courier'>store/chatSlice.js</font>, "
            "<font face='Courier'>store/investigationSlice.js</font>, <font face='Courier'>components/</font>.", "small")]
    s += bullets([
        "<b>Highlights:</b> <font face='Courier'>changedPaths(old, new)</font> compares two versions and lists changed fields and items. Those get a CSS flash for about two seconds.",
        "<b>One review pattern:</b> <font face='Courier'>runAction(fn)</font> runs any human action (accept, edit, confirm, save, undo) and replaces the state with the server's answer.",
        "<b>Failure handling:</b> if the stream errors, the UI shows the message and reloads the saved investigation so it never shows half-applied state.",
        "<b>No manual primary input:</b> values appear as read-only text with an edit affordance, so the form is not typed into by default.",
    ])
    s += [qa("Why stream the state after every node?",
             "It shows the AI working, which builds trust in a demo and in real use. It also means a slow later step does not hide the extraction that already finished.")]

    # 7
    s += [P("7. Domain knowledge to speak confidently", "h1")]
    s += [table([
        ["Term", "Meaning in this project"],
        ["API", "Active Pharmaceutical Ingredient: the drug substance, made in reactors, dryers, blenders. Governed by ICH Q7 GMP for APIs."],
        ["Deviation", "Any departure from an approved procedure or specification. It is recorded, assessed and investigated."],
        ["OOS", "Out of Specification test result. In the sample: residual isopropanol 5,800 ppm against NMT 5,000 ppm (ICH Q3C Class 3 limit)."],
        ["RCA", "Root Cause Analysis: finding the underlying reason, using evidence. Tools: 5 Whys, fishbone (Ishikawa) with 6M categories."],
        ["6M", "Man, Machine, Material, Method, Measurement, Environment: the standard fishbone categories."],
        ["CAPA", "Corrective and Preventive Action. Correction fixes this batch, Corrective removes the cause, Preventive stops recurrence elsewhere. Each needs an effectiveness check."],
        ["Human error", "Not accepted as a root cause on its own. Regulators expect the system reason that allowed it (SOP design, alarms, maintenance, workload)."],
        ["ICH Q9 / Q10", "Quality risk management and the pharmaceutical quality system. They frame risk-based investigation and CAPA."],
        ["Data integrity (ALCOA+)", "Records must be attributable, legible, contemporaneous, original, accurate, and more. This is why provenance and the audit trail matter."],
    ], [CONTENT_W * 0.22, CONTENT_W * 0.78])]
    s += [Spacer(1, 4), qa("Why does your AI challenge \"operator error\"?",
                           "Because it is a symptom. If an operator stopped a cycle early, the useful question is why the process allowed it: an SOP that ends on a test that cannot detect the solvent, "
                           "a lax alarm, overdue maintenance. Fixing the system prevents recurrence. Retraining alone usually does not.")]

    # 8
    s += [PageBreak(), P("8. Limits and next steps", "h1")]
    s += [table([
        ["Not built / weak", "What you would do next"],
        ["No authentication, roles or real electronic signature", "Add login and roles, make confirmation a signed, time-stamped record (21 CFR Part 11 style)."],
        ["Recurrence check against past deviations", "Seed past investigations and add full-text or embedding search; show \"seen before\" in the gap radar."],
        ["No OCR for scanned PDFs", "Add an OCR step before extraction."],
        ["No evaluation set for AI quality", "Build a small labeled set of reports and score extraction accuracy and chain quality."],
        ["Tables created at start-up, no migrations", "Add Alembic migrations."],
        ["Recording relies on free-tier limits", "Paid tier or per-model budgeting and caching."],
        ["Mock mode is canned", "Keep it for tests only. Add automated tests around merge.py and the graph with recorded model outputs."],
    ], [CONTENT_W * 0.45, CONTENT_W * 0.55])]

    s += [P("Live-change drills", "h1")]
    s += [P("Practice each one once so you can do it calmly with someone watching.")]
    s += [table([
        ["If asked to...", "Where to change it"],
        ["Add a new form field (for example Supplier)", "schemas.py: add it to BatchContext. prompts.py: add the name to the \"Valid batch fields\" line. frontend DetailsSection.jsx: add it to the BATCH list. merge.BATCH_FIELDS (used to validate edits) updates itself from the model."],
        ["Change the model or reasoning level", "backend/.env: GROQ_MODEL, GROQ_MODEL_ALT, GROQ_MODEL_FAST, GROQ_REASONING_EFFORT. Restart the backend."],
        ["Add a new AI step (for example risk scoring)", "Write an async function in nodes.py, add a Pydantic output in schemas.py and a prompt in prompts.py, register it in graph.py, add a label in routers/chat.py."],
        ["Change how evidence sufficiency is scored", "merge.recompute_health: the weights are 40 / 30 / 30."],
        ["Make the critic run only when needed", "graph.py: add a conditional edge before critic, or check the chain in nodes.critic first."],
        ["Add an endpoint (for example export a report)", "routers/investigations.py: new route using get_inv and serialize."],
        ["Change when an edit triggers re-analysis", "nodes.py: the IMPACT_FIELDS set."],
        ["Block Save until all high gaps are closed", "routers/investigations.save: add a check on data.gaps."],
    ], [CONTENT_W * 0.36, CONTENT_W * 0.64])]

    s += [P("Numbers and facts worth memorizing", "h1")]
    s += [table([
        ["Fact", "Value"],
        ["LangGraph nodes", "8: route, ingest, edit, hypothesize, critic, plan, answer, finalize"],
        ["Models", "gpt-oss-120b (hypothesize, plan), gpt-oss-20b (route, ingest, edit, critic)"],
        ["Groq limits seen", "8,000 tokens/min and 200,000 tokens/day per model; 1,000 requests/day"],
        ["Typical timing (real model)", "15 to 20 seconds for a full document turn"],
        ["Tables", "investigations, messages, audit_entries, snapshots"],
        ["API surface", "create, list, get, upload, chat (SSE), edit field, accept, edit item, confirm, reject, save, undo, audit, health"],
        ["Health score weights", "40 percent evidence count (cap 8), 30 percent hypotheses with evidence, 30 percent high gaps closed"],
        ["Hypothesis states", "suggested, supported, confirmed (human only), rejected (human)"],
        ["Sample case", "Atorvastatin Calcium API, batch ATC260915A, isopropanol 5,800 ppm vs NMT 5,000, vacuum tray dryer VTD-204"],
    ], [CONTENT_W * 0.30, CONTENT_W * 0.70])]
    s += [Spacer(1, 6), callout(
        "If you get stuck in the interview: say what the code does at a high level, point to the file, then reason about the change out loud. "
        "Interviewers usually want to see how you think about the system, not perfect typing.", title="A calm fallback")]
    doc = make_doc(OUT / "CauseTrace_Interview_Guide.pdf", "Interview Guide", "What to explain, where the code is, and likely questions\nFocus areas, drills and honest limits", "AI Product Engineer Challenge")
    doc.build(s)


if __name__ == "__main__":
    build_manual()
    build_interview()
    print("wrote", [p.name for p in OUT.glob("*.pdf")])
