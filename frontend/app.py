import streamlit as st
from components.sidebar import sidebar_ui
from components.nl_query import nl_query_ui
from components.sql_editor import sql_editor_ui
from components.followup import followup_ui
from components.result_viewer import show_result_summary


st.set_page_config(
    page_title="NL2SQL Intelligence · Samsung",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global premium CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Sidebar overhaul */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1629 60%, #0f172a 100%) !important;
    border-right: 1px solid rgba(99, 102, 241, 0.2) !important;
}
section[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #e2e8f0 !important;
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #060b18 0%, #0b1220 50%, #080e1c 100%) !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Premium page header */
.nlq-header {
    background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.08) 50%, rgba(6,182,212,0.06) 100%);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.nlq-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #6366f1, #8b5cf6, #06b6d4, transparent);
}
.nlq-header h1 {
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 50%, #67e8f9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 !important;
    padding: 0 !important;
    letter-spacing: -0.03em;
}
.nlq-header p {
    color: #64748b !important;
    font-size: 0.88rem !important;
    margin: 0.4rem 0 0 0 !important;
}

/* Section cards */
.section-card {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(51, 65, 85, 0.6);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(10px);
    transition: border-color 0.2s ease;
}
.section-card:hover {
    border-color: rgba(99, 102, 241, 0.35);
}

/* Metric tweaks */
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #a5b4fc !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.01em;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4) !important;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%) !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
}

/* Code blocks */
.stCodeBlock {
    border-radius: 10px !important;
    border: 1px solid rgba(51, 65, 85, 0.5) !important;
}

/* Dataframe */
.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden;
}

/* Text input */
.stTextInput input, .stTextArea textarea {
    background: rgba(15, 23, 42, 0.9) !important;
    border: 1px solid rgba(51, 65, 85, 0.7) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(99, 102, 241, 0.6) !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15) !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background: rgba(15, 23, 42, 0.9) !important;
    border: 1px solid rgba(51, 65, 85, 0.7) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

/* Spinner */
.stSpinner > div > div {
    border-top-color: #6366f1 !important;
}

/* Info / Success / Warning / Error boxes */
.stSuccess {
    background: rgba(16, 185, 129, 0.1) !important;
    border: 1px solid rgba(16, 185, 129, 0.3) !important;
    border-radius: 10px !important;
    color: #6ee7b7 !important;
}
.stError {
    background: rgba(239, 68, 68, 0.1) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    border-radius: 10px !important;
}
.stInfo {
    background: rgba(59, 130, 246, 0.1) !important;
    border: 1px solid rgba(59, 130, 246, 0.3) !important;
    border-radius: 10px !important;
    color: #93c5fd !important;
}
.stWarning {
    background: rgba(245, 158, 11, 0.1) !important;
    border: 1px solid rgba(245, 158, 11, 0.3) !important;
    border-radius: 10px !important;
    color: #fcd34d !important;
}

/* Subheader styling */
h2 {
    color: #e2e8f0 !important;
    font-weight: 700 !important;
    font-size: 1.15rem !important;
    letter-spacing: -0.01em;
}
h3 {
    color: #cbd5e1 !important;
    font-weight: 600 !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(51, 65, 85, 0.5) !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
}
.streamlit-expanderContent {
    background: rgba(8, 14, 28, 0.8) !important;
    border: 1px solid rgba(51, 65, 85, 0.3) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* Nav radio buttons in sidebar */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 4px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 8px !important;
    padding: 8px 14px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    color: #94a3b8 !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    margin: 2px 0 !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(99,102,241,0.15) !important;
    border-color: rgba(99,102,241,0.4) !important;
    color: #e2e8f0 !important;
}

/* Divider */
hr {
    border-color: rgba(51, 65, 85, 0.4) !important;
    margin: 1.2rem 0 !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(8, 14, 28, 0.6) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid rgba(51, 65, 85, 0.4) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #64748b !important;
    font-weight: 500 !important;
    font-size: 0.86rem !important;
    padding: 0.4rem 1rem !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(99, 102, 241, 0.2) !important;
    color: #a5b4fc !important;
    border-bottom: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Initialize session state ──────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "main"

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 1.5rem 0;'>
        <div style='font-size:2.2rem; margin-bottom:0.3rem;'>🧠</div>
        <div style='font-size:1.05rem; font-weight:800; color:#e2e8f0; letter-spacing:-0.02em;'>NL2SQL Intelligence</div>
        <div style='font-size:0.73rem; color:#4b5563; margin-top:0.2rem; font-weight:500; text-transform:uppercase; letter-spacing:0.1em;'>Powered by Gemini · Samsung</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.72rem; color:#4b5563; font-weight:600; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.5rem;'>Navigation</div>", unsafe_allow_html=True)

    PAGE_OPTIONS = ["🏠 Main Dashboard", "📥 Ingest Data", "🕸️ Knowledge Graph"]
    current_idx = 0
    if st.session_state.current_page == "ingest":
        current_idx = 1
    elif st.session_state.current_page == "graph":
        current_idx = 2

    page = st.radio("Navigate", PAGE_OPTIONS, index=current_idx, label_visibility="collapsed")

    st.markdown("<hr style='margin: 1.2rem 0; border-color: rgba(51,65,85,0.4)'>", unsafe_allow_html=True)

# ── Route pages ───────────────────────────────────────────────────────────────
if page == "📥 Ingest Data":
    st.session_state.current_page = "ingest"
    from components.data_ingestion import data_ingestion_page
    data_ingestion_page()

elif page == "🕸️ Knowledge Graph":
    st.session_state.current_page = "graph"
    from components.knowledge_graph import knowledge_graph_page
    knowledge_graph_page()

else:
    st.session_state.current_page = "main"

    # ── Premium header ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="nlq-header">
        <h1>🧠 NL2SQL Intelligence Dashboard</h1>
        <p>Ask questions in plain English · Gemini AI generates MySQL · ChromaDB + Neo4j Knowledge Graph enrichment</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar DB selector ─────────────────────────────────────────────────
    db_selected = sidebar_ui()

    if db_selected:
        # ── Two column layout ─────────────────────────────────────────────
        col1, col2 = st.columns([1, 1], gap="medium")

        with col1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            nl_query_ui(db_selected)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            followup_ui(db_selected)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            sql_editor_ui(db_selected)
            st.markdown('</div>', unsafe_allow_html=True)

            if "last_sql" in st.session_state and st.session_state["last_sql"]:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                show_result_summary(st.session_state["last_sql"], db_selected)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center; padding: 4rem 2rem;'>
            <div style='font-size:3rem; margin-bottom:1rem;'>🗄️</div>
            <div style='font-size:1.1rem; color:#64748b; font-weight:500;'>Select a database from the sidebar to begin</div>
            <div style='font-size:0.85rem; color:#374151; margin-top:0.5rem;'>Upload files first via the <strong style="color:#6366f1">Ingest Data</strong> page to create your first database</div>
        </div>
        """, unsafe_allow_html=True)
