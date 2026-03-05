from __future__ import annotations

import re


def detect_figure_refs(record: dict) -> list[dict]:
    refs=[]
    pattern=re.compile(r"FIG\.?\s*([0-9]+[A-Z]?)", re.I)
    for page in record.get("pages",[]):
        for col in page.get("columns",[]):
            for line in col.get("lines",[]):
                for m in pattern.finditer(line.get("text","")):
                    refs.append({"figure":m.group(1),"citation":f"Col. {line['global_col_number']}, ll. {line['line_no']}-{line['line_no']}"})
    return refs
