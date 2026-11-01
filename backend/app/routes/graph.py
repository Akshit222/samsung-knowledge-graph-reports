"""
Graph API Routes — Semantic Knowledge Graph Explorer endpoints.

All Cypher is parameterised and relationship types are whitelist-validated
inside graph_service.py.  No LLM-generated query is executed directly.
"""
from __future__ import annotations

import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from utils.graph_service import (
    is_available,
    get_full_graph,
    get_entity_by_id,
    get_entity_neighbors,
    search_entities,
    semantic_search_entities,
    get_table_relationships,
    sync_db_schema_to_graph,
    ensure_constraints,
)
from utils.db import root_engine, get_engine_for_db
from sqlalchemy import text, inspect as sa_inspect

router = APIRouter()


# ─── Health / status ─────────────────────────────────────────────────────────

@router.get("/status")
def graph_status():
    """Return whether the Neo4j graph layer is active."""
    available = is_available()
    return {
        "graph_available": available,
        "message": "Neo4j connected ✅" if available else
                   "Neo4j not configured — graph features disabled (application still works normally).",
    }


# ─── Full graph snapshot ──────────────────────────────────────────────────────

@router.get("/")
def get_graph(
    db_name: Optional[str] = Query(None, description="Filter by database name"),
    limit: int = Query(200, ge=1, le=500),
):
    """Return a sampled graph of nodes and edges for visualisation."""
    if not is_available():
        return {"nodes": [], "edges": [], "graph_available": False}
    try:
        data = get_full_graph(db_name=db_name, limit=limit)
        data["graph_available"] = True
        return data
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Entity CRUD ──────────────────────────────────────────────────────────────

@router.get("/entities/{entity_id}")
def get_entity(entity_id: str):
    """Return a single entity node by ID."""
    if not is_available():
        raise HTTPException(status_code=503, detail="Graph layer not available.")
    entity = get_entity_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")
    return entity


@router.get("/entities/{entity_id}/neighbors")
def get_neighbors(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3),
):
    """Return nodes and edges reachable within `depth` hops from an entity."""
    if not is_available():
        raise HTTPException(status_code=503, detail="Graph layer not available.")
    try:
        return get_entity_neighbors(entity_id, depth=depth)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Search ───────────────────────────────────────────────────────────────────

@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Partial-match search on entity names."""
    if not is_available():
        return {"results": [], "graph_available": False}
    try:
        results = search_entities(q, entity_type=entity_type, limit=limit)
        return {"results": results, "graph_available": True}
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Semantic search ──────────────────────────────────────────────────────────

class SemanticSearchRequest(BaseModel):
    question: str = Field(..., min_length=1)
    db_name: Optional[str] = None


@router.post("/semantic-search")
def semantic_search(request: SemanticSearchRequest):
    """
    Extract entities from `question`, find matching graph nodes, return
    related nodes + edges for context injection.
    """
    if not is_available():
        return {"nodes": [], "edges": [], "graph_available": False, "entities_found": []}
    try:
        from utils.entity_extractor import extract_question_entities
        entity_names = extract_question_entities(request.question)
        graph_ctx = semantic_search_entities(entity_names, db_name=request.db_name)
        graph_ctx["entities_found"] = entity_names
        graph_ctx["graph_available"] = True
        return graph_ctx
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Table relationships ───────────────────────────────────────────────────────

@router.get("/tables/{db_name}/relationships")
def table_relationships(db_name: str):
    """Return all verified table-to-table relationships for a database."""
    if not is_available():
        return {"relationships": [], "graph_available": False}
    try:
        rels = get_table_relationships(db_name)
        return {"relationships": rels, "graph_available": True}
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Schema → Graph sync ──────────────────────────────────────────────────────

@router.post("/sync-schema/{db_name}")
def sync_schema(db_name: str):
    """
    Sync the DB schema (tables, columns, FK relationships) into the graph.
    Idempotent — safe to call repeatedly.
    """
    if not is_available():
        return {"status": "skipped", "message": "Graph layer not available."}
    try:
        ensure_constraints()
        engine = get_engine_for_db(db_name)
        inspector = sa_inspect(engine)
        tables_info = []
        for table_name in inspector.get_table_names():
            columns = [
                {"name": c["name"], "type": str(c.get("type", ""))}
                for c in inspector.get_columns(table_name)
            ]
            fks = [
                {"referred_table": fk["referred_table"]}
                for fk in inspector.get_foreign_keys(table_name)
                if fk.get("referred_table")
            ]
            tables_info.append({
                "table_name": table_name,
                "columns": columns,
                "foreign_keys": fks,
            })
        sync_db_schema_to_graph(db_name, tables_info)
        return {
            "status": "success",
            "message": f"Synced {len(tables_info)} tables for '{db_name}' into graph.",
            "tables_synced": len(tables_info),
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
