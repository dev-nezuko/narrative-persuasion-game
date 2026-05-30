import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router
from .session_manager import InvalidSessionId, SessionNotFound

app = FastAPI(title="Doorman Game API")

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("DOORMAN_CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(InvalidSessionId)
def invalid_session_id(_request: Request, _exc: InvalidSessionId):
    return JSONResponse(status_code=422, content={"detail": "Invalid session identifier"})


@app.exception_handler(SessionNotFound)
def session_not_found(_request: Request, _exc: SessionNotFound):
    return JSONResponse(status_code=404, content={"detail": "Session not found or expired"})


app.include_router(router)
