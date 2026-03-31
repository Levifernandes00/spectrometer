"""Parse spectrometer output files (TXT, PDF) and extract key-value results."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedFile:
    """Parsed content from a spectrometer file."""

    batch: str
    date: str
    time: str
    results: dict[str, float]  # key -> value, e.g. {"Cu": 0.086, "Si": 2.58, ...}


# Keys extracted from TXT format (matches Tauri spectometer)
TXT_KEYS = ["Cu", "Mn", "Ni", "Cr", "Sn", "Ti", "P", "Mo", "Si"]

# Keys for PDF tabular format (giorgietti-style)
PDF_KEYS = [
    "C", "Si", "Mn", "P", "S", "Cr", "Mo", "Ni",
    "Cu", "Sn", "Mg", "Al", "Co", "Nb", "Ti", "V",
    "W", "Pb", "As", "Zr", "Bi", "Ce", "Sb", "Te",
    "B", "Zn", "La", "Fe", "CE",
]


def extract_text(path: Path) -> str:
    """Extract text from a file. Supports .txt and .pdf."""
    ext = path.suffix.lower()
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(open(path, "rb"))
            return "\n".join(reader.pages[i].extract_text() or "" for i in range(len(reader.pages)))
        except ImportError:
            return ""
    return ""


def _parse_txt_format(text: str) -> ParsedFile | None:
    """Parse TXT format: Key: value lines, batch/date/time from header."""
    keys = set(TXT_KEYS)
    values: dict[str, float] = {}
    key_re = re.compile(r"(?i)^\s*(\w+):\s*([0-9,]+)")

    for line in text.splitlines():
        if m := key_re.match(line):
            key = m.group(1)
            val_str = m.group(2).replace(",", ".")
            if key in keys:
                try:
                    values[key] = float(val_str)
                except ValueError:
                    pass

    if not all(k in values for k in keys):
        return None

    batch, date, time = _extract_metadata(text)
    if not (batch and date and time):
        return None

    return ParsedFile(batch=batch, date=date, time=time, results=values)


def _extract_metadata(text: str) -> tuple[str | None, str | None, str | None]:
    """Extract batch name, date, time from file header."""
    date_re = re.compile(r"(\d{2}/\d{2}/\d{4})")
    time_re = re.compile(r"(\d{2}:\d{2}:\d{2})")

    batch: str | None = None
    date: str | None = None
    time: str | None = None

    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed == ";":
            continue
        if batch is None:
            bn = trimmed.rstrip(";").strip()
            if bn:
                batch = bn
        if date is None and (m := date_re.search(trimmed)):
            date = m.group(1)
        if time is None and (m := time_re.search(trimmed)):
            time = m.group(1)
        if batch and date and time:
            break

    return batch, date, time


def _extract_datetime(text: str) -> tuple[str | None, str | None]:
    """
    Extract date and time from file text.
    Tries: DD/MM/YYYY HH:MM:SS, DD/MM/YYYY HH:MM, then date and time separately.
    """
    # Combined: "08/01/2026 08:35:15" or "08/01/2026 08:35"
    combined = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}(?::\d{2})?)", text)
    if combined:
        date = combined.group(1)
        time_str = combined.group(2)
        time = time_str if ":" in time_str and time_str.count(":") == 2 else f"{time_str}:00"
        return date, time

    # Separate date and time
    date_re = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    time_re = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    if date_re and time_re:
        return date_re.group(1), time_re.group(1)

    # Alternate date format: YYYY-MM-DD HH:MM:SS
    alt = re.search(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}:\d{2}:\d{2})", text)
    if alt:
        yyyy, mm, dd, time = alt.groups()
        return f"{dd}/{mm}/{yyyy}", time

    return None, None


def _extract_nr_colata(text: str) -> str | None:
    """
    Extract Nr. Colata (batch name) from PDF text.
    Value can be on same line (Nr. Colata: 260009) or next line.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"Nr\.\s*Colata", line, re.I):
            # Same line: "Nr. Colata: 260009" or "Nr. Colata: 260009 ..."
            m = re.search(r"Nr\.\s*Colata:\s*(\d+\w*)", line, re.I)
            if m:
                return m.group(1).strip()
            # Next line: "Nr. Colata: Provino: Note:" followed by "260009 M9888"
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # First token is often the colata number
                first = next_line.split()[0] if next_line.split() else None
                if first and first[0].isdigit():
                    return first
            break
        if re.search(r"š?t\.\s*šarže", line, re.I):
            # Slovenian format: "Št. šarže:" followed by batch number on next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                first = next_line.split()[0] if next_line.split() else None
                if first and first[0].isdigit():
                    return first
            break
    return None


