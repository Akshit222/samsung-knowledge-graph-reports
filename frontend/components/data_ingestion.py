import streamlit as st
import pandas as pd
import requests
from utils.api import list_databases, list_tables, ingest_data_file, execute_sql
from utils.semantic_engine import (
    annotate_columns,
    generate_r2rml,
    generate_rdf_triples,
    generate_knowledge_graph_figure,
    to_pascal_case,
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS injected once per page load
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
/* ── Section headers ── */
.sw-section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: 0.03em;
    margin: 1.4rem 0 0.3rem 0;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid #334155;
}

/* ── Callout cards ── */
.sw-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    font-size: 0.9rem;
    color: #cbd5e1;
    line-height: 1.7;
}
.sw-card strong { color: #f8fafc; }
.sw-card code {
    background: #0f172a;
    color: #7dd3fc;
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 0.82rem;
}

/* ── Concept badge row ── */
.sw-badge-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 0.5rem 0 1rem 0; }
.sw-badge {
    background: #1e3a5f;
    color: #93c5fd;
    border: 1px solid #2563eb44;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.77rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* ── Thin rule ── */
.sw-rule { border: none; border-top: 1px solid #334155; margin: 1.2rem 0; }

/* ── Quote block ── */
.sw-quote {
    border-left: 3px solid #6366f1;
    background: #1e1b4b22;
    padding: 0.7rem 1rem;
    border-radius: 0 8px 8px 0;
    color: #a5b4fc;
    font-style: italic;
    font-size: 0.9rem;
    margin: 0.6rem 0 1rem 0;
}

/* ── Step list ── */
.sw-step { display: flex; gap: 10px; margin-bottom: 0.7rem; align-items: flex-start; }
.sw-step-num {
    background: #6366f1;
    color: white;
    border-radius: 50%;
    min-width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 2px;
}
.sw-step-body { font-size: 0.9rem; color: #cbd5e1; line-height: 1.6; }
.sw-step-body strong { color: #f1f5f9; }
</style>
"""


def _inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def _section_header(title: str):
    st.markdown(f'<p class="sw-section-header">{title}</p>', unsafe_allow_html=True)


def _card(content: str):
    st.markdown(f'<div class="sw-card">{content}</div>', unsafe_allow_html=True)


def _rule():
    st.markdown('<hr class="sw-rule">', unsafe_allow_html=True)


def _badges(*labels):
    badges = "".join(f'<span class="sw-badge">{l}</span>' for l in labels)
    st.markdown(f'<div class="sw-badge-row">{badges}</div>', unsafe_allow_html=True)


def _quote(text: str):
    st.markdown(f'<div class="sw-quote">{text}</div>', unsafe_allow_html=True)


def _step(num: int, title: str, body: str):
    st.markdown(
        f'<div class="sw-step">'
        f'<div class="sw-step-num">{num}</div>'
        f'<div class="sw-step-body"><strong>{title}</strong><br>{body}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Artifacts Renderer
# ─────────────────────────────────────────────────────────────────────────────
def render_semantic_artifacts(
    table_name: str,
    columns: list,
    rows_added: int,
    selected_db: str,
    matches: dict = None,
):
    """Renders the full Semantic Web layer below an ingestion or inspect result."""

    # ── Fetch live data ──────────────────────────────────────────────────────
    sample_rows = []
    try:
        q = execute_sql(f"SELECT * FROM `{table_name}` LIMIT 5;", selected_db)
        if q.get("status") == "success":
            sample_rows = q.get("rows", [])
            if not columns:
                columns = q.get("columns", [])
    except Exception:
        pass

    other_tables = []
    try:
        other_tables = [
            t for t in list_tables(selected_db).get("tables", []) if t != table_name
        ]
    except Exception:
        pass

    # ── Compute artifacts ────────────────────────────────────────────────────
    annotations  = annotate_columns(columns, sample_rows)
    r2rml_turtle = generate_r2rml(table_name, annotations)
    rdf_data     = generate_rdf_triples(table_name, annotations, sample_rows, limit=5)
    kg_fig       = generate_knowledge_graph_figure(table_name, annotations, other_tables)

    owl_class   = f":{to_pascal_case(table_name)}"
    n_props     = len(annotations)
    n_triples   = rows_added * (n_props + 1) if rows_added > 0 else n_props * 5

    # ── Divider & title ──────────────────────────────────────────────────────
    _rule()
    st.markdown("### 🌐 Semantic Web & Knowledge Graph Layer")
    st.caption(
        f"Auto-generated for **{owl_class}** using W3C Direct Mapping, OWL Induction, "
        "and RDF Triplification — no manual configuration required."
    )

    # ── 4 key metric chips ───────────────────────────────────────────────────
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("OWL Class (TBox)", owl_class)
    with col_b:
        st.metric("RDF Properties", n_props, help="CTA + CPA mapped attributes")
    with col_c:
        st.metric("ABox Triples (est.)", f"~{n_triples:,}")
    with col_d:
        st.metric("Standard", "W3C R2RML")

    st.write("")  # breathing room

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_kg, tab_r2rml, tab_rdf, tab_explain = st.tabs([
        "🕸️  Knowledge Graph",
        "📜  R2RML Mapping",
        "💎  RDF Triples",
        "🎓  How to Explain",
    ])

    # ╔═══════════════════════╗
    # ║  TAB 1 — GRAPH / CTA ║
    # ╚═══════════════════════╝
    with tab_kg:
        _section_header("Interactive OWL Ontology Visualizer")
        st.caption(
            "Violet = OWL Class (TBox entity) · Cyan = Datatype Property · "
            "Pink = Linked Class (Object Property / foreign relation)"
        )
        st.plotly_chart(kg_fig, use_container_width=True)

        _rule()
        _section_header("Semantic Labeling Report — CTA & CPA")
        st.caption(
            "Each source column is annotated with its OWL property type, "
            "W3C datatype, and aligned Schema.org concept."
        )
        df_ann = pd.DataFrame(
            [
                {
                    "Source Column":    a["column"],
                    "RDF Predicate":    a["sanitized_predicate"],
                    "OWL Type":         a["owl_type"].replace("owl:", ""),
                    "XSD Datatype":     a["xsd_type"],
                    "Schema.org":       a["schema_concept"],
                    "Semantic Role":    a["cpa_role"],
                }
                for a in annotations
            ]
        )
        st.dataframe(df_ann, use_container_width=True, hide_index=True, height=min(260, 44 + 36 * len(df_ann)))

    # ╔════════════════════╗
    # ║  TAB 2 — R2RML    ║
    # ╚════════════════════╝
    with tab_r2rml:
        _section_header("W3C R2RML Mapping Document")
        _card(
            "<strong>R2RML</strong> (Relational to RDF Mapping Language) is the official "
            "<strong>W3C Recommendation</strong> (2012) for defining how relational database "
            "tables map to RDF Knowledge Graphs. The document below was auto-generated from "
            f"the schema of <code>{table_name}</code> and is fully importable into tools like "
            "<strong>Ontop</strong>, <strong>D2RQ</strong>, or <strong>Apache Jena</strong>."
        )
        st.code(r2rml_turtle, language="turtle")
        st.download_button(
            label="📥  Download R2RML (.ttl)",
            data=r2rml_turtle,
            file_name=f"{table_name}.r2rml.ttl",
            mime="text/turtle",
            use_container_width=True,
        )

    # ╔══════════════════════╗
    # ║  TAB 3 — RDF TRIPLES ║
    # ╚══════════════════════╝
    with tab_rdf:
        _section_header("Live RDF Triples — ABox Population")
        st.caption(
            f"Showing RDF representation of the first "
            f"**{rdf_data['sample_individuals_count']} records** as Named Individuals. "
            f"Each row becomes a `Subject · Predicate · Object` triple."
        )

        fmt = st.radio(
            "Serialization format",
            ["Turtle (.ttl)", "JSON-LD"],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.write("")

        if fmt == "Turtle (.ttl)":
            st.code(rdf_data["turtle"], language="turtle")
            st.download_button(
                "📥  Download Turtle (.ttl)",
                data=rdf_data["turtle"],
                file_name=f"{table_name}_triples.ttl",
                mime="text/turtle",
                use_container_width=True,
            )
        else:
            st.code(rdf_data["json_ld"], language="json")
            st.download_button(
                "📥  Download JSON-LD (.jsonld)",
                data=rdf_data["json_ld"],
                file_name=f"{table_name}_triples.jsonld",
                mime="application/ld+json",
                use_container_width=True,
            )

    # ╔═════════════════════════╗
    # ║  TAB 4 — HOW TO EXPLAIN ║
    # ╚═════════════════════════╝
    with tab_explain:
        _section_header("What Happened — In Semantic Web Terms")
        _badges("TBox Induction", "Ontology Alignment", "ABox Triplification", "W3C Direct Mapping", "OBDA")

        _step(1, "TBox Induction (Schema Level)",
              f"The uploaded file's schema was parsed and aligned to the existing database using "
              f"<strong>ChromaDB vector embeddings</strong> (cosine similarity). The table received the OWL Class "
              f"definition <code>{owl_class} rdf:type owl:Class</code>. This is formally known as "
              f"<strong>Automated Ontology Alignment & Matching</strong>.")

        _step(2, "Semantic Labeling — CTA & CPA",
              "Every attribute was categorised as either <strong><code>owl:DatatypeProperty</code></strong> "
              "(strings, numbers, dates) or <strong><code>owl:ObjectProperty</code></strong> (foreign-key relations "
              "linking to other entities), and typed with W3C XML Schema Datatypes (<code>xsd:*</code>). "
              "This mirrors the <strong>ISWC SemTab Column Type Annotation</strong> challenge.")

        _step(3, "ABox Triplification (Instance Level)",
              "Each database row was converted into a <strong>Named Individual</strong> (Subject URI). "
              "Columns became <strong>Predicates</strong>, and cell values became <strong>Objects</strong>, "
              "forming Subject–Predicate–Object RDF triples following the "
              "<strong>W3C Direct Mapping Specification</strong>.")

        _step(4, "W3C R2RML Mapping Generated",
              "A <strong>Relational to RDF Mapping Language (R2RML)</strong> document was automatically "
              "generated. This is importable into Semantic Web platforms (Ontop, D2RQ, Jena) to expose "
              "the relational store as a live SPARQL endpoint.")

        _rule()
        _section_header("Defense Script for Evaluators")
        _quote(
            "Instead of treating uploaded spreadsheets as disconnected flat tables, our ingestion pipeline "
            "acts as a <strong>Knowledge Graph Construction Engine</strong>. We lift tabular data into the Semantic Web "
            "layer by generating W3C-compliant R2RML mappings, establishing TBox ontologies, and populating "
            "the ABox with RDF triples — forming the foundation of our "
            "<strong>Ontology-Based Data Access (OBDA)</strong> architecture."
        )

        _rule()
        _section_header("Common Evaluator Questions & Answers")

        with st.expander("Why MySQL instead of a native Triple Store (e.g., GraphDB)?"):
            _card(
                "This is the <strong>Virtual Knowledge Graph (VKG)</strong> / "
                "<strong>OBDA</strong> pattern, used in production Semantic Web systems like "
                "<strong>Ontop</strong>. Relational databases provide scalable storage and ACID guarantees, "
                "while our Semantic Layer exposes the data as an RDF Knowledge Graph on demand — "
                "exactly what W3C R2RML was designed for."
            )
        with st.expander("Where is the Ontology formally defined?"):
            _card(
                "The ontology (TBox) is <strong>dynamically induced</strong> from the relational schema: "
                "tables become <code>owl:Class</code> definitions, and columns become <code>owl:DatatypeProperty</code> "
                "or <code>owl:ObjectProperty</code> relations typed with <code>xsd:*</code> datatypes. "
                "The Knowledge Graph tab shows the full TBox graph."
            )
        with st.expander("What role do ChromaDB embeddings play in Semantic Web?"):
            _card(
                "ChromaDB acts as the <strong>Ontology Matching & Alignment layer</strong>. "
                "When new data arrives, vector similarity compares incoming column semantics against "
                "existing Knowledge Graph classes to prevent duplicate or disjoint concepts — "
                "a core task in the Semantic Web research area."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Main Page Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def data_ingestion_page():
    _inject_css()

    # Premium header card
    st.markdown("""
    <style>
    .di-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(16,185,129,0.06) 100%);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 16px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.4rem;
        position: relative;
        overflow: hidden;
    }
    .di-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #6366f1, #10b981, transparent);
    }
    .di-header h1 {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 50%, #6ee7b7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 !important;
        padding: 0 !important;
        letter-spacing: -0.03em;
    }
    .di-header p {
        color: #4b5563 !important;
        font-size: 0.86rem !important;
        margin: 0.4rem 0 0 0 !important;
    }
    </style>
    <div class="di-header">
        <h1>📥 Semantic Data Ingestion</h1>
        <p>Upload Excel, CSV or PDF · Gemini AI analysis · ChromaDB semantic matching · W3C R2RML Knowledge Graph generation</p>
    </div>
    """, unsafe_allow_html=True)

    _rule()

    # ── DB selection ─────────────────────────────────────────────────────────
    db_response = list_databases()
    if "error" in db_response:
        st.error(db_response["error"])
        st.info("Make sure the backend is running: `uvicorn main:app --reload`")
        return

    databases = db_response.get("databases", [])
    if not databases:
        st.warning("No databases found. Please create a database first.")
        return

    selected_db = st.selectbox("Target Knowledge Store (Database)", databases, key="ingest_db_select")
    st.write("")

    # ── Mode selector ─────────────────────────────────────────────────────────
    mode = st.radio(
        "Choose workflow",
        ["📤  Ingest a New File", "🔎  Inspect Existing Table"],
        horizontal=True,
        key="ingest_mode_radio",
        label_visibility="collapsed",
    )

    # ═══════════════════════════════════════
    #  MODE A — Ingest a new file
    # ═══════════════════════════════════════
    if mode == "📤  Ingest a New File":
        _rule()
        _section_header("Upload File")
        uploaded_file = st.file_uploader(
            "Supported: Excel (.xlsx / .xls), CSV, PDF",
            type=["xlsx", "xls", "csv", "pdf"],
            key="ingest_file_upload",
            label_visibility="collapsed",
        )

        if uploaded_file:
            st.caption(f"**{uploaded_file.name}** · {uploaded_file.size:,} bytes")

            if st.button(
                "🔍  Analyse, Match & Build Knowledge Graph",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner(
                    "Running Gemini AI analysis, ChromaDB semantic alignment, and Knowledge Graph construction…"
                ):
                    try:
                        import tempfile, os

                        suffix = os.path.splitext(uploaded_file.name)[1]
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        tmp.write(uploaded_file.getbuffer())
                        tmp.close()
                        try:
                            result = ingest_data_file(tmp.name, uploaded_file.name, selected_db)
                        finally:
                            try:
                                os.remove(tmp.name)
                            except Exception:
                                pass

                        if result.get("status") == "success":
                            st.session_state["last_ingestion_result"] = result
                            st.session_state["last_ingested_db"] = selected_db
                            st.rerun()
                        else:
                            st.error(f"Ingestion failed: {result.get('error', 'Unknown error')}")

                    except Exception as exc:
                        st.error(f"Error: {exc}")
                        import traceback
                        with st.expander("Stack trace"):
                            st.code(traceback.format_exc())

        # ── Show result if available ──────────────────────────────────────────
        if (
            "last_ingestion_result" in st.session_state
            and st.session_state.get("last_ingested_db") == selected_db
        ):
            result      = st.session_state["last_ingestion_result"]
            target_tbl  = result.get("table_name", "N/A")
            rows_added  = result.get("rows_added", 0)
            columns     = result.get("columns", [])
            matches     = result.get("matches", {})

            _rule()
            _section_header("Ingestion Summary")
            st.success("✅  File ingested and semantically aligned successfully.")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Table / OWL Class", target_tbl)
            with c2:
                st.metric("Records Ingested", rows_added)
            with c3:
                st.metric("Schema Attributes", len(columns))

            # Alignment diagnostics — collapsed by default to keep UI clean
            if matches:
                with st.expander("🔗  Schema Alignment Details", expanded=False):
                    if matches.get("table_match"):
                        tm = matches["table_match"]
                        st.write(
                            f"**Table matched:** `{tm.get('table_name')}` "
                            f"— cosine similarity **{tm.get('similarity', 0):.0%}**"
                        )
                    if matches.get("column_matches"):
                        st.write("**Attribute alignments:**")
                        for cm in matches["column_matches"]:
                            st.write(
                                f"  `{cm['source_column']}` → `{cm['target_column']}` "
                                f"({cm['similarity']:.0%})"
                            )
                    if matches.get("new_columns"):
                        st.write(f"**New attributes created:** {', '.join(matches['new_columns'])}")

            render_semantic_artifacts(
                table_name=target_tbl,
                columns=columns,
                rows_added=rows_added,
                selected_db=selected_db,
                matches=matches,
            )

    # ═══════════════════════════════════════
    #  MODE B — Inspect existing table
    # ═══════════════════════════════════════
    else:
        _rule()
        _section_header("Select Table to Explore")
        try:
            existing_tables = list_tables(selected_db).get("tables", [])
        except Exception as exc:
            st.error(f"Could not list tables: {exc}")
            return

        if not existing_tables:
            st.info("No tables found in this database.")
            return

        chosen = st.selectbox(
            "Available tables",
            existing_tables,
            key="inspect_table_select",
            label_visibility="collapsed",
        )

        if chosen:
            sample = execute_sql(f"SELECT * FROM `{chosen}` LIMIT 1;", selected_db)
            cols   = sample.get("columns", []) if sample.get("status") == "success" else []
            cnt_r  = execute_sql(f"SELECT COUNT(*) AS cnt FROM `{chosen}`;", selected_db)
            cnt    = cnt_r.get("rows", [{}])[0].get("cnt", 0) if cnt_r.get("status") == "success" else 0

            render_semantic_artifacts(
                table_name=chosen,
                columns=cols,
                rows_added=cnt,
                selected_db=selected_db,
            )

    # ── Footer — ChromaDB re-sync ─────────────────────────────────────────────
    _rule()
    if st.button("🔄  Re-sync ChromaDB Schema Embeddings", key="refresh_chroma"):
        try:
            r = requests.post("http://127.0.0.1:8000/api/refresh/", json={"db_name": selected_db})
            if r.status_code == 200:
                st.success("ChromaDB schema embeddings re-synchronised.")
            else:
                st.error(f"Server error: {r.text}")
        except Exception as exc:
            st.error(f"Connection error: {exc}")
