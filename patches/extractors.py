"""
Document text extraction and chunking for RAG ingestion.
Each extractor handles a specific file type and produces semantically meaningful chunks.
"""

import csv
import io
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

CHUNK_SIZE = 500  # Target tokens per chunk (approx 4 chars per token)
CHUNK_OVERLAP = 50  # Token overlap between chunks
MAX_CHUNK_CHARS = CHUNK_SIZE * 4


def _split_long_text(text: str, max_len: int) -> list[str]:
    """Split text that exceeds max_len on sentence boundaries."""
    parts = []
    while len(text) > max_len:
        # Try to split on sentence boundary
        cut = text.rfind(". ", 0, max_len)
        if cut < max_len // 2:
            cut = text.rfind(" ", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        parts.append(text[: cut + 1].strip())
        text = text[cut + 1 :].strip()
    if text:
        parts.append(text)
    return parts


@dataclass
class Chunk:
    """A chunk of text extracted from a document."""

    text: str
    index: int
    metadata: dict


def get_extractor(content_type: str):
    """Return the appropriate extractor for the given content type."""
    extractors = {
        "application/pdf": extract_pdf,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": extract_excel,
        # .xls (vnd.ms-excel) excluded — openpyxl only supports .xlsx
        "text/csv": extract_csv,
        "text/plain": extract_text,
    }
    return extractors.get(content_type)


def extract_pdf(file) -> list[Chunk]:
    """Extract text from PDF, splitting by pages/paragraphs."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed, cannot extract PDF")
        return []

    chunks = []
    file.seek(0)
    doc = fitz.open(stream=file.read(), filetype="pdf")

    for page_num, page in enumerate(doc):
        text = page.get_text().strip()
        if not text:
            continue

        # Split into paragraph-sized chunks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_chunk = ""

        for para in paragraphs:
            # Split oversized paragraphs to stay within chunk limits
            if len(para) > CHUNK_SIZE * 4:
                para_parts = _split_long_text(para, CHUNK_SIZE * 4)
            else:
                para_parts = [para]

            for part in para_parts:
                if len(current_chunk) + len(part) > CHUNK_SIZE * 4:
                    if current_chunk:
                        chunks.append(
                            Chunk(
                                text=current_chunk.strip(),
                                index=len(chunks),
                                metadata={"page": page_num + 1},
                            )
                        )
                    current_chunk = part
                else:
                    current_chunk += "\n\n" + part if current_chunk else part

        if current_chunk:
            chunks.append(
                Chunk(
                    text=current_chunk.strip(),
                    index=len(chunks),
                    metadata={"page": page_num + 1},
                )
            )

    doc.close()
    return chunks


def extract_excel(file) -> list[Chunk]:
    """
    Extract from Excel preserving column semantics.
    Each row becomes a chunk with column headers as context.
    """
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not installed, cannot extract Excel")
        return []

    chunks = []
    file.seek(0)
    wb = openpyxl.load_workbook(file, read_only=True, data_only=True)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        # First row as headers
        headers = [str(h) if h else f"Column_{i}" for i, h in enumerate(rows[0])]

        # Each row becomes a chunk
        for row_idx, row in enumerate(rows[1:], start=2):
            parts = []
            for header, value in zip(headers, row):
                if value is not None and str(value).strip():
                    parts.append(f"{header}: {value}")

            if parts:
                text = f"Sheet: {sheet_name} | Row {row_idx}\n" + " | ".join(parts)
                chunks.append(
                    Chunk(
                        text=text,
                        index=len(chunks),
                        metadata={"sheet": sheet_name, "row": row_idx},
                    )
                )

    wb.close()
    return chunks


def extract_csv(file) -> list[Chunk]:
    """Extract from CSV with column headers as context."""
    chunks = []
    file.seek(0)

    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)
    if not headers:
        return []

    for row_idx, row in enumerate(reader, start=2):
        parts = []
        for header, value in zip(headers, row):
            if value and value.strip():
                parts.append(f"{header}: {value}")

        if parts:
            text = " | ".join(parts)
            chunks.append(
                Chunk(
                    text=text,
                    index=len(chunks),
                    metadata={"row": row_idx},
                )
            )

    return chunks


def extract_text(file) -> list[Chunk]:
    """
    Extract plain text into chunks.

    Demo patch: respect markdown section boundaries when present. The upstream
    behaviour splits greedily on paragraph boundaries with a 2000-char cap,
    which routinely leaves section headers stranded at the end of one chunk
    while the section body lands in the next. That makes retrieval noisy on
    section-specific questions because the model gets the body without the
    header, or the header without the body.

    New behaviour:
      * Detect top-level section markers (lines starting with '## ').
      * If present, chunk by section. Sections that fit within MAX_CHUNK_CHARS
        become a single chunk. Sections that exceed it are split on paragraph
        boundaries with the section header carried into each sub-chunk so
        retrieval always has the header context.
      * If no '## ' markers are present, fall back to the original paragraph-
        based chunking so we don't change behaviour for unstructured documents.
    """
    import re

    file.seek(0)
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    # Demo patch: Allium spec files (`.allium`) are designed to be read top
    # to bottom; their rules, invariants and entities cross-reference one
    # another and lose meaning when chunked. Detect the language marker at
    # the head of the file and return the whole spec as a single chunk so
    # the model receives it as one coherent document under a single source
    # header.
    if content.lstrip().startswith("-- allium:"):
        return [Chunk(text=content, index=0, metadata={"format": "allium"})]

    if re.search(r"(?m)^## ", content):
        return _chunk_by_markdown_sections(content)

    # Fallback: original paragraph-based chunking, unchanged.
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(para) > MAX_CHUNK_CHARS:
            para_parts = _split_long_text(para, MAX_CHUNK_CHARS)
        else:
            para_parts = [para]

        for part in para_parts:
            if len(current_chunk) + len(part) > MAX_CHUNK_CHARS:
                if current_chunk:
                    chunks.append(
                        Chunk(
                            text=current_chunk.strip(), index=len(chunks), metadata={}
                        )
                    )
                current_chunk = part
            else:
                current_chunk += "\n\n" + part if current_chunk else part

    if current_chunk:
        chunks.append(Chunk(text=current_chunk.strip(), index=len(chunks), metadata={}))

    return chunks


def _chunk_by_markdown_sections(content: str) -> list[Chunk]:
    """
    Chunk markdown content by '## ' section headers. Each chunk carries its
    section header. Long sections are split on paragraph boundaries with the
    header repeated on each sub-chunk so retrieval never returns orphaned
    body text.
    """
    import re

    parts = re.split(r"(?m)(^## .*$)", content)
    # parts: [preamble?, header1, body1, header2, body2, ...]
    sections: list[tuple[str, str]] = []

    if parts and parts[0].strip():
        preamble = parts[0]
        title_match = re.search(r"(?m)^# (.+)$", preamble)
        header = (
            f"## {title_match.group(1).strip()} — preamble"
            if title_match
            else "## (preamble)"
        )
        sections.append((header, preamble.strip()))

    i = 1
    while i < len(parts):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append((header, body))
        i += 2

    chunks: list[Chunk] = []
    for header, body in sections:
        full_section = f"{header}\n\n{body}".strip() if body else header
        if len(full_section) <= MAX_CHUNK_CHARS:
            chunks.append(Chunk(text=full_section, index=len(chunks), metadata={}))
            continue

        # Section exceeds the budget. Split by paragraph, carry the header
        # into each sub-chunk so the model never sees orphaned body text.
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        body_budget = MAX_CHUNK_CHARS - len(header) - 4  # 4 chars for "\n\n"
        sub = ""
        for para in paragraphs:
            if len(para) > body_budget:
                para_parts = _split_long_text(para, body_budget)
            else:
                para_parts = [para]
            for part in para_parts:
                if sub and len(sub) + len(part) + 2 > body_budget:
                    chunks.append(
                        Chunk(
                            text=f"{header}\n\n{sub.strip()}",
                            index=len(chunks),
                            metadata={},
                        )
                    )
                    sub = part
                else:
                    sub = f"{sub}\n\n{part}" if sub else part
        if sub:
            chunks.append(
                Chunk(
                    text=f"{header}\n\n{sub.strip()}",
                    index=len(chunks),
                    metadata={},
                )
            )

    return chunks
