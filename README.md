# Patent Citation Extractor (Replit-ready)

FastAPI + CLI app for multi-user USPTO patent PDF ingestion and AI-assisted drafting for IPR / ex parte reexam workflows.

## Run in Replit
1. Create `.env` with at least:
   - `SESSION_SECRET_KEY=change-me`
   - Optional: `ANTHROPIC_API_KEY=...` or `OPENAI_API_KEY=...`
   - Optional: `LLM_BACKEND=anthropic` or `openai`
2. Install deps: `pip install -r requirements.txt`
3. Run app: `uvicorn app.server:app --host 0.0.0.0 --port 3000`
4. Open web UI, register, create project, upload patent PDF (+ optional prosecution PDFs).

## Replit config
- `.replit` maps external 80 to internal 3000.
- `replit.nix` includes `tesseract`.

## Web features
- Email/password auth with bcrypt hashing and per-user data isolation.
- Project upload pipeline: structured JSON, claims JSON, tables extraction, viewer search.
- Proceeding type + claim construction defaults:
  - IPR => Phillips
  - Ex Parte Reexam => BRI default (override supported)
- Two-pass drafting pipeline when LLM configured:
  - Pass 1 evidence map (JSON)
  - Pass 2 filing-ready / neutral draft with required disclaimer
- Citation validator checks generated citations against extracted record anchors.
- Export artifacts: `patent_structured.json`, `claims.json`, `patent.md`, `draft.md`, `draft.txt`, `tables.json`, `evidence_map.json`.
- Data deletion: per-project and full account delete.

## CLI
Batch process PDFs:
```bash
python cli.py ./pdfs --out ./cli_output
```
Optional drafting (requires LLM key):
```bash
python cli.py ./pdfs --out ./cli_output --draft
```

## Notes on OCR
If text extraction is insufficient, the pipeline checks whether `tesseract` is installed. If missing, OCR is marked unavailable and the UI artifacts reflect this without crashing.

## Tests
Run:
```bash
pytest
```
