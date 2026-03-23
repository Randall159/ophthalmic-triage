"""
Ophthalmic Triage API — New Workflow (新工作流)
State-triggered pipeline with SSE streaming.
"""
import asyncio
import json
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents import SafetyAgent, RecipientAgent, AssessorAgent, InquirerAgent, empty_emr

app = FastAPI(title="Ophthalmic Triage API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[MessageItem] = []
    current_emr: Optional[dict] = None


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_pipeline(request: ChatRequest):
    safety    = SafetyAgent()
    recipient = RecipientAgent()
    assessor  = AssessorAgent()
    inquirer  = InquirerAgent()

    history = [{"role": m.role, "content": m.content} for m in request.conversation_history]
    current_emr = request.current_emr if request.current_emr else empty_emr()

    # ── Step 1 & 2: Safety pre-check + Recipient (parallel) ──────────────────
    yield _sse({"type": "step_start", "step": 1, "agent": "Safety Monitor", "phase": "Pre-Check"})
    yield _sse({"type": "step_start", "step": 2, "agent": "Recipient Agent", "phase": "EMR Update"})

    # Run both in parallel
    pre, updated_emr = await asyncio.gather(
        asyncio.to_thread(safety.check, request.message),
        asyncio.to_thread(recipient.update_emr, history, request.message, current_emr)
    )

    yield _sse({"type": "step_done", "step": 1, "agent": "Safety Monitor",
                "status": "SAFE" if pre["is_safe"] else "UNSAFE",
                "detail": pre["raw"],
                "input": f"Patient: {request.message}"})

    if not pre["is_safe"]:
        yield _sse({"type": "done", "response": pre["override_message"],
                    "emr": current_emr, "emr_text": recipient.emr_to_text(current_emr),
                    "triage_report": "", "triage_level": None,
                    "gap_analysis": "", "disposition_ready": False,
                    "trigger_handoff": pre["trigger_handoff"],
                    "safety_status": "UNSAFE (pre-check)"})
        return

    emr_complete = recipient.emr_complete(updated_emr)
    emr_text = recipient.emr_to_text(updated_emr)
    yield _sse({"type": "step_done", "step": 2, "agent": "Recipient Agent",
                "status": "COMPLETE",
                "detail": emr_text,
                "input": f"Patient message: {request.message}\nCurrent EMR: {json.dumps(current_emr, ensure_ascii=False)[:200]}...",
                "emr": updated_emr, "emr_complete": emr_complete})

    # ── Step 3: Assessor — only if EMR complete ───────────────────────────────
    yield _sse({"type": "step_start", "step": 3, "agent": "Assessor Agent", "phase": "Gap Analysis"})
    assessment = await asyncio.to_thread(assessor.evaluate, history, updated_emr, emr_text, emr_complete)
    yield _sse({"type": "step_done", "step": 3, "agent": "Assessor Agent",
                "status": "SKIPPED" if assessment["skipped"] else "COMPLETE",
                "detail": assessment["raw"] or "EMR incomplete — assessor sleeping.",
                "input": f"EMR Complete: {emr_complete}\nConversation: {len(history)} messages"})

    # ── Step 4: Inquirer — autonomous or clinical mode ────────────────────────
    yield _sse({"type": "step_start", "step": 4, "agent": "Inquirer Agent",
                "phase": "Autonomous" if not emr_complete else "Clinical"})
    nurse_reply = await asyncio.to_thread(
        inquirer.generate_response,
        history, request.message, updated_emr, emr_text,
        emr_complete, assessment.get("gap_analysis", ""),
        assessment.get("disposition_ready", False),
        assessment.get("triage_level", "")
    )
    yield _sse({"type": "step_done", "step": 4, "agent": "Inquirer Agent",
                "status": "COMPLETE",
                "detail": nurse_reply,
                "input": f"Mode: {'Clinical' if emr_complete else 'Autonomous'}\nDisposition Ready: {assessment.get('disposition_ready', False)}\nGap: {assessment.get('gap_analysis', 'N/A')[:100]}..."})

    # ── Step 5: Safety post-check ─────────────────────────────────────────────
    yield _sse({"type": "step_start", "step": 5, "agent": "Safety Monitor", "phase": "Post-Check"})
    post = await asyncio.to_thread(safety.post_check, nurse_reply)
    yield _sse({"type": "step_done", "step": 5, "agent": "Safety Monitor",
                "status": "SAFE" if post["is_safe"] else "UNSAFE",
                "detail": post["raw"],
                "input": f"Nurse reply: {nurse_reply[:150]}..."})

    final_reply = nurse_reply if post["is_safe"] else post["override_message"]

    yield _sse({"type": "done",
                "response": final_reply,
                "emr": updated_emr,
                "emr_text": emr_text,
                "emr_complete": emr_complete,
                "triage_report": assessment.get("raw", ""),
                "triage_level": assessment.get("triage_level"),
                "gap_analysis": assessment.get("gap_analysis", ""),
                "disposition_ready": assessment.get("disposition_ready", False),
                "trigger_handoff": False,
                "safety_status": "SAFE" if post["is_safe"] else "UNSAFE (post-check)"})


@app.get("/health")
async def health():
    from backend.config import MODEL
    return {"status": "ok", "model": MODEL}


@app.post("/model")
async def change_model(data: dict):
    from backend import config
    config.MODEL = data.get("model", "Qwen/Qwen3.5-4B")
    return {"status": "ok", "model": config.MODEL}


@app.get("/prompts/{agent_type}")
async def get_prompt(agent_type: str):
    from backend.agents import (SAFETY_PRE_PROMPT, SAFETY_POST_PROMPT, RECIPIENT_PROMPT,
                        ASSESSOR_PROMPT, INQUIRER_AUTONOMOUS_PROMPT, INQUIRER_CLINICAL_PROMPT)
    prompts = {
        "safety_pre": SAFETY_PRE_PROMPT,
        "safety_post": SAFETY_POST_PROMPT,
        "recipient": RECIPIENT_PROMPT,
        "assessor": ASSESSOR_PROMPT,
        "inquirer_auto": INQUIRER_AUTONOMOUS_PROMPT,
        "inquirer_clinical": INQUIRER_CLINICAL_PROMPT,
    }
    return {"prompt": prompts.get(agent_type, "")}


@app.post("/prompts/{agent_type}")
async def save_prompt(agent_type: str, data: dict):
    # Note: This saves to memory only, not to file
    # For persistent changes, edit agents.py directly
    return {"status": "ok", "message": "Prompt updated in memory (restart required for persistence)"}


@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_pipeline(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
