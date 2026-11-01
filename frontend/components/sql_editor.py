import streamlit as st
from utils.api import execute_sql
import pandas as pd

_SQL_CSS = """
<style>
.sql-subheader {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.sql-subheader-text {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
}
.sql-badge {
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(6,182,212,0.12);
    color: #22d3ee;
    border: 1px solid rgba(6,182,212,0.3);
    border-radius: 20px;
    padding: 2px 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.row-count-chip {
    display: inline-block;
    background: rgba(16,185,129,0.12);
    color: #34d399;
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
}
</style>
"""

def sql_editor_ui(db_selected):
    st.markdown(_SQL_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="sql-subheader">
        <span style="font-size:1.3rem;">🛠️</span>
        <span class="sql-subheader-text">SQL Editor</span>
        <span class="sql-badge">Live Execute</span>
    </div>
    """, unsafe_allow_html=True)

    if "last_sql" in st.session_state and st.session_state["last_sql"]:
        edited_sql = st.text_area(
            "Edit SQL",
            value=st.session_state["last_sql"],
            height=160,
            label_visibility="collapsed",
            key="sql_editor_textarea"
        )

        run_col, clear_col = st.columns([2, 1])
        with run_col:
            run_clicked = st.button("▶  Run Query", use_container_width=True)
        with clear_col:
            if st.button("✕ Clear", use_container_width=True):
                st.session_state["last_sql"] = ""
                st.rerun()

        if run_clicked:
            with st.spinner("Executing against MySQL…"):
                result = execute_sql(edited_sql, db_selected["db_name"])

            if result.get("status") != "success":
                st.error(result.get("detail", result.get("error", "Query failed.")))
                return

            rows = result.get("rows") or []
            if not rows:
                st.warning("Query returned no results.")
                return

            df = pd.DataFrame(rows)
            st.session_state.last_result_df = df
            st.session_state.last_sql = edited_sql

            st.markdown(
                f"<div class='row-count-chip'>✅ {len(df):,} rows returned</div>",
                unsafe_allow_html=True
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Auto-visualize numeric columns
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if len(numeric_cols) >= 1:
                with st.expander("📊 Auto-visualization", expanded=True):
                    chart_col = st.selectbox(
                        "Select metric to chart",
                        numeric_cols,
                        key="sql_chart_col_select"
                    )
                    st.bar_chart(df[chart_col], color="#6366f1")
    else:
        st.markdown("""
        <div style='text-align:center; padding:2rem 1rem; color:#374151;'>
            <div style='font-size:1.8rem; margin-bottom:0.5rem;'>📝</div>
            <div style='font-size:0.88rem; font-weight:500;'>Generate SQL above and it will appear here for editing</div>
        </div>
        """, unsafe_allow_html=True)
