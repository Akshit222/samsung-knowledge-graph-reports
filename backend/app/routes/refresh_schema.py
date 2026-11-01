# backend/app/routes/refresh_schema.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import traceback
from utils.db_utils import refresh_schema_cache
from utils.chroma_utils import sync_chroma_schema_embeddings

router = APIRouter()

class DBRefreshRequest(BaseModel):
    db_name: str

@router.post("/")
def refresh_schema_and_embeddings(request: DBRefreshRequest):
    """
    Refresh both SQLAlchemy schema cache and Chroma embeddings for the selected DB.
    """
    try:
        db_name = request.db_name
        refresh_schema_cache(db_name)
        sync_chroma_schema_embeddings(db_name)

        # Sync schema to Neo4j knowledge graph if configured
        try:
            from utils.graph_service import is_available, ensure_constraints, sync_db_schema_to_graph
            from utils.db import get_engine_for_db
            from sqlalchemy import inspect as sa_inspect
            if is_available():
                ensure_constraints()
                inspector = sa_inspect(get_engine_for_db(db_name))
                tables_info = []
                for tbl in inspector.get_table_names():
                    cols = [{"name": c["name"], "type": str(c.get("type", ""))} for c in inspector.get_columns(tbl)]
                    fks = [{"referred_table": fk["referred_table"]} for fk in inspector.get_foreign_keys(tbl) if fk.get("referred_table")]
                    tables_info.append({"table_name": tbl, "columns": cols, "foreign_keys": fks})
                sync_db_schema_to_graph(db_name, tables_info)
                print(f"[SchemaRefresh] Synced {len(tables_info)} tables to Neo4j knowledge graph.")
        except Exception as graph_err:
            print(f"[SchemaRefresh] (info) Graph schema sync skipped: {graph_err}")
        
        return {
            "status": "success",
            "message": f"Schema cache + embeddings refreshed for '{db_name}' ✅"
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh schema for '{request.db_name}': {e}"
        )

