import streamlit as st
import requests
import json
import plotly.graph_objects as go

BASE_URL = "http://localhost:8000/api"

_RV_CSS = """
<style>
.rv-subheader {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.rv-subheader-text {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
}
.rv-badge {
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(139,92,246,0.15);
    color: #c4b5fd;
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 20px;
    padding: 2px 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.summary-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.05) 100%);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin: 0.8rem 0;
    color: #cbd5e1;
    font-size: 0.92rem;
    line-height: 1.7;
}
</style>
"""

def show_result_summary(sql_query, db_selected):
    st.markdown(_RV_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="rv-subheader">
        <span style="font-size:1.3rem;">🧠</span>
        <span class="rv-subheader-text">AI Summary</span>
        <span class="rv-badge">Gemini Insight</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("✨ Generate Natural Language Summary", use_container_width=True):
        with st.spinner("Gemini is analyzing your query results…"):
            try:
                payload = {"sql_query": sql_query, "db_name": db_selected["db_name"]}
                res = requests.post(f"{BASE_URL}/summarize/", json=payload)

                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        st.session_state.last_summary = data.get("summary")
                        st.session_state.last_chart = data.get("chart_json")
                    else:
                        st.error(f"Error: {data.get('detail', 'Unknown error')}")
                elif res.status_code == 429:
                    try:
                        error_data = res.json()
                        detail = error_data.get("detail", {})
                        error_msg = detail.get("error", "API quota exceeded") if isinstance(detail, dict) else str(detail)
                        st.warning(f"⚠️ {error_msg}")
                    except Exception:
                        st.warning("⚠️ API quota exceeded. Please try again later.")
                else:
                    try:
                        error_msg = res.json().get("detail", f"API request failed with status {res.status_code}")
                    except Exception:
                        error_msg = f"API request failed with status {res.status_code}"
                    st.error(f"Error: {error_msg}")
            except Exception as e:
                st.error(f"Error generating summary: {str(e)}")

    # Display summary
    if st.session_state.get("last_summary"):
        st.markdown(
            f'<div class="summary-card">{st.session_state.last_summary}</div>',
            unsafe_allow_html=True
        )

    # Display chart
    if st.session_state.get("last_chart"):
        try:
            chart_data = st.session_state.last_chart
            if chart_data:
                fig = go.Figure(json.loads(chart_data))

                # Style the chart to match the dark theme
                fig.update_layout(
                    paper_bgcolor="rgba(8,14,28,0.0)",
                    plot_bgcolor="rgba(15,23,42,0.5)",
                    font=dict(color="#94a3b8", family="Inter"),
                    title_font=dict(color="#e2e8f0", size=14),
                    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8")),
                    margin=dict(t=40, l=10, r=10, b=10),
                )
                fig.update_xaxes(gridcolor="rgba(51,65,85,0.4)", tickfont=dict(color="#64748b"))
                fig.update_yaxes(gridcolor="rgba(51,65,85,0.4)", tickfont=dict(color="#64748b"))

                st.markdown("**📊 Visualization**")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not display chart: {str(e)}")