from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ai import generate_structured, ollama_status
from .models import AnalyzeRequest, ContinueRequest, DecisionRequest, PersonalContextRequest
from .storage import case_from_row, connect, create_case, get_case, get_personal_context, init_db, list_cases, list_decisions, replay, save_personal_context, update_case, clear_all, now_iso
from .workflow import analysis_from_context, context_from_problem, question_from_context, title_for

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

app = FastAPI(title="ContextLens API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"ok": True, "backend": "connected", "ai": ollama_status(), "storage": "sqlite"}


@app.get("/api/v1/cases")
def cases() -> dict[str, Any]:
    return {"cases": list_cases()}


@app.get("/api/v1/decisions")
def decisions() -> dict[str, Any]:
    return {"decisions": list_decisions()}


@app.post("/api/v1/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    problem = request.problem.strip()
    if len(problem) < 20:
        raise HTTPException(status_code=422, detail={"code": "invalid_input", "message": "Describe the situation in at least 20 characters so ContextLens has something concrete to work with."})
    case_id = uuid.uuid4().hex[:12]
    context = context_from_problem(problem, request.about)
    question = question_from_context(context, problem)
    timestamp = now_iso()
    case = {"id": case_id, "title": title_for(problem), "preview": problem[:150], "status": "question", "created_at": timestamp, "updated_at": timestamp, "problem": problem, "about": request.about, "mode": request.mode, "use_personal_context": request.use_personal_context, "context": context, "question": question, "analysis": {}}
    saved = create_case(case)
    personal = get_personal_context() if request.use_personal_context else None
    return {"case": saved, "stage": "context", "context": context, "question": question, "ai": {**ollama_status(), "used_fallback": True}, "personal_context_used": bool(personal and personal.get("enabled"))}


@app.post("/api/v1/analyze/continue")
def continue_analysis(request: ContinueRequest) -> dict[str, Any]:
    case = get_case(request.case_id)
    if not case:
        raise HTTPException(status_code=404, detail={"code": "case_not_found", "message": "This case could not be found."})
    answer = request.answer.strip()
    question = {**case["question"], "answer": answer or None, "skipped": request.skipped}
    fallback = analysis_from_context(case["context"], case["problem"], answer, request.skipped)
    analysis, ai = generate_structured(case["problem"], case["context"], fallback)
    updated = update_case(case["id"], status="analysis", question=question, analysis=analysis)
    return {"case": updated, "stage": "analysis", "analysis": analysis, "ai": ai}


@app.post("/api/v1/analyze/decision")
def save_decision(request: DecisionRequest) -> dict[str, Any]:
    case = get_case(request.case_id)
    if not case:
        raise HTTPException(status_code=404, detail={"code": "case_not_found", "message": "This case could not be found."})
    decision = {"text": request.decision.strip(), "confidence": request.confidence, "review_date": request.review_date, "saved_at": now_iso()}
    updated = update_case(case["id"], status="decision_saved", decision=decision)
    return {"case": updated, "decision": decision}


@app.get("/api/v1/cases/{case_id}/replay")
def case_replay(case_id: str) -> dict[str, Any]:
    result = replay(case_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "case_not_found", "message": "This case could not be found."})
    return result


@app.post("/api/v1/memory/personal")
def save_memory(request: PersonalContextRequest) -> dict[str, Any]:
    return {"personal_context": save_personal_context(request.content.strip(), request.enabled)}


@app.get("/api/v1/memory/personal")
def get_memory() -> dict[str, Any]:
    return {"personal_context": get_personal_context()}


@app.delete("/api/v1/data")
def delete_data() -> dict[str, Any]:
    clear_all()
    return {"ok": True, "message": "Local ContextLens data cleared."}


if PUBLIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=PUBLIC_DIR), name="assets")


@app.get("/manus-routes.json")
def routes_manifest() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "manus-routes.json", media_type="application/json")


@app.get("/{path:path}")
def frontend(path: str = "") -> FileResponse:
    requested = PUBLIC_DIR / path
    if path and requested.is_file() and PUBLIC_DIR in requested.parents:
        return FileResponse(requested)
    return FileResponse(PUBLIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "3000")), reload=False)
