import os
import datetime
import zipfile
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_police_complaint_docx(report_facts, reports_folder):
    """
    Format for Police Complaint: Electrical Transformer Theft
    """
    doc = Document()
    
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("Format for Police Complaint: Electrical Transformer Theft\n")
    r_title.bold = True
    r_title.font.size = Pt(13)

    p_from = doc.add_paragraph()
    p_from.add_run("From:\n").bold = True
    p_from.add_run(f"{report_facts.get('owner_name', '[Your Name / Designation]')}\n")
    p_from.add_run(f"Distribution Company: {report_facts.get('discom_name', 'APSPDCL')}\n")
    p_from.add_run(f"Office Address / Location: {report_facts.get('location', '[Office Address]')}\n")
    p_from.add_run(f"Contact: {report_facts.get('phone', '[Contact Number]')} | Email: {report_facts.get('email', '[Email]')}\n\n")

    doc.add_paragraph(f"Date: {datetime.datetime.now().strftime('%d/%m/%Y')}\n")

    p_to = doc.add_paragraph()
    p_to.add_run("To:\n").bold = True
    p_to.add_run("The Station House Officer (SHO)\nLocal Police Station\n")
    p_to.add_run(f"{report_facts.get('location', '[City, District]')}\n\n")

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(f"Subject: Complaint regarding the theft of an electrical distribution transformer from {report_facts.get('location', '[Exact Location]')}.")
    r_sub.bold = True

    doc.add_paragraph("\nRespected Sir/Madam,\n\nI am writing to formally report the theft of public utility property belonging to " + report_facts.get('discom_name', 'APSPDCL') + ".\n")

    p_bullets = doc.add_paragraph()
    p_bullets.add_run(f"• Date and Time of Discovery: Discovered on {report_facts.get('detected_time', '[Date/Time]')}.\n")
    p_bullets.add_run(f"• Exact Location of Incident: {report_facts.get('location', '[Landmark/Pole No]')}.\n")
    p_bullets.add_run("• Details of Stolen Property:\n").bold = True
    p_bullets.add_run(f"   • Item: Distribution Transformer / Copper winding / Core units\n")
    p_bullets.add_run(f"   • Capacity: {report_facts.get('capacity', '100 KVA')}\n")
    p_bullets.add_run(f"   • Asset / Serial Number: {report_facts.get('transformer_id', '[Serial Number]')}\n")
    p_bullets.add_run(f"   • Estimated Value: Approximately ₹{report_facts.get('estimated_value', '2,50,000')}\n")

    p_desc = doc.add_paragraph()
    p_desc.add_run("Description of Incident:\n").bold = True
    p_desc.add_run(f"Upon visiting the site, our maintenance team observed that the transformer unit had been removed. Theft occurred around {report_facts.get('detected_time', 'the event window')}.\n")

    p_req = doc.add_paragraph()
    p_req.add_run("\nRequest for Action:\n").bold = True
    p_req.add_run("Kindly register an FIR under relevant sections of BNS / Electricity Act and initiate an investigation.")

    doc.add_paragraph("\nThank you for your prompt attention.\n")

    p_sig = doc.add_paragraph()
    p_sig.add_run("Yours faithfully,\n\n(Signature)\n").bold = True
    p_sig.add_run(f"{report_facts.get('owner_name', '[Your Name]')}\n")

    filename = f"Police_Complaint_TG-{report_facts.get('id', '000')}.docx"
    filepath = os.path.join(reports_folder, filename)
    doc.save(filepath)
    return filename


def create_electrical_complaint_docx(report_facts, reports_folder):
    """
    ELECETRIICAL Complaint Letter Format
    """
    doc = Document()
    
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("ELECETRIICAL Complaint Letter Format\n")
    r_title.bold = True
    r_title.font.size = Pt(13)

    p_from = doc.add_paragraph()
    p_from.add_run("From:\n").bold = True
    p_from.add_run(f"{report_facts.get('owner_name', '[Your Name]')}\n")
    p_from.add_run(f"{report_facts.get('location', '[Your Address]')}\n")
    p_from.add_run(f"Contact: {report_facts.get('phone', '[Contact Number]')}\n\n")

    doc.add_paragraph(f"Date: {datetime.datetime.now().strftime('%d/%m/%Y')}\n")

    p_to = doc.add_paragraph()
    p_to.add_run("To:\n").bold = True
    p_to.add_run(f"The Assistant Engineer / Branch Manager,\n{report_facts.get('discom_name', 'APSPDCL')}\n\n")

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Subject: Urgent report regarding theft of area electricity transformer and request for immediate replacement.")
    r_sub.bold = True

    doc.add_paragraph("\nRespected Sir/Madam,\n")
    doc.add_paragraph(
        f"I am writing to report the theft of the distribution transformer installed at {report_facts.get('location', '[Location]')}. "
        f"The theft was discovered on {report_facts.get('detected_time', '[Time]')}. Due to this outage, our locality is experiencing a total blackout. "
        "We request an immediate site inspection and replacement."
    )

    doc.add_paragraph("\nThanking you,\n\nYours faithfully,\n\n(Signature)\n" + report_facts.get('owner_name', '[Printed Name]'))

    filename = f"Electrical_Dept_Request_TG-{report_facts.get('id', '000')}.docx"
    filepath = os.path.join(reports_folder, filename)
    doc.save(filepath)
    return filename


