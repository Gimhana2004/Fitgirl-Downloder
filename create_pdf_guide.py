#!/usr/bin/env python3
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf(filename="FitGirl_Downloader_User_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1e1e2e")
    ACCENT_BLUE = colors.HexColor("#2563eb")
    ACCENT_PURPLE = colors.HexColor("#7c3aed")
    TEXT_DARK = colors.HexColor("#1f2937")
    TEXT_MUTED = colors.HexColor("#4b5563")
    BG_LIGHT = colors.HexColor("#f3f4f6")
    SUCCESS = colors.HexColor("#059669")
    DANGER = colors.HexColor("#dc2626")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        alignment=1, # Center
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=ACCENT_BLUE,
        alignment=1,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=ACCENT_PURPLE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_DARK,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_DARK,
        leftIndent=15,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=PRIMARY
    )

    footer_style = ParagraphStyle(
        'Footer_Text',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11,
        textColor=TEXT_MUTED,
        alignment=1
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("FitGirl Multi-Part Downloader", title_style))
    elements.append(Paragraph("Complete User & Installation Guide (v4.2) • Fast Host & DataNodes Support", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE, spaceBefore=0, spaceAfter=14))

    # Overview Box
    overview_text = """
    <b>Welcome!</b> This tool is a high-speed multi-part download manager designed specifically for downloading split game archives (e.g. <code>.part01.rar</code>, <code>.part02.rar</code>) without manual captcha clicking, countdown waiting, or losing progress when shutting down your PC.
    """
    overview_table = Table([[Paragraph(overview_text, callout_style)]], colWidths=[532])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e0e7ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#93c5fd")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(overview_table)
    elements.append(Spacer(1, 10))

    # Key Features
    elements.append(Paragraph("🌟 Key Features", h1_style))
    features = [
        "<b>Multi-Day Resume:</b> Turn off your PC anytime. Downloads resume from the exact byte on disk without restarting from 0%.",
        "<b>1-by-1 Sequential Auto-Grab:</b> Resolves links one at a time in the active browser tab to ensure Cloudflare verification never freezes.",
        "<b>Dual Filehoster Support:</b> Fully automated for both Fast Host (FF) and DataNodes.",
        "<b>2-by-2 Controlled Concurrency:</b> Downloads up to 2 parts simultaneously and automatically advances to the next queue items.",
        "<b>Automatic Dead Link Detection:</b> Missing or 404 files are automatically flagged in bold red so you never get stuck.",
        "<b>Batch Right-Click Management:</b> Select multiple parts with Shift/Ctrl and Start, Pause, or Remove in one click."
    ]
    for feat in features:
        elements.append(Paragraph(f"• {feat}", bullet_style))

    elements.append(Spacer(1, 8))

    # Step-by-Step Guide
    elements.append(Paragraph("🚀 3-Step Quick Start Guide", h1_style))

    # Step 1
    elements.append(Paragraph("Step 1: Install Browser Extension (One-time Setup)", h2_style))
    elements.append(Paragraph("1. Install <b>Tampermonkey</b> in Chrome, Brave, Edge, or Opera (Search Chrome Web Store).", bullet_style))
    elements.append(Paragraph("2. In Tampermonkey, click <b>Create a new script</b>, paste the contents of <code>datanodes_autoclicker.user.js</code>, and press <b>Ctrl + S</b> (or Cmd + S) to Save.", bullet_style))

    # Step 2
    elements.append(Paragraph("Step 2: Launch the Downloader Application", h2_style))
    elements.append(Paragraph("• <b>On Windows:</b> Double-click <code>FitGirlDownloader.exe</code> (No Python required).", bullet_style))
    elements.append(Paragraph("• <b>On macOS:</b> Double-click <code>Run_Mac.command</code> or run <code>python3 downloader.py</code> in Terminal.", bullet_style))

    # Step 3
    elements.append(Paragraph("Step 3: Resolve & Download", h2_style))
    elements.append(Paragraph("1. Go to any FitGirl repack page and copy the links under <b>Filehoster: F-Fast</b> or <b>DataNodes</b>.", bullet_style))
    elements.append(Paragraph("2. Paste them into the top text box in the Downloader app (or click the floating <i>'Send Parts to Downloader'</i> button on the webpage).", bullet_style))
    elements.append(Paragraph("3. Click the purple button <b>🌐 Start 1-by-1 Auto-Grab</b>.", bullet_style))
    elements.append(Paragraph("4. The browser opens tabs sequentially, grabs the direct links, sends them straight to the queue, and closes each tab automatically. Downloads start immediately!", bullet_style))

    elements.append(Spacer(1, 10))

    # Pro Tips & Shortcuts Table
    elements.append(Paragraph("💡 Helpful Tips & Shortcuts", h1_style))
    tip_data = [
        [Paragraph("<b>Feature</b>", body_style), Paragraph("<b>How to Use It</b>", body_style)],
        [
            Paragraph("<b>Multi-Select</b>", bullet_style),
            Paragraph("Hold <b>Ctrl</b> (or <b>Cmd</b>) or <b>Shift</b> and click multiple parts in the table. Right-click to Pause, Resume, or Remove them all at once.", body_style)
        ],
        [
            Paragraph("<b>Expired Links</b>", bullet_style),
            Paragraph("If a 24-hour direct link expires, right-click the row and choose <b>🔄 Refresh Expired Link</b>. Paste the fresh link to resume without losing downloaded bytes.", body_style)
        ],
        [
            Paragraph("<b>Dead Links (404)</b>", bullet_style),
            Paragraph("If a part was removed from the hoster, it is marked <b>❌ File Not Found</b> in red, and the auto-grabber moves to the next part automatically.", body_style)
        ],
        [
            Paragraph("<b>Change Folder</b>", bullet_style),
            Paragraph("Click <b>📁 Browse</b> to select any external hard drive or folder where you want your game archives saved.", body_style)
        ]
    ]

    tip_table = Table(tip_data, colWidths=[140, 392])
    tip_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(tip_table)

    elements.append(Spacer(1, 18))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#d1d5db"), spaceBefore=0, spaceAfter=8))
    elements.append(Paragraph("FitGirl Multi-Part Downloader • Open-Source Community Release • Created by Pasindu Gimhana", footer_style))

    doc.build(elements)
    print(f"PDF successfully generated at: {os.path.abspath(filename)}")

if __name__ == "__main__":
    generate_pdf()
