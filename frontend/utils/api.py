import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000/api"

def list_databases():
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        try:
            return r.json()
        except Exception:
            print("Response text:", r.text)
            return {"databases": [], "error": "Invalid response"}
    except requests.exceptions.ConnectionError:
        return {"databases": [], "error": "Cannot connect to backend. Please ensure the backend server is running."}
    except Exception as e:
        return {"databases": [], "error": str(e)}


def list_tables(db_name):
    r = requests.get(f"{BASE_URL}/{db_name}")
    return r.json()

def upload_file(file_path, table_name=None, db_name=None, if_exists="replace"):
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f)}
        data = {"table_name": table_name, "if_exists": if_exists, "db_name": db_name}
        r = requests.post(f"{BASE_URL}/upload/", files=files, data=data)
    return r.json()

# def nl_to_sql(question, db_name):
#     r = requests.post(f"{BASE_URL}/nl2sql/", json={"question": question, "db_name": db_name})
#     return r.json()

def nl_to_sql(question,db_name, table_name):
    """
    Calls /nl2sql endpoint with the selected table.
    """
    payload = {
        "question": question,
        "db_name": db_name,
        "table_name": table_name
    }
    r = requests.post(f"{BASE_URL}/nl2sql/", json=payload)
    try:
        return r.json()
    except Exception:
        st.error(f"Failed to parse response from backend: {r.text}")
        return {"status": "error", "error": "Invalid response"}


def execute_sql(sql_query, db_name):
    r = requests.post(f"{BASE_URL}/execute/", json={"sql_query": sql_query, "db_name": db_name})
    return r.json()

def ingest_data_file(file_path, filename, db_name):
    """
    Calls the intelligent ingestion endpoint with file upload.
    """
    with open(file_path, "rb") as f:
        files = {"file": (filename, f)}
        data = {"db_name": db_name}
        r = requests.post(f"{BASE_URL}/ingest/", files=files, data=data)
    return r.json()


# ─── Knowledge Graph API Helpers ─────────────────────────────────────────────

def get_graph_status():
    """Check if the Neo4j graph layer is available."""
    try:
        r = requests.get(f"{BASE_URL}/graph/status", timeout=5)
        return r.json()
    except Exception as e:
        return {"graph_available": False, "message": str(e)}


def get_graph_data(db_name=None, limit=200):
    """Fetch nodes and edges for graph visualization."""
    try:
        params = {"limit": limit}
        if db_name:
            params["db_name"] = db_name
        r = requests.get(f"{BASE_URL}/graph/", params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"nodes": [], "edges": [], "graph_available": False, "error": str(e)}


def search_graph_entities(query, entity_type=None, limit=50):
    """Search for entities matching query string."""
    try:
        params = {"q": query, "limit": limit}
        if entity_type:
            params["entity_type"] = entity_type
        r = requests.get(f"{BASE_URL}/graph/search", params=params, timeout=5)
        return r.json()
    except Exception as e:
        return {"results": [], "graph_available": False, "error": str(e)}


def semantic_search_graph(question, db_name=None):
    """Extract entities from natural language and return matching graph subgraph."""
    try:
        payload = {"question": question}
        if db_name:
            payload["db_name"] = db_name
        r = requests.post(f"{BASE_URL}/graph/semantic-search", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"nodes": [], "edges": [], "graph_available": False, "entities_found": [], "error": str(e)}


def get_entity_neighbors(entity_id, depth=1):
    """Fetch neighborhood around a specific entity."""
    try:
        r = requests.get(f"{BASE_URL}/graph/entities/{entity_id}/neighbors", params={"depth": depth}, timeout=5)
        return r.json()
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}


def get_table_relationships(db_name):
    """Fetch verified relationships between tables for a database."""
    try:
        r = requests.get(f"{BASE_URL}/graph/tables/{db_name}/relationships", timeout=5)
        return r.json()
    except Exception as e:
        return {"relationships": [], "graph_available": False, "error": str(e)}


def sync_schema_to_graph(db_name):
    """Trigger manual sync of database schema to knowledge graph."""
    try:
        r = requests.post(f"{BASE_URL}/graph/sync-schema/{db_name}", timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}

