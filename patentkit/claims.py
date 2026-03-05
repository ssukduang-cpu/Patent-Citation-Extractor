from __future__ import annotations

import re


def parse_claims(record: dict) -> dict:
    text = record.get("full_text", "")
    pattern = r"(?ms)^\s*(\d{1,3})\.\s+(.+?)(?=^\s*\d{1,3}\.\s+|\Z)"
    matches = re.finditer(pattern, text)
    claims = []
    for m in matches:
        n = int(m.group(1))
        body = " ".join(m.group(2).split())
        dep = re.findall(r"claim\s+(\d+)", body, re.I)
        independent = len(dep) == 0
        ctype = "method" if "method" in body.lower() else ("composition" if "composition" in body.lower() else "other")
        claims.append(
            {
                "number": n,
                "text": body,
                "independent": independent,
                "depends_on": [int(d) for d in dep],
                "claim_type": ctype,
                "stable_id": f"{record['doc_id']}:claim:{n}",
                "citation": "",
            }
        )
    by_ind = {}
    for c in claims:
        key = c["number"] if c["independent"] else (c["depends_on"][0] if c["depends_on"] else c["number"])
        by_ind.setdefault(key, []).append(c["number"])
    return {"doc_id": record["doc_id"], "claims": claims, "claim_sets_by_independent": by_ind}
