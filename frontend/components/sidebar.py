import streamlit as st
from utils.api import list_databases, list_tables, execute_sql
from utils.api import BASE_URL
import requests

_SB_CSS = """
<style>
.sb-section-title {
    font-size: 0.7rem;
    font-weight: 600;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
    margin-top: 1rem;
    display: block;
}
.sb-stat-row {
    display: flex;
    gap: 8px;
    margin: 0.6rem 0;
}
.sb-stat {
    flex: 1;
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 8px;
    padding: 0.5rem 0.6rem;
    text-align: center;
}
.sb-stat-val {
    font-size: 1.1rem;
    font-weight: 700;
    color: #818cf8;
    line-height: 1.2;
}
.sb-stat-lbl {
    font-size: 0.65rem;
    color: #4b5563;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
</style>
"""

def sidebar_ui():
    st.sidebar.markdown(_SB_CSS, unsafe_allow_html=True)

    # ── Database Settings ─────────────────────────────────────────────────────
    st.sidebar.markdown('<span class="sb-section-title">📦 Database</span>', unsafe_allow_html=True)

    db_response = list_databases()

    if "error" in db_response:
        st.sidebar.error(db_response["error"])
        st.sidebar.info("💡 Start the backend: `uvicorn main:app --reload`")
        return None

    databases = db_response.get("databases", [])
    if not databases:
        st.sidebar.markdown("""
        <div style='background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:0.8rem;font-size:0.82rem;color:#fbbf24;'>
            No databases found.<br>
            <strong>→ Upload a file on the Ingest page first</strong>
        </div>
        """, unsafe_allow_html=True)
        return None

    db_selected = st.sidebar.selectbox(
        "Database",
        databases,
        label_visibility="collapsed",
        key="sidebar_db_select"
    )

    # Schema refresh
    if st.sidebar.button("🔄 Refresh Schema & Embeddings", use_container_width=True, key="sidebar_refresh_btn"):
        try:
            r = requests.post(f"{BASE_URL}/refresh/", json={"db_name": db_selected})
            if r.status_code == 200:
                st.sidebar.success(r.json().get("message", "Schema refreshed ✅"))
            else:
                st.sidebar.error(r.text)
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

    # ── Table selection ───────────────────────────────────────────────────────
    st.sidebar.markdown('<span class="sb-section-title">🗂️ Table</span>', unsafe_allow_html=True)

    table_response = list_tables(db_selected)
    tables = table_response.get("tables", [])

    if not tables:
        st.sidebar.markdown("""
        <div style='font-size:0.8rem; color:#4b5563; padding:0.4rem 0;'>
            No tables in this database yet.
        </div>
        """, unsafe_allow_html=True)
        return {"db_name": db_selected, "table_name": None}

    # Stats row
    st.sidebar.markdown(
        f"""<div class="sb-stat-row">
            <div class="sb-stat">
                <div class="sb-stat-val">{len(databases)}</div>
                <div class="sb-stat-lbl">DBs</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-val">{len(tables)}</div>
                <div class="sb-stat-lbl">Tables</div>
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    table_selected = st.sidebar.selectbox(
        "Table",
        tables,
        label_visibility="collapsed",
        key="sidebar_table_select"
    )

    # ── Table preview ─────────────────────────────────────────────────────────
    st.sidebar.markdown('<span class="sb-section-title">🔍 Preview</span>', unsafe_allow_html=True)

    if table_selected:
        try:
            preview_sql = f"SELECT * FROM `{table_selected}` LIMIT 5;"
            result = execute_sql(preview_sql, db_selected)

            if result.get("status") == "success":
                rows = result.get("rows", [])
                if rows:
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    st.sidebar.dataframe(df, use_container_width=True, hide_index=True, height=180)
                    st.sidebar.markdown(
                        f"<div style='font-size:0.72rem;color:#4b5563;text-align:right;'>showing 5 of {len(rows)} rows</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.sidebar.markdown("<div style='font-size:0.8rem;color:#4b5563;'>Table is empty.</div>", unsafe_allow_html=True)
            else:
                st.sidebar.error(result.get("detail", "Failed to load preview."))
        except Exception as e:
            st.sidebar.error(f"Preview error: {e}")

    st.sidebar.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    return {"db_name": db_selected, "table_name": table_selected}
