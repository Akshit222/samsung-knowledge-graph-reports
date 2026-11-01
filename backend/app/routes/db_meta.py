from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from utils.db import root_engine, get_engine_for_db
import traceback

router = APIRouter()

@router.get("/")
def list_databases():
    try:
        print("[DB Meta] Using root_engine for SHOW DATABASES")
        with root_engine.connect() as conn:
            print("[DB Meta] Connected successfully")
            result = conn.execute(text("SHOW DATABASES;"))
            # Filter out system databases
            dbs = [row[0] for row in result.fetchall() if row[0] not in ('information_schema', 'mysql', 'performance_schema', 'sys')]
            print("[DB Meta] Databases found:", dbs)
        return {"databases": dbs}
    except Exception as e:
        print("[DB Meta] Error in /databases:", str(e).encode('ascii', 'ignore').decode())
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{db_name}")
def list_tables(db_name: str):
    try:
        print(f"[DB Meta] Connecting to DB: {db_name}")
        engine_db = get_engine_for_db(db_name)
        with engine_db.connect() as conn:
            print("[DB Meta] Connected to", db_name)
            result = conn.execute(text("SHOW TABLES;"))
            tables = [row[0] for row in result.fetchall()]
            print(f"[DB Meta] Tables in {db_name}:", tables)
        return {"tables": tables}
    except Exception as e:
        print(f"[DB Meta] Error listing tables in {db_name}:", str(e).encode('ascii', 'ignore').decode())
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

