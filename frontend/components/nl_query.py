import streamlit as st
from utils.api import nl_to_sql

_NL_CSS = """
<style>
.nl-question-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
    display: block;
}
.nl-subheader {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.nl-subheader-text {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
}
.nl-badge {
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(99,102,241,0.15);
    color: #818cf8;
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 2px 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
</style>
"""

def nl_query_ui(db_selected):
    """
    UI component for Natural Language to SQL conversion.
    Expects db_selected = {"db_name": "...", "table_name": "..."}
    """
    st.markdown(_NL_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="nl-subheader">
        <span style="font-size:1.3rem;">💬</span>
        <span class="nl-subheader-text">Ask a Question</span>
        <span class="nl-badge">Gemini AI</span>
    </div>
    """, unsafe_allow_html=True)

    question = st.text_input(
        "Your question",
        placeholder="e.g. Show total sales by region for Q3 2024",
        label_visibility="collapsed",
        key="nl_question_input"
    )

    btn_col, hint_col = st.columns([1, 2])
    with btn_col:
        clicked = st.button("⚡ Generate SQL", type="primary", use_container_width=True)

    if clicked and question:
        with st.spinner("Querying ChromaDB schema → Gemini 2.5 Flash…"):
            sql_result = nl_to_sql(
                question,
                db_selected["db_name"],
                db_selected["table_name"]
            )

        if sql_result.get("status") == "success":
            sql_query = sql_result.get("sql_query")
            st.session_state["last_sql"] = sql_query

            # Show schema & graph context hints if available
            tables_used = sql_result.get("tables_used", [])
            graph_ctx = sql_result.get("graph_context", "")

            if tables_used:
                st.markdown(
                    "<div style='font-size:0.75rem; color:#4b5563; margin-bottom:0.4rem;'>"
                    "📊 Tables used: " + " · ".join(f"<code style='background:rgba(99,102,241,0.1);color:#818cf8;border-radius:4px;padding:1px 6px'>{t}</code>" for t in tables_used)
                    + "</div>",
                    unsafe_allow_html=True
                )

            st.code(sql_query, language="sql")

            if graph_ctx:
                with st.expander("🕸️ Knowledge Graph context injected into prompt", expanded=False):
                    st.code(graph_ctx, language="yaml")
        else:
            error_msg = sql_result.get("error", "Failed to generate SQL query.")
            st.error(f"⚠️ {error_msg}")
    elif clicked and not question:
        st.warning("Please enter a question first.")
