"""
modules/pdf_parser.py
Pure-Python PDF text extraction — no dependencies required.
Uses structural heuristics against the PDF binary format.

For production use, drop-in replace extract_text() body with PyPDF2
or pdfplumber if those packages are available.
"""

import re


def extract_text(data: bytes, filename: str, max_chars: int = 40_000) -> str:
    """
    Extract readable text from raw PDF bytes.

    Strategies (applied in order):
      1. BT...ET text blocks with parenthesis and hex strings
      2. Readable ASCII runs from stream objects
      3. Full-file fallback scan

    Returns extracted text capped at max_chars, or a fallback message.
    """
    try:
        # Decode as latin-1 to preserve all byte values
        raw = data.decode("latin-1", errors="replace")
        text_parts: list[str] = []

        # ── Strategy 1: BT...ET blocks ────────────────────────────────
        for bt_match in re.finditer(r"BT(.*?)ET", raw, re.DOTALL):
            block = bt_match.group(1)

            # Parenthesis strings: (Hello World)
            for s in re.findall(r"\(([^)]{1,300})\)", block):
                cleaned = (
                    s.replace(r"\n", " ")
                     .replace(r"\r", " ")
                     .replace(r"\t", " ")
                     .strip()
                )
                if len(cleaned) > 2:
                    text_parts.append(cleaned)

            # Hex strings: <48656c6c6f>
            for hex_str in re.findall(r"<([0-9a-fA-F]+)>", block):
                if len(hex_str) % 2 == 0:
                    try:
                        decoded = bytes.fromhex(hex_str).decode("latin-1", errors="ignore")
                        printable = "".join(c for c in decoded if 0x20 <= ord(c) < 0x7F)
                        if len(printable) > 2:
                            text_parts.append(printable)
                    except ValueError:
                        pass

        # ── Strategy 2: stream content ASCII runs ─────────────────────
        for stream_match in re.finditer(r"stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL):
            chunk = stream_match.group(1)
            runs = re.findall(r"[\x20-\x7E]{5,}", chunk)
            for run in runs:
                if re.search(r"[a-zA-Z]{3,}", run):
                    text_parts.append(run)

        text = " ".join(text_parts)

        # ── Strategy 3: whole-file fallback ───────────────────────────
        if len(text.strip()) < 80:
            all_runs = re.findall(r"[\x20-\x7E]{6,}", raw)
            text = " ".join(
                r for r in all_runs
                if re.search(r"[a-zA-Z]{4,}", r)
                and not re.match(r"^[<>\[\]()\\/]{3,}", r)
            )

        # ── Clean & cap ───────────────────────────────────────────────
        text = re.sub(r"\s{3,}", " ", text).strip()

        if len(text) < 50:
            return _fallback(filename)

        return text[:max_chars]

    except Exception as exc:
        return _fallback(filename, str(exc))


def _fallback(filename: str, reason: str = "") -> str:
    note = f" ({reason})" if reason else ""
    return (
        f'[PDF: "{filename}" — browser-side text extraction was limited{note}. '
        f"For best results, convert to .txt or .md before uploading, "
        f"or install PyPDF2: pip install PyPDF2]"
    )


def extract_text_pypdf(data: bytes, filename: str, max_chars: int = 40_000) -> str:
    """
    High-fidelity extraction using PyPDF2 (if installed).
    Falls back to heuristic extraction if not available.
    """
    try:
        import io
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
        text = "\n".join(pages).strip()
        return text[:max_chars] if text else _fallback(filename)

    except ImportError:
        return extract_text(data, filename, max_chars)
    except Exception as exc:
        return _fallback(filename, str(exc))
