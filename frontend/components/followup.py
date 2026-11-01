import streamlit as st
import pandas as pd
from utils.api import nl_to_sql, execute_sql

_FU_CSS = """
<style>
.fu-subheader {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.fu-subheader-text {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
}
.fu-badge {
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(245,158,11,0.12);
    color: #fbbf24;
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 20px;
    padding: 2px 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.prev-result-header {
    font-size: 0.78rem;
    font-weight: 600;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
}
</style>
"""

def followup_ui(db_selected):
    """
    Handle follow-up questions for contextual query generation.
    db_selected: dict -> {"db_name": "unox", "table_name": "movies"}
    """
    st.markdown(_FU_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="fu-subheader">
        <span style="font-size:1.3rem;">🔁</span>
        <span class="fu-subheader-text">Follow-up Question</span>
        <span class="fu-badge">Contextual</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Initialize session state ---
    if "last_result_df" not in st.session_state:
        st.session_state.last_result_df = pd.DataFrame()
    if "last_sql" not in st.session_state:
        st.session_state.last_sql = ""
    if "last_followup_sql" not in st.session_state:
        st.session_state.last_followup_sql = ""

    # --- Previous result preview ---
    if not st.session_state.last_result_df.empty:
        with st.expander("📋 Previous query result", expanded=False):
            st.markdown('<div class="prev-result-header">Last result</div>', unsafe_allow_html=True)
            st.dataframe(st.session_state.last_result_df.head(5), use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div style='font-size:0.82rem; color:#374151; padding:0.6rem 0 0.8rem 0;'>
            💡 Run a main query first, then ask follow-up questions here
        </div>
        """, unsafe_allow_html=True)

    # --- Follow-up input ---
    followup = st.text_input(
        "Follow-up",
        placeholder="e.g. Now filter only North region, or show top 5…",
        label_visibility="collapsed",
        key="followup_input"
    )

    if st.button("🔁 Generate Follow-up SQL", use_container_width=True) and followup:
        if not st.session_state.last_sql:
            st.warning("Please run a main query first before asking a follow-up.")
            return

        with st.spinner("Building context-aware SQL with Gemini…"):
            try:
                context_question = f"""
Previous SQL Query: {st.session_state.last_sql}
Follow-up Question: {followup}
"""
                sql_result = nl_to_sql(
                    context_question,
                    db_selected["db_name"],
                    db_selected["table_name"]
                )

                followup_sql = sql_result.get("sql_query")
                st.session_state.last_followup_sql = followup_sql

                if not followup_sql:
                    st.error("No SQL query generated for follow-up.")
                    return

                st.success("✅ Follow-up SQL generated")
                st.code(followup_sql, language="sql")

                with st.spinner("Running follow-up query…"):
                    result = execute_sql(followup_sql, db_selected["db_name"])

                if result.get("status") == "success":
                    df = pd.DataFrame(result["rows"])
                    st.session_state.last_result_df = df
                    st.markdown(
                        f"<div style='font-size:0.78rem; color:#34d399; margin-bottom:0.4rem;'>✅ {len(df):,} rows</div>",
                        unsafe_allow_html=True
                    )
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.error(result.get("detail", result.get("error", "Query failed.")))

            except Exception as e:
                st.error(f"Error while generating follow-up: {e}")