def _extract_decimal(line: str) -> float | None:
    """Extract the first decimal number from a line, handling comma decimals."""
    m = re.search(r"<?\s*([0-9]+[.,][0-9]+)\s*>?", line)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _parse_pdf_vertical_format(lines: list[str]) -> dict[str, float]:
    """
    Parse vertical PDF format where value is on the previous line and the key is on its own line.
    Example:
      3,161
      C
    """
    key_map = {"CEQ": "CE"}
    valid_keys = set(PDF_KEYS) | set(key_map.keys())
    values: dict[str, float] = {}

    for i, line in enumerate(lines):
        key = line.strip()
        if key not in valid_keys:
            continue
        # Ignore noisy glyphs that can be mis-extracted as valid element symbols.
        if i + 1 >= len(lines) or _extract_decimal(lines[i + 1]) is None:
            continue
        out_key = key_map.get(key, key)
        # In this format, "V" is frequently a mis-read average marker glyph.
        if out_key == "V":
            continue
        # Try the previous two lines and use the first decimal-looking value.
        for j in (i - 1, i - 2):
            if j < 0:
                continue
            val = _extract_decimal(lines[j])
            if val is not None:
                values[out_key] = val
                break

    return values


def _parse_pdf_format(text: str) -> ParsedFile | None:
    """Parse PDF tabular format (giorgietti-style): element headers + value rows."""
    batch = _extract_nr_colata(text) or "unknown"

    date, time = _extract_datetime(text)
    if not date:
        data_re = re.search(r"Data:\s*(\d{2}/\d{2}/\d{4})", text, re.I)
        date = data_re.group(1) if data_re else "01/01/1970"
    if not time:
        time = "00:00:00"

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    values: dict[str, float] = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        parts = line.split()
        headers = [p for p in parts if p in PDF_KEYS]
        # Require at least two headers to avoid false positives from noisy single glyphs.
        if len(headers) >= 2:
            for j in range(i + 1, min(i + 4, len(lines))):
                val_line = lines[j]
                nums = re.findall(r"<?\s*([0-9]+[.,][0-9]+)\s*>?", val_line)
                if len(nums) >= len(headers):
                    for k, v in zip(headers, nums):
                        try:
                            values[k] = float(v.replace(",", "."))
                        except ValueError:
                            pass
                    break
        i += 1

    if not values:
        values = _parse_pdf_vertical_format(lines)

    if not values:
        return None

    return ParsedFile(batch=batch, date=date, time=time, results=values)


def parse_file(path: Path) -> ParsedFile | None:
    """Parse a spectrometer file and return extracted results, or None if unparseable."""
    text = extract_text(path)
    if not text.strip():
        return None

    # Try TXT format first
    parsed = _parse_txt_format(text)
    if parsed:
        return parsed

    # Try PDF format
    return _parse_pdf_format(text)


def find_files(folder: Path) -> list[Path]:
    """Recursively find .txt and .pdf files in folder."""
    files: list[Path] = []
    if not folder.is_dir():
        return files
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".txt", ".pdf"):
            files.append(path)
    return sorted(files)
