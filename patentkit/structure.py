from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from patentkit.detect import citation_mode, detect_doc_type
from patentkit.extract_text import extract_structured
from patentkit.utils import sha256_bytes


def build_record(pdf_path: Path) -> dict:
    data = pdf_path.read_bytes()
    doc_id = uuid4().hex[:12]
    extracted = extract_structured(pdf_path, doc_id)
    full_text = extracted["full_text"]
    doc_type = detect_doc_type(full_text)
    has_para = bool(re.search(r"\[\d{4}\]", full_text))
    mode = citation_mode(doc_type, has_para)
    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "citation_mode": mode,
        "ocr_used": extracted["ocr_used"],
        "ocr_available": extracted["ocr_available"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256_bytes(data),
        "computed_citation_warning": mode != "col_line" and not has_para,
        "pages": extracted["pages"],
        "full_text": full_text,
    }
