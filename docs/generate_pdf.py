import os
import re
import shutil
from pathlib import Path
from PIL import Image as PILImage

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
    Image,
    KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages for 'Page X of Y' footer and running header."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header rule and text (on pages > 1)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(45, letter[1] - 36, letter[0] - 45, letter[1] - 36)
            self.drawString(45, letter[1] - 30, "Resume-to-Technical-Case-Study System -- Technical & Operational Documentation")
            self.drawRightString(letter[0] - 45, letter[1] - 30, "Author: Sandipan Sarkar")

        # Footer rule and text (on all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(45, 40, letter[0] - 45, 40)
        
        self.drawString(45, 28, "Confidential & Proprietary | Engineering Portfolio Documentation")
        page_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(letter[0] - 45, 28, page_text)
        self.restoreState()


def clean_markdown_inline(text: str) -> str:
    """Escape XML special chars and translate markdown inline formatting to ReportLab XML tags."""
    # Convert unicode punctuation to safe ASCII/entities for ReportLab standard Helvetica
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("\u2014", " -- ")     # Em dash to clean double dash
    t = t.replace("\u2013", "-")        # En dash to single dash
    t = t.replace("\u2026", "...")      # Ellipsis
    t = t.replace("\u2018", "'").replace("\u2019", "'")  # Curly single quotes
    t = t.replace("\u201c", '"').replace("\u201d", '"')  # Curly double quotes
    t = t.replace("\u2192", "->")       # Arrow ->

    # Links: [text](url) -> text (url)
    t = re.sub(r"\[(.*?)\]\((.*?)\)", r'<b>\1</b> (<font color="#0284C7">\2</font>)', t)
    # Bold italic: ***text***
    t = re.sub(r"\*\*\*(.*?)\*\*\*", r"<b><i>\1</i></b>", t)
    # Bold: **text**
    t = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", t)
    # Italic: *text*
    t = re.sub(r"\*(.*?)\*", r"<i>\1</i>", t)
    # Inline code: `text`
    t = re.sub(r"`(.*?)`", r'<font face="Courier" color="#0369A1">\1</font>', t)
    return t


