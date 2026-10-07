"""
DVT Preflight Validator — FastAPI entry point.

Stage 1: Generic ZIP Preflight Validation.
Validates the structure and consistency of YAML validation contracts against
SeaTunnel .conf execution plans.  Zero hardcoding — works with any migration
package.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.preflight import migration_router, router as preflight_router

app = FastAPI(
    title="DVT Preflight Validator",
    description=(
        "Stage 1 — Static preflight validation for migration packages. "
        "Upload a ZIP containing a validation YAML and a SeaTunnel .conf. "
        "The backend validates structure, internal consistency, and "
        "cross-checks the two files dynamically."
    ),
    version="1.0.0",
)

# CORS — allow all during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(preflight_router)
app.include_router(migration_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dvt-preflight-validator", "stage": 1}