def create_evidence_pdf(report_facts, reports_folder, root_static_folder):
    """
    Generates a PDF evidence report containing metadata and image thumbnails with fixed paths.
    """
    filename = f"Evidence_Package_TG-{report_facts.get('id', '000')}.pdf"
    filepath = os.path.join(reports_folder, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=colors.HexColor("#0f172a")
    )

    story.append(Paragraph("TRANSGUARD AI — INCIDENT EVIDENCE PACKAGE", title_style))
    story.append(Spacer(1, 15))

    meta_text = f"""
    <b>Incident ID:</b> TG-{report_facts.get('id', '000')}<br/>
    <b>Transformer ID:</b> {report_facts.get('transformer_id', 'TG-001')}<br/>
    <b>Detected Date/Time:</b> {report_facts.get('detected_time', 'N/A')}<br/>
    <b>Threat Level:</b> {report_facts.get('threat_level', 'HIGH')}<br/>
    <b>Complainant:</b> {report_facts.get('owner_name', 'N/A')} ({report_facts.get('phone', 'N/A')})<br/>
    <b>Location:</b> {report_facts.get('location', 'N/A')}
    """
    story.append(Paragraph(meta_text, styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Captured Frame Evidence Attachments:</b>", styles['Heading3']))
    story.append(Spacer(1, 10))

    imgs = report_facts.get('images', [])
    img_cells = []

    for img in imgs[:6]:
        rel_path = img.get('file_path') if isinstance(img, dict) else (img['file_path'] if hasattr(img, '__getitem__') else getattr(img, 'file_path', None))
        timestamp = img.get('captured_at') if isinstance(img, dict) else (img['captured_at'] if hasattr(img, '__getitem__') else getattr(img, 'captured_at', 'N/A'))
        
        if rel_path:
            full_img_path = os.path.join(root_static_folder, rel_path)
            if os.path.exists(full_img_path):
                rl_img = RLImage(full_img_path, width=220, height=140)
                caption = Paragraph(f"<font size=8>{timestamp}</font>", styles['Normal'])
                img_cells.append([rl_img, caption])

    if img_cells:
        table_data = []
        for i in range(0, len(img_cells), 2):
            row = [img_cells[i][0]]
            row.append(img_cells[i+1][0] if i + 1 < len(img_cells) else "")
            table_data.append(row)

            caption_row = [img_cells[i][1]]
            caption_row.append(img_cells[i+1][1] if i + 1 < len(img_cells) else "")
            table_data.append(caption_row)

        t = Table(table_data, colWidths=[260, 260])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No physical image frames were captured for this session.", styles['Normal']))

    doc.build(story)
    return filename


def create_evidence_zip(report_facts, reports_folder, root_static_folder, video_rel_path=None):
    """
    Bundles PDF report, raw photo JPEG files, and video WEBM file into a downloadable .ZIP archive.
    """
    pdf_filename = f"Evidence_Package_TG-{report_facts.get('id', '000')}.pdf"
    pdf_filepath = os.path.join(reports_folder, pdf_filename)

    # Only generate the PDF if it does not already exist.
    # This avoids regenerating it every time the download button is pressed.
    if not os.path.exists(pdf_filepath):
        create_evidence_pdf(report_facts, reports_folder, root_static_folder)

    zip_filename = f"Full_Evidence_Bundle_TG-{report_facts.get('id', '000')}.zip"
    zip_filepath = os.path.join(reports_folder, zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 1. Add generated PDF
        if os.path.exists(pdf_filepath):
            zipf.write(pdf_filepath, arcname=pdf_filename)

        # 2. Add Captured Images
        imgs = report_facts.get('images', [])
        for idx, img in enumerate(imgs, start=1):
            rel_path = img.get('file_path') if isinstance(img, dict) else (img['file_path'] if hasattr(img, '__getitem__') else getattr(img, 'file_path', None))
            if rel_path:
                full_path = os.path.join(root_static_folder, rel_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, arcname=f"captured_photos/Frame_{idx}.jpg")

        # 3. Add Video File if recorded
        if video_rel_path:
            full_video_path = os.path.join(root_static_folder, video_rel_path)
            if os.path.exists(full_video_path):
                zipf.write(full_video_path, arcname="video_evidence/Live_Feed_Recording.mp4")

    return zip_filename