from __future__ import annotations

import argparse
import json
from pathlib import Path

from patentkit.claims import parse_claims
from patentkit.exports import export_all
from patentkit.figures import detect_figure_refs
from patentkit.llm import build_evidence_map, draft_from_evidence
from patentkit.retrieval import chunk_record, retrieve
from patentkit.structure import build_record
from patentkit.tables import extract_tables


def patent_md(record: dict, claims: dict) -> str:
    lines = [f"# Patent {record['doc_id']}", f"- Type: {record['doc_type']}", f"- Citation mode: {record['citation_mode']}"]
    if record.get("computed_citation_warning"):
        lines.append("- WARNING: Computed citations are in use.")
    lines.append("## Claims")
    for c in claims["claims"]:
        lines.append(f"- Claim {c['number']}: {c['text'][:180]}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("--out", default="cli_output")
    ap.add_argument("--draft", action="store_true")
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    for pdf in Path(args.input_dir).glob("*.pdf"):
        record = build_record(pdf)
        claims = parse_claims(record)
        tables = extract_tables(pdf)
        md = patent_md(record, claims)
        draft = None
        evidence = None
        if args.draft:
            chunks = chunk_record(record)
            ex = retrieve(chunks, "support for claim limitations", 6)
            evidence = build_evidence_map(claims["claims"][:3], ex)
            draft = draft_from_evidence(evidence, "IPR", "Phillips", "Filing-Ready Draft", "claim_support")
        base = out_root / pdf.stem
        base.mkdir(exist_ok=True)
        export_all(base, record, claims, tables, md, draft, evidence)
        (base / "figures.json").write_text(json.dumps(detect_figure_refs(record), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
