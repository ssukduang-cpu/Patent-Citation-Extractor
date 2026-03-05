from __future__ import annotations

import re
from pathlib import Path

import fitz
import pdfplumber

from patentkit.layout import assign_columns
from patentkit.ocr import tesseract_available


def _line_noise(line: str) -> float:
    if not line:
        return 1.0
    alpha = sum(ch.isalpha() for ch in line)
    symbols = sum(not ch.isalnum() and not ch.isspace() for ch in line)
    return min(1.0, (symbols / max(len(line), 1)) + (0.5 if alpha / len(line) < 0.35 else 0.0))


def extract_structured(pdf_path: Path, doc_id: str) -> dict:
    pages = []
    full_text = []
    printed_line_numbers = False
    with pdfplumber.open(pdf_path) as pdf:
        global_col = 1
        for p_i, page in enumerate(pdf.pages, start=1):
            words = page.extract_words() or []
            if words:
                cols = assign_columns(words)
                page_cols = []
                for col_words in cols:
                    by_y = {}
                    for w in col_words:
                        key = round(w["top"], 1)
                        by_y.setdefault(key, []).append(w)
                    lines = []
                    for ln, key in enumerate(sorted(by_y), start=1):
                        ws = sorted(by_y[key], key=lambda i: i.get("x0", 0))
                        txt = " ".join(w["text"] for w in ws)
                        full_text.append(txt)
                        noise = _line_noise(txt)
                        lines.append(
                            {
                                "page_number": p_i,
                                "global_col_number": global_col,
                                "line_no": ln,
                                "text": txt,
                                "bbox": [ws[0].get("x0"), ws[0].get("top"), ws[-1].get("x1"), ws[-1].get("bottom")],
                                "line_number_source": "printed" if re.match(r"^\d+\s", txt) else "computed",
                                "noise_flag": noise > 0.55,
                                "noise_score": round(noise, 3),
                                "stable_id": f"{doc_id}:c{global_col}:l{ln}",
                            }
                        )
                        if re.match(r"^\d+\s", txt):
                            printed_line_numbers = True
                    page_cols.append({"global_col_number": global_col, "lines": lines})
                    global_col += 1
                pages.append({"page_number": p_i, "columns": page_cols})
            else:
                pages.append({"page_number": p_i, "columns": []})

    text = "\n".join(full_text).strip()
    ocr_used = False
    ocr_available = tesseract_available()
    if len(re.sub(r"\s+", "", text)) < 500:
        with fitz.open(pdf_path) as doc:
            extracted = "\n".join(page.get_text() for page in doc)
        if len(re.sub(r"\s+", "", extracted)) > len(re.sub(r"\s+", "", text)):
            text = extracted

    return {
        "pages": pages,
        "full_text": text,
        "printed_line_numbers": printed_line_numbers,
        "ocr_used": ocr_used,
        "ocr_available": ocr_available,
    }
