"""
Graph Service — Neo4j integration for Semantic Knowledge Graph.

Wraps all Neo4j operations with graceful degradation: if NEO4J_URI is
not configured or the database is unreachable the rest of the application
continues to work normally — graph features are simply skipped.

Node labels used:
  - Document       : a processed file / data source
  - Entity         : a business entity extracted from a document
  - DatabaseTable  : a MySQL table
  - DatabaseColumn : a column within a table

Relationship types:
  - CONTAINS        : Document → Entity  /  DatabaseTable → DatabaseColumn
  - RELATED_TO      : Entity ↔ Entity  /  Table ↔ Table (semantic or FK-verified)
  - BELONGS_TO      : Entity → Document (back-ref)
  - REFERENCES      : Entity → DatabaseTable (provenance link)
"""
from __future__ import annotations

import os
import traceback
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pathlib import Path

# Load .env from backend/ or project root
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env)
else:
    load_dotenv()

# ─── optional Neo4j import ────────────────────────────────────────────────────
try:
    from neo4j import GraphDatabase, exceptions as neo4j_exceptions  # type: ignore
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

_driver = None  # module-level singleton


# ─── Driver lifecycle ─────────────────────────────────────────────────────────

def get_driver():
    """Return a cached Neo4j driver, or None if not configured / unavailable."""
    global _driver
    if _driver is not None:
        return _driver
    if not NEO4J_AVAILABLE:
        print("[GraphService] neo4j package not installed — graph features disabled.")
        return None

    neo4j_uri = os.getenv("NEO4J_URI", "")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")

    if not neo4j_uri or not neo4j_password:
        print("[GraphService] NEO4J_URI / NEO4J_PASSWORD not set — graph features disabled.")
        return None
    try:
        _driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        _driver.verify_connectivity()
        print(f"[GraphService] [OK] Connected to Neo4j at {neo4j_uri}")
        return _driver
    except Exception as exc:
        print(f"[GraphService] [WARN] Could not connect to Neo4j: {exc}")
        _driver = None
        return None



def close_driver():
    global _driver
    if _driver:
        try:
            _driver.close()
        except Exception:
            pass
        _driver = None


def is_available() -> bool:
    return get_driver() is not None


# ─── Helper ───────────────────────────────────────────────────────────────────

def _run(cypher: str, params: Optional[Dict] = None) -> List[Dict]:
    """
    Execute a Cypher query and return a list of record dicts.
    Returns [] silently when Neo4j is unavailable.
    """
    driver = get_driver()
    if driver is None:
        return []
    params = params or {}
    try:
        with driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(r) for r in result]
    except Exception as exc:
        print(f"[GraphService] Cypher error: {exc}\n  Query: {cypher[:200]}")
        traceback.print_exc()
        return []


# ─── Schema creation ──────────────────────────────────────────────────────────

