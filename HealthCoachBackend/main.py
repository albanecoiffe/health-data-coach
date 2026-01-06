from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas import ChatRequest
from agent import (
    analyze_question,
    comparison_response_agent,
)
from services.comparisons import resolve_intent, infer_period_context_from_keys
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
    print("🔥 snapshots =", req.snapshots)
    print("🔥 meta =", req.meta)

    # ======================================================
    # 🔴 COMPARAISON FINALE — PRIORITÉ ABSOLUE
    # (snapshots + meta déjà fournis)
    # ======================================================
    if req.snapshots is not None and req.meta is not None:
        print("🟢 COMPARAISON FINALE — SNAPSHOTS PRÉSENTS")

        if not req.snapshots:
            raise HTTPException(
                status_code=400, detail="snapshots manquant pour comparaison"
            )

        left = req.snapshots.left
        right = req.snapshots.right

        raw_delta_distance = right.totals.distance_km - left.totals.distance_km
        raw_delta_duration = right.totals.duration_min - left.totals.duration_min
        raw_delta_sessions = right.totals.sessions - left.totals.sessions

        trend = (
            "UP"
            if raw_delta_distance > 0
            else "DOWN"
            if raw_delta_distance < 0
            else "STABLE"
        )

        delta = {
            "distance_km": round(abs(raw_delta_distance), 1),
            "duration_min": round(abs(raw_delta_duration)),
            "sessions": abs(raw_delta_sessions),
            "trend": trend,
        }

        reply = comparison_response_agent(
            message=req.message,
            metric=req.meta.get("metric", "DISTANCE"),
            delta=delta,
            left_period=(left.period.start, left.period.end),
            right_period=(right.period.start, right.period.end),
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
