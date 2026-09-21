import re
from pathlib import Path
from typing import List
from app.ai.schemas.resume import (
    DocumentRepresentation,
    DocumentMetadata,
    DocumentBlock,
)

class ResumeParser:
    """
    Layout-aware and structure-aware resume document parser.
    Converts PDF, DOCX, and TXT files into a normalized DocumentRepresentation
    with block typing, ordering, page/column awareness.
    """

    HEADING_PATTERNS = [
        r"^(?:technical\s+)?projects?(?:\s+portfolio)?$",
        r"^(?:selected|featured|relevant|personal|academic)\s+projects?$",
        r"^(?:work\s+)?experience(?:\s+history)?$",
        r"^education(?:\s+&\s+qualifications)?$",
        r"^skills(?:\s+&\s+technologies)?$",
        r"^summary(?:\s+statement)?$",
        r"^achievements?$",
        r"^publications?$",
        r"^certifications?$"
    ]

    BULLET_PREFIXES = ("•", "-", "*", "–", "—", "►", "▪", "▫", "✓")

    def parse(self, file_path: Path, filename: str) -> DocumentRepresentation:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            doc = self._parse_pdf(file_path, filename)
        elif suffix in (".docx", ".doc"):
            doc = self._parse_docx(file_path, filename)
        elif suffix in (".txt", ".md"):
            doc = self._parse_text(file_path, filename)
        else:
            # Fallback to text reading
            doc = self._parse_text(file_path, filename)

        doc.blocks = self._merge_wrapped_lines(doc.blocks)
        return doc

    def _is_date_ending(self, text: str) -> bool:
        return bool(re.search(r'(\d{1,2}/\d{2,4}|\b\d{4})\s*[-–—\s]*(present|\d{1,2}/\d{2,4}|\d{4})?\s*$', text, re.I))

    def _merge_wrapped_lines(self, blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        """
        Merge wrapped lines that are part of the same paragraph/sentence.
        For example: 'Developing a CRAG-based...' + 'generation capabilities.'
        """
        if not blocks:
            return blocks

        merged: List[DocumentBlock] = []
        for b in blocks:
            if not merged:
                merged.append(b)
                continue

            prev = merged[-1]
            if (
                b.type == "paragraph" and
                prev.type in ("paragraph", "bullet") and
                b.text and b.text[0].islower() and
                prev.column == b.column and
                prev.page == b.page and
                not prev.text.endswith((".", ":", "!", "?", ";")) and
                not self._is_date_ending(prev.text)
            ):
                prev.text = f"{prev.text.rstrip('-')} {b.text}"
            else:
                merged.append(b)

        for idx, b in enumerate(merged, start=1):
            b.order = idx
            b.id = f"b_{idx}"

        return merged

    def _is_heading(self, line: str) -> bool:
        clean = line.strip().lower()
        clean = re.sub(r"[:\-_#]+$", "", clean).strip()
        for pat in self.HEADING_PATTERNS:
            if re.match(pat, clean):
                return True
        # Heuristic for short uppercase lines that look like headings
        if 2 < len(clean) < 35 and line.isupper():
            return True
        return False

    def _parse_pdf(self, file_path: Path, filename: str) -> DocumentRepresentation:
        blocks: List[DocumentBlock] = []
        total_pages = 1
        order = 1

        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract words with coordinates to detect columns
                    words = page.extract_words()
                    if not words:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            line_str = line.strip()
                            if not line_str:
                                continue
                            b_type = "heading" if self._is_heading(line_str) else (
                                "bullet" if line_str.startswith(self.BULLET_PREFIXES) else "paragraph"
                            )
                            blocks.append(DocumentBlock(
                                id=f"b_{order}",
                                type=b_type,
                                text=line_str,
                                order=order,
                                page=page_num,
                                column=1
                            ))
                            order += 1
                        continue

                    # Detect genuine two-column layout:
                    # A true two-column page requires:
                    # 1. Zero words crossing the center dividing line
                    # 2. Substantial content in both columns (>30 words each)
                    # 3. An actual measurable whitespace gutter (>10pt) between the two columns
                    page_mid = page.width / 2.0
                    spanning_words = [w for w in words if w['x0'] < page_mid < w['x1']]
                    left_words = [w for w in words if w['x1'] <= page_mid]
                    right_words = [w for w in words if w['x0'] >= page_mid]

                    is_two_col = False
                    if len(spanning_words) == 0 and len(left_words) > 30 and len(right_words) > 30:
                        left_max_x = max((w['x1'] for w in left_words), default=0)
                        right_min_x = min((w['x0'] for w in right_words), default=page.width)
                        if (right_min_x - left_max_x) > 10.0:
                            is_two_col = True

                    if is_two_col:
                        left_crop = page.crop((0, 0, page_mid, page.height))
                        right_crop = page.crop((page_mid, 0, page.width, page.height))
                        
                        for col_idx, crop in enumerate([left_crop, right_crop], start=1):
                            crop_text = crop.extract_text(layout=False) or ""
                            for line in crop_text.splitlines():
                                line_str = line.strip()
                                if not line_str or len(line_str) <= 1:
                                    continue
                                b_type = "heading" if self._is_heading(line_str) else (
                                    "bullet" if line_str.startswith(self.BULLET_PREFIXES) else "paragraph"
                                )
                                blocks.append(DocumentBlock(
                                    id=f"b_{order}",
                                    type=b_type,
                                    text=line_str,
                                    order=order,
                                    page=page_num,
                                    column=col_idx
                                ))
                                order += 1
                    else:
                        # Extract full natural page layout
                        page_text = page.extract_text(layout=False) or ""
                        for line in page_text.splitlines():
                            line_str = line.strip()
                            if not line_str or len(line_str) <= 1:
                                continue
                            b_type = "heading" if self._is_heading(line_str) else (
                                "bullet" if line_str.startswith(self.BULLET_PREFIXES) else "paragraph"
                            )
                            blocks.append(DocumentBlock(
                                id=f"b_{order}",
                                type=b_type,
                                text=line_str,
                                order=order,
                                page=page_num,
                                column=1
                            ))
                            order += 1
        except Exception as e:
            # Fallback to pypdf if pdfplumber encounters an error
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                total_pages = len(reader.pages)
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        line_str = line.strip()
                        if not line_str:
                            continue
                        b_type = "heading" if self._is_heading(line_str) else (
                            "bullet" if line_str.startswith(self.BULLET_PREFIXES) else "paragraph"
                        )
                        blocks.append(DocumentBlock(
                            id=f"b_{order}",
                            type=b_type,
                            text=line_str,
                            order=order,
                            page=page_num,
                            column=1
                        ))
                        order += 1
            except Exception:
                pass

        return DocumentRepresentation(
            metadata=DocumentMetadata(
                filename=filename,
                file_type="pdf",
                total_pages=total_pages,
                file_size_bytes=file_path.stat().st_size if file_path.exists() else 0
            ),
            blocks=blocks
        )

    def _parse_docx(self, file_path: Path, filename: str) -> DocumentRepresentation:
        import docx
        doc = docx.Document(file_path)
        blocks: List[DocumentBlock] = []
        order = 1

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower() if p.style else ""
            if "heading" in style_name or self._is_heading(text):
                b_type = "heading"
            elif "list" in style_name or text.startswith(self.BULLET_PREFIXES):
                b_type = "bullet"
            else:
                b_type = "paragraph"

            blocks.append(DocumentBlock(
                id=f"b_{order}",
                type=b_type,
                text=text,
                order=order,
                page=1,
                column=1
            ))
            order += 1

        return DocumentRepresentation(
            metadata=DocumentMetadata(
                filename=filename,
                file_type="docx",
                total_pages=1,
                file_size_bytes=file_path.stat().st_size if file_path.exists() else 0
            ),
            blocks=blocks
        )

    def _parse_text(self, file_path: Path, filename: str) -> DocumentRepresentation:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        blocks: List[DocumentBlock] = []
        order = 1

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            if self._is_heading(line_str) or line_str.startswith("#"):
                b_type = "heading"
                line_str = re.sub(r"^#+\s*", "", line_str)
            elif line_str.startswith(self.BULLET_PREFIXES):
                b_type = "bullet"
            else:
                b_type = "paragraph"

            blocks.append(DocumentBlock(
                id=f"b_{order}",
                type=b_type,
                text=line_str,
                order=order,
                page=1,
                column=1
            ))
            order += 1

        return DocumentRepresentation(
            metadata=DocumentMetadata(
                filename=filename,
                file_type="txt",
                total_pages=1,
                file_size_bytes=file_path.stat().st_size if file_path.exists() else 0
            ),
            blocks=blocks
        )
