"""Turn an uploaded PDF / email / text file into plain text for the extraction tool."""
import io
from email import policy
from email.parser import BytesParser

import pdfplumber

MAX_BYTES = 10 * 1024 * 1024


def extract_text(filename: str, content: bytes) -> tuple[str, dict]:
    if len(content) > MAX_BYTES:
        raise ValueError("File is larger than 10 MB.")
    name = filename.lower()
    if name.endswith(".pdf"):
        pages = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
        text = "\n\n".join(pages).strip()
        if not text:
            raise ValueError("No text found in this PDF (scanned image PDFs are not supported).")
        return text, {"pages": len(pages)}
    if name.endswith(".eml"):
        msg = BytesParser(policy=policy.default).parsebytes(content)
        body = msg.get_body(preferencelist=("plain", "html"))
        text = f"From: {msg['from']}\nTo: {msg['to']}\nSubject: {msg['subject']}\nDate: {msg['date']}\n\n"
        text += body.get_content() if body else ""
        return text.strip(), {"pages": 1}
    return content.decode("utf-8", errors="replace").strip(), {"pages": 1}
