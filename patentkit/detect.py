from __future__ import annotations

import re


def detect_doc_type(text: str) -> str:
    t = text.lower()
    if "united states patent" in t and "patent" in t:
        return "granted_patent"
    if "patent application publication" in t or re.search(r"\[\d{4}\]", text):
        return "published_application"
    return "unknown"


def citation_mode(doc_type: str, has_paragraph_markers: bool) -> str:
    if doc_type == "granted_patent":
        return "col_line"
    if doc_type == "published_application" and has_paragraph_markers:
        return "paragraph"
    if doc_type == "published_application":
        return "page_paragraph_computed"
    return "page_paragraph_computed"
