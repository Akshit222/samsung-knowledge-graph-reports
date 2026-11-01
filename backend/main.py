import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from backend/ or project root
_root_env = Path(__file__).resolve().parent.parent / ".env"
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env, override=True)
_backend_env = Path(__file__).resolve().parent / ".env"
if _backend_env.exists():
    load_dotenv(dotenv_path=_backend_env, override=True)

from fastapi import FastAPI
from app.routes import upload_excel
from app.routes import nl2sql
from app.routes import execute_query
from app.routes import db_meta
from app.routes import debug_chroma
from app.routes import refresh_schema
from app.routes import intelligent_ingest
from app.routes import summarize
from app.routes import graph as graph_routes
from utils.graph_service import ensure_constraints, is_available


app = FastAPI(
    title="NL2SQL Backend",
    version="1.0.0",
    description="API backend for natural language to SQL query execution"
)

app.include_router(upload_excel.router, prefix="/api/upload", tags=["upload"])
app.include_router(nl2sql.router, prefix="/api/nl2sql", tags=["NL2SQL"])
app.include_router(execute_query.router, prefix="/api/execute", tags=["Execute"])
app.include_router(db_meta.router, prefix="/api", tags=["DB Meta"])
app.include_router(debug_chroma.router, prefix="/api/debug", tags=["Debug"])
app.include_router(refresh_schema.router, prefix="/api/refresh", tags=["Schema Refresh"])
app.include_router(intelligent_ingest.router, prefix="/api/ingest", tags=["Intelligent Ingestion"])
app.include_router(summarize.router, prefix="/api/summarize", tags=["summarization"])
app.include_router(graph_routes.router, prefix="/api/graph", tags=["Knowledge Graph"])

# Initialise Neo4j constraints at startup (no-op if Neo4j is not configured)
@app.on_event("startup")
async def startup_event():
    if is_available():
        ensure_constraints()
        print("[Startup] Neo4j constraints ensured [OK]")
    else:
        print("[Startup] Neo4j not configured - graph features disabled (app works normally).")

# Health check route
# uvicorn main:app --reload
@app.get("/")
def root():
    return {"message": "Server is running fine"}

