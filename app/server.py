from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import authenticate_user, clear_session_cookie, create_user, get_current_user, set_session_cookie
from app.db import Project, User, cleanup_inactive, get_session, init_db
from patentkit.claims import parse_claims
from patentkit.exports import export_all
from patentkit.llm import build_evidence_map, draft_from_evidence
from patentkit.retrieval import chunk_record, retrieve
from patentkit.structure import build_record
from patentkit.tables import extract_tables
from patentkit.validate import validate_citations

app = FastAPI(title="Patent Citation Extractor")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup():
    init_db()
    cleanup_inactive()


def require_user(request: Request, session: Session) -> User:
    user = get_current_user(request, session)
    if not user:
        raise HTTPException(status_code=401)
    return user


def project_dir(user_id: int, project_id: int) -> Path:
    p = Path("data") / str(user_id) / str(project_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", 302)
    projects = session.scalars(select(Project).where(Project.user_id == user.id)).all()
    return templates.TemplateResponse("projects.html", {"request": request, "user": user, "projects": projects})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register(request: Request, email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    if session.scalar(select(User).where(User.email == email.lower().strip())):
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})
    user = create_user(session, email, password)
    resp = RedirectResponse("/", 302)
    set_session_cookie(resp, user.id)
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = authenticate_user(session, email, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    resp = RedirectResponse("/", 302)
    set_session_cookie(resp, user.id)
    return resp


@app.post("/logout")
def logout():
    resp = RedirectResponse("/login", 302)
    clear_session_cookie(resp)
    return resp


@app.post("/projects")
def create_project(request: Request, name: str = Form(...), session: Session = Depends(get_session)):
    user = require_user(request, session)
    p = Project(user_id=user.id, name=name)
    session.add(p)
    session.commit()
    session.refresh(p)
    return RedirectResponse(f"/projects/{p.id}", 302)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404)
    base = project_dir(user.id, p.id)
    files = sorted([f.name for f in base.glob("*") if f.is_file()])
    return templates.TemplateResponse("project_detail.html", {"request": request, "project": p, "files": files})


@app.post("/projects/{project_id}/upload")
async def upload(
    project_id: int,
    request: Request,
    patent_pdf: UploadFile = File(...),
    addons: list[UploadFile] = File(default=[]),
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404)
    base = project_dir(user.id, p.id)
    patent_path = base / "patent.pdf"
    patent_path.write_bytes(await patent_pdf.read())
    addons_dir = base / "record_addons"
    addons_dir.mkdir(exist_ok=True)
    for a in addons:
        (addons_dir / a.filename).write_bytes(await a.read())
    record = build_record(patent_path)
    claims = parse_claims(record)
    tables = extract_tables(patent_path)
    md = f"# Patent {record['doc_id']}\n\nType: {record['doc_type']}\nCitation mode: {record['citation_mode']}\n"
    export_all(base, record, claims, tables, md, None, None)
    return RedirectResponse(f"/projects/{project_id}/viewer", 302)


@app.get("/projects/{project_id}/viewer", response_class=HTMLResponse)
def viewer(project_id: int, request: Request, q: str = "", include_noisy: bool = False, session: Session = Depends(get_session)):
    user = require_user(request, session)
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404)
    base = project_dir(user.id, p.id)
    record = json.loads((base / "patent_structured.json").read_text()) if (base / "patent_structured.json").exists() else {"pages": []}
    lines = []
    for pg in record.get("pages", []):
        for col in pg.get("columns", []):
            for l in col.get("lines", []):
                if not include_noisy and l.get("noise_flag"):
                    continue
                txt = l.get("text", "")
                if q and q.lower() not in txt.lower():
                    continue
                lines.append({"citation": f"Col. {l['global_col_number']}, ll. {l['line_no']}-{l['line_no']}", "text": txt})
    return templates.TemplateResponse("viewer.html", {"request": request, "project": p, "lines": lines, "q": q})


@app.post("/projects/{project_id}/draft")
def draft(
    project_id: int,
    request: Request,
    proceeding_type: str = Form("IPR"),
    drafting_mode: str = Form("Filing-Ready Draft"),
    claim_standard: str = Form(""),
    action: str = Form("claim_support"),
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404)
    base = project_dir(user.id, p.id)
    if not (base / "patent_structured.json").exists():
        raise HTTPException(400, "Upload a patent first")
    record = json.loads((base / "patent_structured.json").read_text())
    claims = json.loads((base / "claims.json").read_text())
    default_std = "Phillips" if proceeding_type == "IPR" else "BRI"
    standard = claim_standard or default_std
    chunks = chunk_record(record)
    excerpts = retrieve(chunks, " ".join(c["text"] for c in claims.get("claims", [])[:3]), 8)
    try:
        evidence = build_evidence_map(claims.get("claims", [])[:5], excerpts)
        out = draft_from_evidence(evidence, proceeding_type, standard, drafting_mode, action)
    except Exception as exc:
        out = f"LLM disabled or unavailable: {exc}"
        evidence = {"error": str(exc), "excerpts": excerpts}
    val = validate_citations(out, record)
    out += f"\n\n## Assumed Construction Standard\n{standard}\n\n## Citation Validation\nTotal citations: {val['total']}\nInvalid citations: {len(val['invalid'])}\n"
    (base / "draft.md").write_text(out, encoding="utf-8")
    (base / "draft.txt").write_text(out, encoding="utf-8")
    (base / "evidence_map.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    p.latest_draft = out
    p.updated_at = datetime.now(timezone.utc)
    session.commit()
    return RedirectResponse(f"/projects/{project_id}", 302)


@app.get("/projects/{project_id}/download/{name}")
def download(project_id: int, name: str, request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404)
    path = project_dir(user.id, p.id) / name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.post("/projects/{project_id}/delete")
def delete_project(project_id: int, request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404)
    shutil.rmtree(project_dir(user.id, p.id), ignore_errors=True)
    session.delete(p)
    session.commit()
    return RedirectResponse("/", 302)


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})


@app.post("/settings/delete-data")
def delete_data(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    shutil.rmtree(Path("data") / str(user.id), ignore_errors=True)
    session.delete(user)
    session.commit()
    resp = RedirectResponse("/register", 302)
    clear_session_cookie(resp)
    return resp
