try:
    import pypdf as _pdf_lib          # modern successor to PyPDF2
    _PDF_BACKEND = "pypdf"
except ImportError:
    try:
        import PyPDF2 as _pdf_lib     # legacy fallback
        _PDF_BACKEND = "pypdf2"
    except ImportError:
        _pdf_lib = None
        _PDF_BACKEND = None

import docx
import re


class ResumeParser:
    """Parser for extracting text from resume files."""

    # Robust phone regex supporting:
    #   +91-XXXXX-XXXXX  (Indian with dashes)
    #   +91 9999900000   (Indian international)
    #   +1 (555) 123-4567 (US)
    #   987-654-3210     (US local)
    #   9876543210       (plain 10-digit Indian mobile, starts with 6-9)
    _PHONE_RE = re.compile(
        r"""
        (?:
            # Option A: international prefix + grouped digits with separators
            (?:\+|00)\d{1,3}[\s\-.]?
            \(?\d{2,5}\)?[\s\-.]
            \d{2,5}(?:[\s\-.]?\d{2,5})*
          |
            # Option B: local grouped (e.g. 987-654-3210, (555) 123-4567)
            \(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}
          |
            # Option C: plain 10-digit Indian mobile (starts 6–9)
            [6-9]\d{9}
        )
        (?!\d)
        """,
        re.VERBOSE,
    )

    def extract_text(self, file: str) -> str:
        """Extract text from PDF, DOCX, or TXT files."""
        if file.endswith(".pdf"):
            if _pdf_lib is None:
                raise ImportError("No PDF library found. Install pypdf: pip install pypdf")
            with open(file, "rb") as f:
                reader = _pdf_lib.PdfReader(f)
                return "".join(p.extract_text() or "" for p in reader.pages)

        if file.endswith(".docx"):
            doc = docx.Document(file)
            return "\n".join(p.text for p in doc.paragraphs)

        if file.endswith(".txt"):
            with open(file, "r", encoding="utf-8") as f:
                return f.read()

        return ""

    def parse(self, file: str) -> dict:
        """Parse resume file and extract basic information."""
        text = self.extract_text(file)

        # Extract email
        emails = re.findall(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}", text)

        # Extract phone — supports plain 10-digit, +91, +1, and most
        # international formats (country code up to 3 digits).
        raw_phones = self._PHONE_RE.findall(text)
        # Normalise: keep only digits + leading +
        phones = []
        seen   = set()
        for p in raw_phones:
            digits = re.sub(r"[^\d+]", "", p)
            digit_only = re.sub(r"\D", "", digits)
            # Must have at least 7 digits and NOT be a plain 4-digit year
            if len(digit_only) >= 7 and not re.fullmatch(r'20\d{2}', digit_only) and digits not in seen:
                phones.append(digits)
                seen.add(digits)

        # Extract name: first non-empty line that has no special chars and ≤5 words
        name = ""
        for line in text.replace('\r\n', '\n').split('\n'):
            line = line.strip()
            if not line:
                continue
            if (not re.search(r'[@|:/\d]', line)
                    and len(line.split()) <= 5
                    and len(line) > 3):
                name = line
                break

        return {
            "raw_text":   text,
            "name":       name,
            "email":      emails[0] if emails else "",
            "phone":      phones[0] if phones else "",
            "all_phones": phones,
        }