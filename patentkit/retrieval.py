from __future__ import annotations

from rank_bm25 import BM25Okapi


def chunk_record(record: dict) -> list[dict]:
    chunks=[]
    for page in record.get("pages",[]):
        for col in page.get("columns",[]):
            lines=[ln for ln in col.get("lines",[]) if not ln.get("noise_flag")]
            for i in range(0, len(lines), 4):
                group=lines[i:i+4]
                if not group:
                    continue
                txt=" ".join(g["text"] for g in group)
                chunks.append({"text":txt,"section_type":"detailed_description","citation":f"Col. {col['global_col_number']}, ll. {group[0]['line_no']}-{group[-1]['line_no']}"})
    return chunks


def retrieve(chunks: list[dict], query: str, k: int = 8) -> list[dict]:
    if not chunks:
        return []
    tokenized=[c["text"].lower().split() for c in chunks]
    bm25=BM25Okapi(tokenized)
    scores=bm25.get_scores(query.lower().split())
    order=sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [chunks[i] for i in order]
