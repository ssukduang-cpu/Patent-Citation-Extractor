from __future__ import annotations

from pathlib import Path

from patentkit.utils import write_json


def export_all(base: Path, record: dict, claims: dict, tables: dict, patent_md: str, draft_md: str | None, evidence_map: dict | None) -> None:
    write_json(base / "patent_structured.json", record)
    write_json(base / "claims.json", claims)
    write_json(base / "tables.json", tables)
    (base / "patent.md").write_text(patent_md, encoding="utf-8")
    if draft_md:
        (base / "draft.md").write_text(draft_md, encoding="utf-8")
        (base / "draft.txt").write_text(draft_md, encoding="utf-8")
    if evidence_map is not None:
        write_json(base / "evidence_map.json", evidence_map)
