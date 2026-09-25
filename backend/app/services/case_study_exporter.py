import io
import re
from typing import List, Optional
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages for 'Page X of Y' footer."""
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
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 40, letter[0] - 54, letter[1] - 40)
            self.drawString(54, letter[1] - 35, "Technical Case Study — Architecture & Engineering Analysis")

        # Footer rule and text
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 45, letter[0] - 54, 45)
        
        self.drawString(54, 32, "Confidential & Proprietary • Engineering Portfolio")
        page_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(letter[0] - 54, 32, page_text)
        self.restoreState()


class CaseStudyExporter:
    """Exports technical case studies into polished Word (.docx) and PDF formats."""

    @staticmethod
    def _parse_inline_formatting_to_docx(paragraph, text: str):
        """Parse markdown bold and italic inline tokens into docx runs."""
        # Tokens: **bold**, *italic*, `code`
        token_pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.*?`)")
        parts = token_pattern.split(text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                run = paragraph.add_run(part[2:-2])
                run.bold = True
            elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
                run = paragraph.add_run(part[1:-1])
                run.italic = True
            elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
                run = paragraph.add_run(part[1:-1])
                run.font.name = "Consolas"
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(0x02, 0x84, 0xC7)
            else:
                paragraph.add_run(part)

    @classmethod
    def export_to_docx(cls, title: str, markdown_content: str) -> io.BytesIO:
        """Generate a professionally formatted Word DOCX document."""
        doc = Document()

        # Page setup: Standard margins (0.8 inch)
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.85)
            section.right_margin = Inches(0.85)

        # Document Title
        clean_title = re.sub(r"^#\s*", "", title).strip()
        title_p = doc.add_paragraph()
        title_p.paragraph_format.space_before = Pt(0)
        title_p.paragraph_format.space_after = Pt(4)
        run_title = title_p.add_run(clean_title)
        run_title.font.name = "Arial"
        run_title.font.size = Pt(22)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)  # Slate 900

        # Subtitle
        sub_p = doc.add_paragraph()
        sub_p.paragraph_format.space_before = Pt(0)
        sub_p.paragraph_format.space_after = Pt(18)
        run_sub = sub_p.add_run("Deep-Dive Technical Architecture & Engineering Case Study")
        run_sub.font.name = "Arial"
        run_sub.font.size = Pt(10.5)
        run_sub.font.italic = True
        run_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)  # Slate 500

        # Horizontal separator line
        hr_p = doc.add_paragraph()
        hr_p.paragraph_format.space_before = Pt(0)
        hr_p.paragraph_format.space_after = Pt(14)
        pPr = hr_p._p.get_or_add_pPr()
        pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="8" w:space="1" w:color="0284C7"/></w:pBdr>')
        pPr.append(pBdr)

        lines = markdown_content.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Skip duplicate main document title
            if line.startswith("# ") and clean_title.lower() in line.lower():
                continue

            # Level 2 Heading (e.g. ## Architecture & System Design)
            if line.startswith("## "):
                heading_text = line[3:].strip()
                h2 = doc.add_paragraph()
                h2.paragraph_format.space_before = Pt(16)
                h2.paragraph_format.space_after = Pt(6)
                h2.paragraph_format.keep_with_next = True
                h2_run = h2.add_run(heading_text)
                h2_run.font.name = "Arial"
                h2_run.font.size = Pt(14)
                h2_run.font.bold = True
                h2_run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

                # Light bottom border for h2
                hpPr = h2._p.get_or_add_pPr()
                hBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="4" w:space="2" w:color="E2E8F0"/></w:pBdr>')
                hpPr.append(hBdr)

            # Level 3 Heading (e.g. ### Sub-component)
            elif line.startswith("### "):
                heading_text = line[4:].strip()
                h3 = doc.add_paragraph()
                h3.paragraph_format.space_before = Pt(10)
                h3.paragraph_format.space_after = Pt(4)
                h3.paragraph_format.keep_with_next = True
                h3_run = h3.add_run(heading_text)
                h3_run.font.name = "Arial"
                h3_run.font.size = Pt(11.5)
                h3_run.font.bold = True
                h3_run.font.color.rgb = RGBColor(0x03, 0x69, 0xA1)

            # Bullet points
            elif line.startswith(("- ", "* ", "• ")):
                bullet_text = line[2:].strip()
                p = doc.add_paragraph(style='List Bullet')
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.15
                cls._parse_inline_formatting_to_docx(p, bullet_text)

            # Indented continuation lines (e.g., under a bullet point)
            elif raw_line.startswith(("  ", "\t")):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.4)
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.15
                cls._parse_inline_formatting_to_docx(p, line)

            # Blockquotes / Callout
            elif line.startswith(">"):
                quote_text = line.lstrip("> ").strip()
                qp = doc.add_paragraph()
                qp.paragraph_format.left_indent = Inches(0.3)
                qp.paragraph_format.space_before = Pt(4)
                qp.paragraph_format.space_after = Pt(6)
                q_pPr = qp._p.get_or_add_pPr()
                q_bdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:left w:val="single" w:sz="18" w:space="8" w:color="0284C7"/></w:pBdr>')
                q_pPr.append(q_bdr)
                cls._parse_inline_formatting_to_docx(qp, quote_text)

            # Standard body paragraph
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.line_spacing = 1.15
                cls._parse_inline_formatting_to_docx(p, line)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    @classmethod
    def export_to_pdf(cls, title: str, markdown_content: str) -> io.BytesIO:
        """Generate a crisp, styled PDF document using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CaseStudyTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'CaseStudySubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=14
        )

        h2_style = ParagraphStyle(
            'CaseStudyH2',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13.5,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )

        h3_style = ParagraphStyle(
            'CaseStudyH3',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#0284C7"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            'CaseStudyBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14.5,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6
        )

        bullet_style = ParagraphStyle(
            'CaseStudyBullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            leftIndent=16,
            firstLineIndent=-10,
            spaceAfter=4
        )

        bullet_sub_style = ParagraphStyle(
            'CaseStudyBulletSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#475569"),
            leftIndent=24,
            spaceAfter=4
        )

        callout_style = ParagraphStyle(
            'CaseStudyCallout',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
            leftIndent=14,
            spaceBefore=6,
            spaceAfter=6
        )

        story = []

        clean_title = re.sub(r"^#\s*", "", title).strip()
        story.append(Paragraph(clean_title, title_style))
        story.append(Paragraph("Deep-Dive Technical Architecture & Engineering Case Study", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=14))

        def format_markdown_inline_for_reportlab(text: str) -> str:
            """Escape HTML entities and convert Markdown syntax to ReportLab tags."""
            t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            t = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", t)
            t = re.sub(r"\*(.*?)\*", r"<i>\1</i>", t)
            t = re.sub(r"`(.*?)`", r'<font color="#0284C7" name="Courier">\1</font>', t)
            return t

        lines = markdown_content.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("# ") and clean_title.lower() in line.lower():
                continue

            if line.startswith("## "):
                heading = format_markdown_inline_for_reportlab(line[3:].strip())
                story.append(Paragraph(heading, h2_style))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=6))
            elif line.startswith("### "):
                heading = format_markdown_inline_for_reportlab(line[4:].strip())
                story.append(Paragraph(heading, h3_style))
            elif line.startswith(("- ", "* ", "• ")):
                bullet_content = format_markdown_inline_for_reportlab(line[2:].strip())
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{bullet_content}", bullet_style))
            elif raw_line.startswith(("  ", "\t")):
                sub_content = format_markdown_inline_for_reportlab(line)
                story.append(Paragraph(sub_content, bullet_sub_style))
            elif line.startswith(">"):
                quote_content = format_markdown_inline_for_reportlab(line.lstrip("> ").strip())
                story.append(Paragraph(quote_content, callout_style))
            else:
                body_content = format_markdown_inline_for_reportlab(line)
                story.append(Paragraph(body_content, body_style))

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer
