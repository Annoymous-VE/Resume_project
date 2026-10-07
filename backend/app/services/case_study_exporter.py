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
    KeepTogether,
    Table,
    TableStyle
)
from reportlab.pdfgen import canvas

class BrochureNumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages for 'Page X of Y' brochure footer with commercial branding."""
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
        # Header rule and text (on pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor("#0284C7"))
            self.drawString(45, letter[1] - 32, "CLIENT SOLUTION OVERVIEW & VALUE PROPOSITION")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawRightString(letter[0] - 45, letter[1] - 32, "Executive Commercial Brief")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(45, letter[1] - 36, letter[0] - 45, letter[1] - 36)

        # Footer rule and text
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(45, 38, letter[0] - 45, 38)
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(45, 26, "Confidential • Commercial in Confidence • Solution Overview")
        page_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(letter[0] - 45, 26, page_text)
        self.restoreState()


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
    def export_to_docx(cls, title: str, markdown_content: str, variant_type: str = "technical") -> io.BytesIO:
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
        sub_text = (
            "Executive Solution Overview & Commercial Value Proposition"
            if variant_type == "client_brochure"
            else "Deep-Dive Technical Architecture & Engineering Case Study"
        )
        run_sub = sub_p.add_run(sub_text)
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

    @staticmethod
    def _extract_brochure_metrics(markdown_content: str) -> List[dict]:
        """Extract quantifiable metric callouts from brochure markdown for highlight cards."""
        metrics = []
        for line in markdown_content.splitlines():
            clean = line.strip()
            if not clean.startswith(("- ", "* ", "• ")):
                continue
            # Pattern 1: - **Category**: **Value** — Description
            m1 = re.match(r"^[-*•]\s*\*\*(.*?)\*\*:\s*\*\*(.*?)\*\*\s*(?:[—–-]\s*(.*))?$", clean)
            if m1:
                lbl, val, desc = m1.group(1).strip(), m1.group(2).strip(), (m1.group(3) or "").strip()
                metrics.append({"label": lbl, "value": val, "description": desc})
                continue
            # Pattern 2: - **Category**: Value — Description (where Value has numbers or stats)
            m2 = re.match(r"^[-*•]\s*\*\*(.*?)\*\*:\s*([^—–-]+?)\s*(?:[—–-]\s*(.*))?$", clean)
            if m2:
                lbl, val, desc = m2.group(1).strip(), m2.group(2).strip(), (m2.group(3) or "").strip()
                if any(c.isdigit() for c in val) or any(w in val.lower() for w in ["faster", "reduction", "%", "boost", "scale", "req/"]):
                    metrics.append({"label": lbl, "value": val, "description": desc})
        return metrics[:4]

    @classmethod
    def export_brochure_to_pdf(cls, title: str, markdown_content: str, key_metrics: Optional[List[dict]] = None) -> io.BytesIO:
        """
        Generate a dedicated 1-to-2 page marketing flyer/brochure PDF using ReportLab.
        Features visual metric callout boxes, executive summary sidebars, and commercial styling.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=45,
            rightMargin=45,
            topMargin=45,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()

        eyebrow_style = ParagraphStyle(
            'BrochureEyebrow',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0284C7"),
            spaceAfter=3
        )

        title_style = ParagraphStyle(
            'BrochureTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4
        )

        tagline_style = ParagraphStyle(
            'BrochureTagline',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            leading=13.5,
            textColor=colors.HexColor("#475569"),
            spaceAfter=10
        )

        h2_style = ParagraphStyle(
            'BrochureH2',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        )

        h3_style = ParagraphStyle(
            'BrochureH3',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#0284C7"),
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            'BrochureBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4
        )

        bullet_style = ParagraphStyle(
            'BrochureBullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            leftIndent=14,
            firstLineIndent=-8,
            spaceAfter=3
        )

        summary_callout_style = ParagraphStyle(
            'BrochureSummaryCallout',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1E293B")
        )

        metric_card_style = ParagraphStyle(
            'BrochureMetricCard',
            parent=styles['Normal'],
            alignment=1, # Center
            leading=12
        )

        story = []

        # 1. Header Banner
        clean_title = re.sub(r"^#\s*", "", title).strip()
        story.append(Paragraph("CLIENT SOLUTION BRIEF | BUSINESS IMPACT REPORT", eyebrow_style))
        story.append(Paragraph(clean_title, title_style))

        # Look for tagline in first few lines of markdown (*tagline* or _tagline_)
        tagline = "Executive Solution Brief & Measurable Client Transformation"
        lines = markdown_content.splitlines()
        for l in lines[:5]:
            clean_l = l.strip()
            if clean_l.startswith("*") and clean_l.endswith("*") and len(clean_l) > 6:
                tagline = clean_l.strip("*_ ")
                break

        story.append(Paragraph(tagline, tagline_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0284C7"), spaceAfter=8))

        # 2. Visual Metric Callout Boxes
        metrics = key_metrics or cls._extract_brochure_metrics(markdown_content)
        if metrics:
            printable_width = letter[0] - 90  # 522 pt
            col_width = printable_width / len(metrics)
            card_cells = []
            for m in metrics:
                val = m.get("value", "")
                lbl = m.get("label", "")
                desc = m.get("description", "")
                cell_html = (
                    f'<font size="14" color="#0284C7"><b>{val}</b></font><br/>'
                    f'<font size="8" color="#0F172A"><b>{lbl}</b></font>'
                )
                if desc:
                    clean_desc = desc[:45] + ("..." if len(desc) > 45 else "")
                    cell_html += f'<br/><font size="7" color="#64748B">{clean_desc}</font>'
                card_cells.append(Paragraph(cell_html, metric_card_style))

            metric_table = Table([card_cells], colWidths=[col_width] * len(metrics))
            metric_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(metric_table)
            story.append(Spacer(1, 8))

        def format_markdown_inline_for_reportlab(text: str) -> str:
            t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            t = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", t)
            t = re.sub(r"\*(.*?)\*", r"<i>\1</i>", t)
            t = re.sub(r"`(.*?)`", r'<font color="#0284C7" name="Courier">\1</font>', t)
            return t

        in_executive_summary = False
        summary_paragraphs = []

        def flush_summary():
            nonlocal in_executive_summary, summary_paragraphs
            if summary_paragraphs:
                summary_text = "<br/><br/>".join(summary_paragraphs)
                callout_table = Table([[Paragraph(summary_text, summary_callout_style)]], colWidths=[letter[0] - 90])
                callout_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#BBF7D0")),
                    ('LINEBEFORE', (0,0), (-1,-1), 3.5, colors.HexColor("#16A34A")),
                    ('TOPPADDING', (0,0), (-1,-1), 7),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                    ('LEFTPADDING', (0,0), (-1,-1), 10),
                    ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ]))
                story.append(callout_table)
                story.append(Spacer(1, 6))
                summary_paragraphs = []
            in_executive_summary = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Skip main title or tagline already rendered in banner
            if (line.startswith("# ") and clean_title.lower() in line.lower()) or (line.startswith("*") and line.endswith("*") and line.strip("*_ ") == tagline):
                continue

            if line.startswith("## "):
                flush_summary()
                heading_raw = line[3:].strip()
                if "executive summary" in heading_raw.lower() or "value proposition" in heading_raw.lower():
                    in_executive_summary = True
                heading = format_markdown_inline_for_reportlab(heading_raw)
                story.append(Paragraph(heading, h2_style))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4))
            elif line.startswith("### "):
                flush_summary()
                heading = format_markdown_inline_for_reportlab(line[4:].strip())
                story.append(Paragraph(heading, h3_style))
            elif line.startswith(("- ", "* ", "• ")):
                flush_summary()
                bullet_content = format_markdown_inline_for_reportlab(line[2:].strip())
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{bullet_content}", bullet_style))
            elif in_executive_summary:
                summary_paragraphs.append(format_markdown_inline_for_reportlab(line))
            elif line.startswith(">"):
                quote_content = format_markdown_inline_for_reportlab(line.lstrip("> ").strip())
                story.append(Paragraph(quote_content, summary_callout_style))
            else:
                body_content = format_markdown_inline_for_reportlab(line)
                story.append(Paragraph(body_content, body_style))

        flush_summary()
        doc.build(story, canvasmaker=BrochureNumberedCanvas)
        buffer.seek(0)
        return buffer

    @classmethod
    def export_to_pdf(cls, title: str, markdown_content: str, variant_type: str = "technical") -> io.BytesIO:
        """Generate a crisp, styled PDF document using ReportLab."""
        if variant_type == "client_brochure":
            return cls.export_brochure_to_pdf(title, markdown_content)

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