def build_pdf(md_path: str, output_pdf_path: str):
    available_width = letter[0] - 90  # 612 - 90 = 522 pt
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=21,
        leading=25,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0284C7"),
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor("#475569")
    )

    h1_style = ParagraphStyle(
        'DocH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=16,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=12,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3.5
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.white
    )

    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B"),
        alignment=1, # Centered
        spaceAfter=8
    )

    story = []

    content = Path(md_path).read_text(encoding='utf-8')
    lines = content.splitlines()

    i = 0
    in_code_block = False
    code_block_lang = ""
    code_block_lines = []

    diagram_map = {
        'flowchart': ('docs/assets/flowchart.png', 'Figure 1: End-to-End Workflow & Adaptive Interview Pipeline'),
        'graph tb': ('docs/assets/architecture.png', 'Figure 2: Modular System Architecture & Service Topology'),
        'erdiagram': ('docs/assets/er_diagram.png', 'Figure 3: Relational Data Model & Entity Relationships')
    }

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # Handle code blocks (e.g. Mermaid or config)
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_lang = stripped[3:].strip().lower()
                code_block_lines = []
                i += 1
                continue
            else:
                in_code_block = False
                code_text = "\n".join(code_block_lines).strip()

                # Check if this code block matches one of our pre-rendered diagrams
                matched_diag = None
                code_lower = code_text.lower()
                for key, (diag_path, caption) in diagram_map.items():
                    if key in code_lower and os.path.exists(diag_path):
                        matched_diag = (diag_path, caption)
                        break

                if matched_diag:
                    diag_path, caption = matched_diag
                    with PILImage.open(diag_path) as img:
                        w, h = img.size
                    
                    target_w = min(available_width, 480)
                    scale = target_w / w
                    target_h = min(h * scale, 340)
                    if target_h == 340:
                        target_w = w * (340 / h)

                    story.append(Spacer(1, 4))
                    story.append(Image(diag_path, width=target_w, height=target_h))
                    story.append(Spacer(1, 4))
                    story.append(Paragraph(caption, caption_style))
                    story.append(Spacer(1, 4))
                else:
                    # Regular code block: render as formatted monospace box
                    code_p = Paragraph(
                        f'<font face="Courier" size="7.5" color="#0369A1">{clean_markdown_inline(code_text).replace(chr(10), "<br/>")}</font>',
                        body_style
                    )
                    t_box = Table([[code_p]], colWidths=[available_width])
                    t_box.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('LEFTPADDING', (0,0), (-1,-1), 8),
                        ('RIGHTPADDING', (0,0), (-1,-1), 8),
                    ]))
                    story.append(Spacer(1, 4))
                    story.append(t_box)
                    story.append(Spacer(1, 6))

                i += 1
                continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        # Skip main markdown top title and subtitle since we render a custom executive header
        if stripped.startswith("# Resume-to-Technical-Case-Study System"):
            # Render Executive Header Block
            story.append(Paragraph("Resume-to-Technical-Case-Study System", title_style))
            story.append(Paragraph("Comprehensive Technical & Operational Architecture Documentation", subtitle_style))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0284C7"), spaceAfter=10))

            meta_data = [
                [
                    Paragraph("<b>Author:</b> Sandipan Sarkar", meta_style),
                    Paragraph("<b>Version:</b> 1.0 (Production)", meta_style),
                    Paragraph("<b>Date:</b> September 2026", meta_style)
                ],
                [
                    Paragraph("<b>Frontend:</b> resume-project-sooty-eta.vercel.app", meta_style),
                    Paragraph("<b>Backend API:</b> resume-project-osw9.onrender.com", meta_style),
                    Paragraph("<b>Swagger Docs:</b> .../docs", meta_style)
                ]
            ]
            t_meta = Table(meta_data, colWidths=[available_width/3.0]*3)
            t_meta.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t_meta)
            story.append(Spacer(1, 14))
            i += 1
            continue

        # Skip redundant preamble lines already captured in header
        if stripped.startswith(("### Project Documentation", "**Author**:", "**Date**:", "**Version**:", "**Live Application**:", "- Frontend:", "- Backend API:", "- API Documentation:")):
            i += 1
            continue

        # Horizontal Rule
        if stripped == "---":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=8))
            i += 1
            continue

        # Markdown Table Detection
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Parse table lines
            if len(table_lines) >= 2:
                header_raw = [c.strip() for c in table_lines[0].strip("|").split("|")]
                rows_data = []

                # Row 0: headers
                header_cells = [Paragraph(clean_markdown_inline(c), table_header_style) for c in header_raw]
                rows_data.append(header_cells)

                # Data rows (skipping delimiter line at index 1)
                for r_idx in range(2, len(table_lines)):
                    r_raw = [c.strip() for c in table_lines[r_idx].strip("|").split("|")]
                    # Ensure matching cell count
                    while len(r_raw) < len(header_raw):
                        r_raw.append("")
                    row_cells = [Paragraph(clean_markdown_inline(c), table_cell_style) for c in r_raw[:len(header_raw)]]
                    rows_data.append(row_cells)

                num_cols = len(header_raw)
                # Compute balanced column widths
                if num_cols == 2:
                    col_widths = [140, available_width - 140]
                elif num_cols == 3:
                    col_widths = [110, 150, available_width - 260]
                elif num_cols == 4:
                    col_widths = [80, 130, 130, available_width - 340]
                else:
                    col_widths = [available_width / num_cols] * num_cols

                t_table = Table(rows_data, colWidths=col_widths, repeatRows=1)
                t_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E293B")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(Spacer(1, 4))
                story.append(t_table)
                story.append(Spacer(1, 8))
            continue

        # Headings
        if stripped.startswith("## "):
            heading_text = clean_markdown_inline(stripped[3:].strip())
            story.append(Spacer(1, 6))
            story.append(Paragraph(heading_text, h1_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=8))
            i += 1
            continue

        if stripped.startswith("### "):
            heading_text = clean_markdown_inline(stripped[4:].strip())
            story.append(Spacer(1, 4))
            story.append(Paragraph(heading_text, h2_style))
            i += 1
            continue

        # Bullet points
        if stripped.startswith(("- ", "* ")):
            bullet_text = clean_markdown_inline(stripped[2:].strip())
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{bullet_text}", bullet_style))
            i += 1
            continue

        # Numbered list
        num_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if num_match:
            num = num_match.group(1)
            num_text = clean_markdown_inline(num_match.group(2).strip())
            story.append(Paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{num_text}", bullet_style))
            i += 1
            continue

        # Standard paragraph
        p_text = clean_markdown_inline(stripped)
        story.append(Paragraph(p_text, body_style))
        i += 1

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF at: {output_pdf_path}")

if __name__ == '__main__':
    md_file = 'docs/PROJECT_DOCUMENTATION.md'
    pdf_out = 'docs/PROJECT_DOCUMENTATION.pdf'
    build_pdf(md_file, pdf_out)

    # Copy to frontend/public for direct web download
    os.makedirs('frontend/public', exist_ok=True)
    shutil.copy(pdf_out, 'frontend/public/PROJECT_DOCUMENTATION.pdf')
    print("Copied to frontend/public/PROJECT_DOCUMENTATION.pdf")

    # Copy to conversation artifacts directory
    artifact_dir = r'C:\Users\sandipansarkar\.gemini\antigravity-ide\brain\6dbc0273-3885-4883-98e9-8909879d7b16'
    if os.path.exists(artifact_dir):
        shutil.copy(pdf_out, os.path.join(artifact_dir, 'PROJECT_DOCUMENTATION.pdf'))
        print(f"Copied to artifact directory: {artifact_dir}")
