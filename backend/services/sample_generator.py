import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from config import DATA_DIR

SAMPLE_PDF_PATH = DATA_DIR / "Andheri_Lease_Agreement.pdf"

SAMPLE_CLAUSES = [
    {
        "num": "1.1",
        "title": "Demised Premises & Term",
        "text": "The Lessor hereby grants and the Lessee hereby accepts the tenancy of Flat No. 804, Sea Breeze Apartments, Andheri West, Mumbai 400053, for a fixed tenure of 24 (twenty-four) continuous months commencing from 1st December 2026."
    },
    {
        "num": "2.1",
        "title": "Monthly Rent & Escalation",
        "text": "The Lessee shall pay a monthly lease rent of INR 40,000 (Forty Thousand Rupees) payable in advance on or before the 5th day of every English calendar month. The rent shall escalate by 10% after completion of 12 months."
    },
    {
        "num": "3.1",
        "title": "Security Deposit",
        "text": "The Lessee has deposited an interest-free refundable security deposit of INR 2,40,000 (equivalent to 6 months rent) with the Lessor, acknowledgment whereof the Lessor hereby admits."
    },
    {
        "num": "4.3",
        "title": "Maintenance Charges & Society Dues",
        "text": "The Lessee shall pay monthly society maintenance of INR 4,500 directly to the Sea Breeze Co-operative Housing Society office. Water charges, electricity consumption bills, and piped gas dues shall be paid directly by the Lessee based on actual meter readings."
    },
    {
        "num": "6.1",
        "title": "Use of Premises & Non-Subletting",
        "text": "The Demised Premises shall be used exclusively for residential purposes by the Lessee and immediate family. The Lessee shall not assign, underlet, transfer, or part with possession of the premises to any third party."
    },
    {
        "num": "8.2",
        "title": "Lock-in Period & Early Termination Penalty",
        "text": "Tenant shall not terminate this agreement before 24 months. Early exit will attract a penalty equal to 6 months rent, irrespective of notice period served. In the event of breach, the entire security deposit shall stand forfeited."
    },
    {
        "num": "12.1",
        "title": "Security Deposit Refund Timeline",
        "text": "Security deposit of INR 2,40,000 shall be held without interest and refunded within 90 days of vacating after adjusting unpaid utility dues and reasonable repainting charges."
    },
    {
        "num": "15.2",
        "title": "Alterations & Structural Changes",
        "text": "The Lessee shall not make any major structural changes, alterations, or drill load-bearing pillars without prior written approval from the Lessor and Housing Society."
    },
    {
        "num": "19.1",
        "title": "Stamp Duty & Registration Costs",
        "text": "The stamp duty, e-registration fee, and documentation charges under the Maharashtra Rent Control Act shall be borne equally (50:50) by the Lessor and the Lessee."
    }
]


def ensure_sample_pdf() -> Path:
    """Generate a clean legal PDF if not already present."""
    if SAMPLE_PDF_PATH.exists():
        return SAMPLE_PDF_PATH

    doc = SimpleDocTemplate(
        str(SAMPLE_PDF_PATH),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=colors.HexColor("#1E293B")
    )
    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#64748B")
    )
    clause_title_style = ParagraphStyle(
        'ClauseTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#334155")
    )
    clause_body_style = ParagraphStyle(
        'ClauseBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#475569")
    )

    story = [
        Paragraph("RESIDENTIAL LEAVE AND LICENSE AGREEMENT", title_style),
        Spacer(1, 4),
        Paragraph("Registered under Section 55 of Maharashtra Rent Control Act, 1999 • Andheri West, Mumbai", sub_style),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceBefore=5, spaceAfter=15),
        Paragraph("This Lease Agreement is executed on 1st December 2026 between Shri Rajesh V. Sharma (Lessor) and Shri A. Kumar (Lessee).", clause_body_style),
        Spacer(1, 12),
    ]

    for item in SAMPLE_CLAUSES:
        story.append(Paragraph(f"<b>Clause {item['num']} — {item['title']}</b>", clause_title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(item['text'], clause_body_style))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>IN WITNESS WHEREOF</b> the Lessor and the Lessee have subscribed their hands on the day and year first written above.", clause_body_style))

    doc.build(story)
    return SAMPLE_PDF_PATH
