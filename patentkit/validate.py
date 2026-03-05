from __future__ import annotations

import re


def citation_index(record: dict) -> set[str]:
    idx=set()
    for p in record.get("pages",[]):
        for c in p.get("columns",[]):
            for l in c.get("lines",[]):
                idx.add(f"Col. {l['global_col_number']}, ll. {l['line_no']}-{l['line_no']}")
    return idx


def validate_citations(text: str, record: dict) -> dict:
    cites = re.findall(r"Col\.\s*\d+,\s*ll\.\s*\d+(?:-\d+)?|¶\[\d{4}\]|Page\s*\d+,\s*¶\d+", text)
    valid = citation_index(record)
    invalid=[c for c in cites if c not in valid and c.startswith("Col.")]
    return {"total":len(cites),"invalid":invalid,"ok":len(invalid)==0}
