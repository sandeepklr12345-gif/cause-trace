"""Generate a realistic sample deviation report (PDF) + a short email (.eml) for demos.

Run:  backend\\.venv\\Scripts\\python.exe tools\\make_sample_docs.py
Output goes to ./samples (git-ignored; keep it private per the assignment rules).
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "samples"
OUT.mkdir(exist_ok=True)

HEADER = [
    ("Deviation No", "DEV-2026-0412"),
    ("Title", "Residual isopropanol above limit after final drying"),
    ("Deviation Type", "OOS - residual solvent (GC-HS)"),
    ("Date Detected", "17-Sep-2026"),
    ("Detected By", "QC Analyst, Chemical Laboratory"),
    ("Department", "API Manufacturing, Block B"),
    ("Product", "Atorvastatin Calcium API"),
    ("Grade", "USP"),
    ("Batch No", "ATC260915A"),
    ("Process Stage", "Final drying (vacuum tray dryer)"),
    ("Equipment", "Vacuum tray dryer VTD-204; vacuum pump VP-204"),
    ("Batch Size", "250 kg"),
    ("Affected Quantity", "250 kg (10 HDPE drums)"),
    ("Manufacturing Date", "15-Sep-2026"),
    ("Test Result", "Isopropanol 5,800 ppm (limit NMT 5,000 ppm)"),
]

DESCRIPTION = (
    "During release testing of batch ATC260915A, residual isopropanol was found at 5,800 ppm against a "
    "specification of NMT 5,000 ppm (ICH Q3C Class 3). The batch had completed final drying in vacuum tray "
    "dryer VTD-204 on 16-Sep-2026. The result was confirmed on re-injection of the same preparation."
)
IMMEDIATE = (
    "The batch (10 drums) was placed on QA hold and labelled 'Quarantine'. Retention sample secured. "
    "Dispatch of ATC260915A was stopped. No downstream batch has consumed this lot."
)
OBS = [
    "Drying cycle was scheduled for 12 h at 60 C under vacuum NMT 50 mbar. The operator ended the cycle at 9 h after the in-process LOD read 0.4% (limit NMT 0.5%).",
    "Batch record shows a tray bed depth of about 4 cm. The validated bed depth range is not stated in the batch record.",
    "Only a start-of-cycle gauge reading is recorded in the batch record; no in-cycle readings were noted.",
    "GC-HS system suitability passed for the analytical run (RSD 1.2%).",
    "The previous batch ATC260911B was dried in the same dryer VTD-204 without any residual solvent OOS.",
]

styles = getSampleStyleSheet()
body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10, leading=14)
h = ParagraphStyle("h", parent=styles["Heading2"], fontSize=12, spaceBefore=10)


def make_pdf(path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    s = [Paragraph("DEVIATION / INCIDENT REPORT", styles["Title"]),
         Paragraph("Sunrise Pharma Ltd - API Division - Quality Assurance", styles["Normal"]), Spacer(1, 8)]
    t = Table([[Paragraph(f"<b>{k}:</b>", body), Paragraph(v, body)] for k, v in HEADER],
              colWidths=[42 * mm, 130 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s += [t, Paragraph("Description:", h), Paragraph(DESCRIPTION, body),
          Paragraph("Immediate Actions:", h), Paragraph(IMMEDIATE, body), Paragraph("Observations:", h)]
    s += [Paragraph("- " + o, body) for o in OBS]
    doc.build(s)


def make_eml(path: Path) -> None:
    lines = [
        "From: qc.lab@sunrisepharma.example", "To: qa.api@sunrisepharma.example",
        "Subject: URGENT - Metformin HCl API batch MFH260712A - assay low", "Date: Mon, 14 Sep 2026 09:12:00 +0530", "",
        "Product: Metformin Hydrochloride API", "Grade: IP/BP", "Batch No: MFH260712A",
        "Process Stage: Final blending (cone blender)", "Batch Size: 500 kg", "Test Result: Assay 97.1% (limit 98.0-102.0%)", "",
        "Description: Assay for the above batch came in low on two independent preparations. Blend uniformity samples were not taken as per plan.",
        "", "Observations:", "- Blender run time recorded as 14 min against 20 min in the batch record.",
        "- Blender BL-12 had a gearbox noise complaint logged last week.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    make_pdf(OUT / "DEV-2026-0412_residual_solvent.pdf")
    make_eml(OUT / "assay_low_email.eml")
    print("wrote", [p.name for p in OUT.iterdir()])
