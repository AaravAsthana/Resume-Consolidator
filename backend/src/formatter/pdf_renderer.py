import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Image, FrameBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def render_pdf(parsed: dict, output_path: str):
    styles = getSampleStyleSheet()
    blue_body = ParagraphStyle(
        'BlueBody', parent=styles['BodyText'], textColor=colors.white, fontSize=9
    )
    white_body = ParagraphStyle(
        'WhiteBody', parent=styles['BodyText'], textColor=colors.black, fontSize=10
    )
    title_style = ParagraphStyle(
        'Title', parent=styles['Title'], textColor=colors.black, fontSize=16, spaceAfter=8
    )
    heading_style = ParagraphStyle(
        'Heading', parent=styles['Heading2'], textColor=colors.HexColor('#333366'), fontSize=12, spaceAfter=6
    )

    doc = BaseDocTemplate(output_path, pagesize=letter,
        leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)

    width, height = letter
    mid = width * 0.35

    # Frames
    left = Frame(0, 0, mid, height, leftPadding=16, rightPadding=16, topPadding=24, bottomPadding=24)
    right = Frame(mid, 0, width-mid, height, leftPadding=24, rightPadding=24, topPadding=24, bottomPadding=24)
    full = Frame(0, 0, width, height, leftPadding=36, rightPadding=36, topPadding=36, bottomPadding=36)

    # Background color for left column
    def draw_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#5594D4"))  # deep blue
        canvas.rect(0, 0, mid, height, fill=1, stroke=0)
        canvas.restoreState()

    doc.addPageTemplates([
        PageTemplate(id='FirstPage', frames=[left, right], onPage=draw_background),
        PageTemplate(id='LaterPages', frames=[full])
    ])

    story = []

    # ─── LEFT SIDE ───────────────────────────────────────
    story.append(Paragraph("", styles['Normal']))  # Ensure we're in left frame

    # Image (if present)
    img_bytes = parsed.get("image_bytes")
    if img_bytes:
        img_path = os.path.splitext(output_path)[0] + "_img.png"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        story.append(Image(img_path, width=120, height=120))
        story.append(Spacer(1, 16))

    # About Me
    about_me = parsed.get("sections", {}).get("about_me", "")
    if about_me:
        story.append(Paragraph("About Me", heading_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph(about_me, blue_body))
        story.append(Spacer(1, 12))

    # Contact Info
    contact = parsed.get("contact", {})
    contact_lines = []
    if contact.get("email"):
        contact_lines.append(f"Email: {contact['email']}")
    if contact.get("phone"):
        contact_lines.append(f"Phone: {contact['phone']}")
    if contact.get("linkedin"):
        contact_lines.append(f"LinkedIn: {contact['linkedin']}")
    if contact.get("github"):
        contact_lines.append(f"GitHub: {contact['github']}")
    if contact_lines:
        story.append(Paragraph("Contact", heading_style))
        for line in contact_lines:
            story.append(Paragraph(line, blue_body))
        story.append(Spacer(1, 12))

    # References
    refs = parsed.get("sections", {}).get("references", "")
    if refs:
        story.append(Paragraph("References", heading_style))
        for r in refs.splitlines():
            story.append(Paragraph(r.strip(), blue_body))
        story.append(Spacer(1, 12))

    # Break to Right Column
    story.append(FrameBreak())

    # ─── RIGHT SIDE ──────────────────────────────────────
    story.append(Paragraph(parsed.get("full_name", ""), title_style))
    if parsed.get("current_job"):
        story.append(Paragraph(parsed["current_job"], heading_style))
    story.append(Spacer(1, 12))

    # Education & Experience from Gemini
    for key in ['education', 'experience']:
        entries = parsed.get("sections", {}).get(key, [])
        if entries:
            story.append(Paragraph(key.capitalize(), heading_style))
            for entry in entries:
                line = " • ".join(str(v) for v in entry.values() if v)
                story.append(Paragraph(line, white_body))
            story.append(Spacer(1, 12))

    # Skills
    skills = parsed.get("sections", {}).get("skills", [])
    if skills:
        story.append(Paragraph("Skills", heading_style))
        skill_line = " • ".join(skills)
        story.append(Paragraph(skill_line, white_body))
        story.append(Spacer(1, 12))

    # Miscellaneous (dynamic sections)
    misc = parsed.get("sections", {}).get("misc", {})
    for k, v in misc.items():
        story.append(Paragraph(k.replace('_', ' ').title(), heading_style))
        story.append(Paragraph(v, white_body))
        story.append(Spacer(1, 12))

    # Build PDF
    doc.build(story)
