from __future__ import annotations

from pathlib import Path

import pdfplumber


def extract_tables(pdf_path: Path) -> dict:
    tables=[]
    with pdfplumber.open(pdf_path) as pdf:
        for i,page in enumerate(pdf.pages, start=1):
            for t_i,table in enumerate(page.extract_tables() or [], start=1):
                tables.append({"page":i,"table_index":t_i,"rows":table})
    return {"tables":tables}
