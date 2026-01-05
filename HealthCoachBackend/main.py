from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas import ChatRequest
from agent import (
    analyze_question,
    comparison_response_agent,
)
from services.comparisons import resolve_intent
from services.intent import (
    apply_backend_overrides,
    route_decision,
)

app = FastAPI()


# ======================================================
# ❌ HANDLER ERREUR VALIDATION
# ======================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("❌ ERREUR DE VALIDATION FASTAPI")
    print("BODY :", await request.body())
    print("DETAILS :", exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/")
def root():
    return {"status": "ok"}


# ======================================================
# 💬 ENDPOINT CHAT
# ======================================================
@app.post("/chat")
def chat(req: ChatRequest):
    print("\n================= CHAT =================")
    print("📝 MESSAGE :", req.message)
    print("📦 SNAPSHOT REÇU")
    print("   Période :", req.snapshot.period.start, "→", req.snapshot.period.end)

    # ======================================================
    # 🔴 COMPARAISON FINALE — PRIORITÉ ABSOLUE
    # (snapshots + meta déjà fournis)
    # ======================================================
    if req.snapshots is not None and req.meta is not None:
        print("🟢 COMPARAISON FINALE — SNAPSHOTS PRÉSENTS")

        left = req.snapshots.left
        right = req.snapshots.right

        delta = {
            "distance_km": round(left.totals.distance_km - right.totals.distance_km, 1),
            "duration_min": round(left.totals.duration_min - right.totals.duration_min),
            "sessions": left.totals.sessions - right.totals.sessions,
        }

        reply = comparison_response_agent(
            message=req.message,
            metric=req.meta.get("metric", "DISTANCE"),
            delta=delta,
            left_label=req.meta.get("left_label", "période 1"),
            right_label=req.meta.get("right_label", "période 2"),
        )

        return {"reply": reply}

    # ======================================================
    # 🔵 FLOW NORMAL — ANALYSE + VERROUS BACKEND
    # ======================================================
    decision = analyze_question(
        req.message,
        (req.snapshot.period.start, req.snapshot.period.end),
    )

    decision = apply_backend_overrides(req.message, decision)

    print("\n================= DECISION =================")
    print("🧠 DECISION :", decision)

    # ======================================================
    # 🧭 ROUTING CENTRALISÉ
    # ======================================================
    return route_decision(req, decision)