def ensure_constraints():
    """Create uniqueness constraints (idempotent)."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document)       REQUIRE d.id         IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity)         REQUIRE e.id         IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:DatabaseTable)  REQUIRE t.unique_key IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:DatabaseColumn) REQUIRE c.unique_key IS UNIQUE",
    ]
    for c in constraints:
        _run(c)


# ─── Document nodes ───────────────────────────────────────────────────────────

def upsert_document(
    doc_id: str,
    name: str,
    source_db: str,
    source_table: str,
    file_type: str = "unknown",
) -> None:
    """Create or update a Document node."""
    _run(
        """
        MERGE (d:Document {id: $id})
        SET   d.name         = $name,
              d.source_db    = $source_db,
              d.source_table = $source_table,
              d.file_type    = $file_type,
              d.updated_at   = timestamp()
        """,
        {"id": doc_id, "name": name, "source_db": source_db,
         "source_table": source_table, "file_type": file_type},
    )


# ─── Entity nodes & relationships ─────────────────────────────────────────────

def upsert_entity(
    entity_id: str,
    name: str,
    entity_type: str,
    source_doc_id: str,
    source_row: Optional[int] = None,
    properties: Optional[Dict] = None,
) -> None:
    """Create or update an Entity node and link it to its source Document."""
    props = properties or {}
    _run(
        """
        MERGE (e:Entity {id: $id})
        SET   e.name        = $name,
              e.type        = $type,
              e.source_doc  = $source_doc,
              e.source_row  = $source_row,
              e.updated_at  = timestamp()
        """,
        {"id": entity_id, "name": name, "type": entity_type,
         "source_doc": source_doc_id, "source_row": source_row},
    )
    # Link Document → Entity
    _run(
        """
        MATCH (d:Document {id: $doc_id})
        MATCH (e:Entity   {id: $ent_id})
        MERGE (d)-[:CONTAINS]->(e)
        """,
        {"doc_id": source_doc_id, "ent_id": entity_id},
    )


def upsert_relationship(
    from_entity_id: str,
    to_entity_id: str,
    rel_type: str = "RELATED_TO",
    evidence: str = "",
    confidence: float = 1.0,
) -> None:
    """
    Create/update a relationship between two Entity nodes.
    rel_type must be one of RELATED_TO, BELONGS_TO, REFERENCES, PART_OF.
    Only whitelisted types are allowed — no LLM-generated arbitrary Cypher.
    """
    _ALLOWED_REL_TYPES = {"RELATED_TO", "BELONGS_TO", "REFERENCES", "PART_OF"}
    if rel_type not in _ALLOWED_REL_TYPES:
        rel_type = "RELATED_TO"

    # We build the rel type into the query string safely (whitelist-validated above)
    cypher = f"""
        MATCH (a:Entity {{id: $from_id}})
        MATCH (b:Entity {{id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET   r.evidence   = $evidence,
              r.confidence = $confidence,
              r.updated_at = timestamp()
    """
    _run(cypher, {
        "from_id": from_entity_id, "to_id": to_entity_id,
        "evidence": evidence, "confidence": confidence,
    })


# ─── Schema graph nodes ───────────────────────────────────────────────────────

def sync_db_schema_to_graph(db_name: str, tables_info: List[Dict]) -> None:
    """
    Represent DB tables and columns as graph nodes.

    tables_info: list of {table_name, columns: [{name, type}], foreign_keys: [{referred_table}]}
    """
    for tbl in tables_info:
        table_name = tbl["table_name"]
        unique_key = f"{db_name}.{table_name}"

        # Upsert table node
        _run(
            """
            MERGE (t:DatabaseTable {unique_key: $key})
            SET   t.name       = $name,
                  t.db_name    = $db_name,
                  t.updated_at = timestamp()
            """,
            {"key": unique_key, "name": table_name, "db_name": db_name},
        )

        # Upsert column nodes
        for col in tbl.get("columns", []):
            col_key = f"{db_name}.{table_name}.{col['name']}"
            _run(
                """
                MERGE (c:DatabaseColumn {unique_key: $key})
                SET   c.name       = $name,
                      c.col_type   = $col_type,
                      c.table_name = $table_name,
                      c.db_name    = $db_name,
                      c.updated_at = timestamp()
                """,
                {"key": col_key, "name": col["name"],
                 "col_type": str(col.get("type", "")),
                 "table_name": table_name, "db_name": db_name},
            )
            # Table → Column
            _run(
                """
                MATCH (t:DatabaseTable  {unique_key: $tbl_key})
                MATCH (c:DatabaseColumn {unique_key: $col_key})
                MERGE (t)-[:CONTAINS_COLUMN]->(c)
                """,
                {"tbl_key": unique_key, "col_key": col_key},
            )

        # FK-verified table relationships
        for fk in tbl.get("foreign_keys", []):
            referred = fk.get("referred_table")
            if not referred:
                continue
            ref_key = f"{db_name}.{referred}"
            _run(
                """
                MATCH (a:DatabaseTable {unique_key: $from_key})
                MATCH (b:DatabaseTable {unique_key: $to_key})
                MERGE (a)-[r:RELATED_TO]->(b)
                SET   r.source     = 'foreign_key',
                      r.updated_at = timestamp()
                """,
                {"from_key": unique_key, "to_key": ref_key},
            )


# ─── Query helpers ────────────────────────────────────────────────────────────

def get_entity_by_id(entity_id: str) -> Optional[Dict]:
    rows = _run(
        "MATCH (e:Entity {id: $id}) RETURN e",
        {"id": entity_id},
    )
    if rows:
        return dict(rows[0]["e"])
    return None


def get_entity_neighbors(entity_id: str, depth: int = 1) -> Dict:
    """Return nodes and edges reachable within `depth` hops from entity_id."""
    depth = min(depth, 3)  # cap traversal depth
    rows = _run(
        f"""
        MATCH path = (e:Entity {{id: $id}})-[*1..{depth}]-(n)
        RETURN e, relationships(path) AS rels, nodes(path) AS nds
        LIMIT 100
        """,
        {"id": entity_id},
    )
    nodes, edges = {}, []
    for row in rows:
        for n in row.get("nds", []):
            nid = n.get("id") or n.get("unique_key") or n.get("name", "?")
            nodes[nid] = dict(n)
            nodes[nid]["labels"] = list(n.labels) if hasattr(n, "labels") else []
        for r in row.get("rels", []):
            edges.append({
                "from": r.start_node.get("id") or r.start_node.get("unique_key"),
                "to":   r.end_node.get("id")   or r.end_node.get("unique_key"),
                "type": r.type,
                "properties": dict(r),
            })
    return {"nodes": list(nodes.values()), "edges": edges}


def get_full_graph(db_name: Optional[str] = None, limit: int = 200) -> Dict:
    """Return a sample of the full graph for visualization."""
    if db_name:
        rows = _run(
            """
            MATCH (n)-[r]-(m)
            WHERE n.db_name = $db
            RETURN n, r, m
            LIMIT $limit
            """,
            {"db": db_name, "limit": limit},
        )
    else:
        rows = _run(
            "MATCH (n)-[r]-(m) RETURN n, r, m LIMIT $limit",
            {"limit": limit},
        )
    return _rows_to_graph(rows)


def search_entities(query: str, entity_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """Full-text / partial match search on entity names."""
    if entity_type:
        rows = _run(
            """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS toLower($q)
              AND e.type = $etype
            RETURN e
            LIMIT $limit
            """,
            {"q": query, "etype": entity_type, "limit": limit},
        )
    else:
        rows = _run(
            """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS toLower($q)
            RETURN e
            LIMIT $limit
            """,
            {"q": query, "limit": limit},
        )
    return [dict(r["e"]) for r in rows]


def semantic_search_entities(entity_names: List[str], db_name: Optional[str] = None) -> Dict:
    """
    Given a list of entity names (extracted from user question),
    find matching Entity and DatabaseTable nodes plus their 1-hop neighbours.
    Returns {nodes, edges} for injection into prompts.
    """
    if not entity_names:
        return {"nodes": [], "edges": []}

    conditions = " OR ".join(
        [f"toLower(e.name) CONTAINS toLower($n{i})" for i in range(len(entity_names))]
    )
    params = {f"n{i}": name for i, name in enumerate(entity_names)}
    if db_name:
        params["db"] = db_name
        db_filter = "AND (e.source_db = $db OR e.source_db IS NULL)"
    else:
        db_filter = ""

    rows = _run(
        f"""
        MATCH (e:Entity)
        WHERE ({conditions}) {db_filter}
        WITH e
        OPTIONAL MATCH (e)-[r]-(n)
        RETURN e, r, n
        LIMIT 100
        """,
        params,
    )
    return _rows_to_graph(rows)


def get_table_relationships(db_name: str) -> List[Dict]:
    """Return all table-to-table relationships for a given DB."""
    rows = _run(
        """
        MATCH (a:DatabaseTable {db_name: $db})-[r:RELATED_TO]->(b:DatabaseTable {db_name: $db})
        RETURN a.name AS from_table, b.name AS to_table,
               r.source AS source, r.confidence AS confidence
        """,
        {"db": db_name},
    )
    return rows


def delete_document_graph(doc_id: str) -> None:
    """Remove a document and all its owned entities from the graph."""
    _run(
        """
        MATCH (d:Document {id: $id})
        OPTIONAL MATCH (d)-[:CONTAINS]->(e:Entity)
        DETACH DELETE d, e
        """,
        {"id": doc_id},
    )


# ─── Internal helpers ─────────────────────────────────────────────────────────

# ─── Internal helpers ─────────────────────────────────────────────────────────

def _stable_node_id(node) -> str:
    """
    Return a consistent ID string for any Neo4j node object.
    Priority: id -> unique_key -> name -> fallback '?'
    Must match the _node_id() function in the frontend knowledge_graph.py.
    """
    for key in ("id", "unique_key", "name"):
        val = node.get(key)
        if val is not None and str(val) not in ("None", ""):
            return str(val)
    return "?"


def _rows_to_graph(rows: List[Dict]) -> Dict:
    """
    Convert raw Neo4j query rows into {nodes, edges} for the frontend visualiser.

    Key fix: use _stable_node_id() for BOTH node dict keys AND edge from/to values
    so that DatabaseTable / DatabaseColumn nodes (which use 'unique_key' not 'id')
    are correctly keyed and wired to their edges.
    Previously these all resolved to None and appeared as a single collapsed point.
    """
    nodes: Dict[str, Dict] = {}
    edges: List[Dict] = []

    for row in rows:
        for key in ("n", "e", "m"):
            node = row.get(key)
            if node is None:
                continue
            nid = _stable_node_id(node)
            if nid not in nodes:
                n_dict = dict(node)
                n_dict["labels"] = list(node.labels) if hasattr(node, "labels") else []
                nodes[nid] = n_dict

        rel = row.get("r")
        if rel is not None:
            edges.append({
                "from":       _stable_node_id(rel.start_node),
                "to":         _stable_node_id(rel.end_node),
                "type":       rel.type,
                "properties": dict(rel),
            })

    return {"nodes": list(nodes.values()), "edges": edges}

