import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from utils.api import (
    list_databases,
    get_graph_status,
    get_graph_data,
    search_graph_entities,
    semantic_search_graph,
    get_entity_neighbors,
    get_table_relationships,
    sync_schema_to_graph,
)

# ─── Color palette for node types ────────────────────────────────────────────
NODE_COLORS = {
    "DatabaseTable":  "#38BDF8",   # Sky blue   — DB table nodes
    "DatabaseColumn": "#64748B",   # Slate      — column nodes
    "Document":       "#FBBF24",   # Amber      — ingested file nodes
    "Entity":         "#A855F7",   # Purple     — extracted entities
    "Organization":   "#EC4899",   # Pink
    "Person":         "#10B981",   # Emerald
    "Location":       "#F97316",   # Orange
    "Product":        "#6366F1",   # Indigo
    "Concept":        "#14B8A6",   # Teal
    "default":        "#8B5CF6",   # Violet
}

NODE_SIZE = {
    "DatabaseTable": 36,
    "Document":      30,
    "Entity":        24,
    "DatabaseColumn": 18,
    "default":       22,
}


def _node_id(node: dict) -> str:
    """
    Return a stable, unique string ID for any Neo4j node.

    Neo4j nodes use different ID fields depending on their label:
      - Entity / Document  → 'id'
      - DatabaseTable      → 'unique_key'  (e.g. "file2sql.chrome_timeline")
      - DatabaseColumn     → 'unique_key'  (e.g. "file2sql.chrome_timeline.col1")

    We try all candidates in priority order, falling back to name/? so we
    never return "None" (which makes all un-identified nodes collapse together).
    """
    for key in ("id", "unique_key", "name"):
        val = node.get(key)
        if val and str(val) != "None":
            return str(val)
    return str(id(node))          # last resort: Python object id (always unique)


def _get_node_color(labels: list, entity_type: str = "") -> str:
    for lbl in labels:
        if lbl in NODE_COLORS:
            return NODE_COLORS[lbl]
    if entity_type in NODE_COLORS:
        return NODE_COLORS[entity_type]
    return NODE_COLORS["default"]


def _get_node_size(labels: list) -> int:
    for lbl in labels:
        if lbl in NODE_SIZE:
            return NODE_SIZE[lbl]
    return NODE_SIZE["default"]


def render_graph_plotly(nodes: list, edges: list, title: str = "Knowledge Graph"):
    """
    Render an interactive Plotly force-directed graph from Neo4j nodes/edges.

    Key fix: every node gets a stable unique ID via _node_id(), which handles
    both 'id' (Entity/Document) and 'unique_key' (DatabaseTable/DatabaseColumn).
    Edges reference those same IDs so all connections render correctly.
    """
    if not nodes:
        st.info("📭 No graph nodes to display. Try syncing the DB schema first (button above).")
        return

    G = nx.Graph()
    node_meta: dict[str, dict] = {}

    # Build networkx graph from Neo4j node dicts
    for n in nodes:
        nid    = _node_id(n)
        labels = n.get("labels", [])
        name   = n.get("name") or nid.split(".")[-1]   # use last segment as display name
        ntype  = labels[0] if labels else "Entity"

        G.add_node(nid)
        # Store all original node properties for hover/inspector display
        props = {k: v for k, v in n.items() if k not in ("labels",)}
        node_meta[nid] = {
            "name":    name,
            "labels":  ", ".join(labels),
            "type":    ntype,
            "color":   _get_node_color(labels, n.get("type", "")),
            "size":    _get_node_size(labels),
            "raw":     n,            # full original dict for inspector
            "props":   props,
        }

    # Add edges — use same _node_id logic for from/to resolution
    edge_labels: dict[tuple, str] = {}
    for e in edges:
        u   = str(e.get("from", ""))
        v   = str(e.get("to",   ""))
        rel = e.get("type", "RELATED_TO")
        if u and v and u in node_meta and v in node_meta:
            G.add_edge(u, v, label=rel)
            edge_labels[(u, v)] = rel

    if len(G.nodes()) == 0:
        st.warning("Graph nodes exist but none could be matched to edges. Check Neo4j data.")
        return

    # ── Spring layout ──
    k_val = max(0.5, 2.0 / max(len(G.nodes()), 1) ** 0.5)
    pos = nx.spring_layout(G, k=k_val, seed=42, iterations=80)

    # ── Edge traces ──
    edge_x, edge_y = [], []
    mid_x, mid_y, mid_labels = [], [], []

    for u, v, data in G.edges(data=True):
        if u not in pos or v not in pos:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        mid_x.append((x0 + x1) / 2)
        mid_y.append((y0 + y1) / 2)
        mid_labels.append(data.get("label", ""))

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color="rgba(99,102,241,0.25)"),
        hoverinfo="none",
        mode="lines",
    )

    # Edge-label annotations placed at midpoints
    edge_label_trace = go.Scatter(
        x=mid_x, y=mid_y,
        mode="text",
        text=mid_labels,
        textfont=dict(size=9, color="#94A3B8"),
        hoverinfo="none",
    )

    # ── Node traces (one scatter per type for legend) ──
    # Group nodes by type so we can draw a colour legend
    type_groups: dict[str, list] = {}
    for nid in G.nodes():
        if nid not in pos:
            continue
        meta = node_meta.get(nid, {})
        ntype = meta.get("type", "Entity")
        type_groups.setdefault(ntype, []).append(nid)

    node_traces = []
    for ntype, nids in type_groups.items():
        xs, ys, texts, hovers, colors, sizes = [], [], [], [], [], []
        sample_meta = node_meta.get(nids[0], {})
        color = sample_meta.get("color", NODE_COLORS["default"])

        for nid in nids:
            x, y = pos[nid]
            meta = node_meta.get(nid, {})
            name = meta.get("name", nid)
            display = (name[:15] + "…") if len(name) > 16 else name
            xs.append(x); ys.append(y)
            texts.append(display)
            colors.append(meta.get("color", color))
            sizes.append(meta.get("size", 22))

            # Build rich hover card
            p = meta.get("props", {})
            prop_lines = "<br>".join(
                f"&nbsp;&nbsp;<b>{k}</b>: {str(v)[:60]}"
                for k, v in list(p.items())[:8]
                if v is not None
            )
            hovers.append(
                f"<b>{name}</b><br>"
                f"<i>Type: {ntype}</i><br>"
                f"<i>Labels: {meta.get('labels')}</i>"
                + (f"<br><br>{prop_lines}" if prop_lines else "")
            )

        node_traces.append(go.Scatter(
            x=xs, y=ys,
            name=ntype,
            mode="markers+text",
            hoverinfo="text",
            hovertext=hovers,
            text=texts,
            textposition="bottom center",
            textfont=dict(size=10, color="#CBD5E1"),
            marker=dict(
                color=colors,
                size=sizes,
                line=dict(width=2, color="#0F172A"),
                symbol="circle",
            ),
            showlegend=True,
        ))

    all_traces = [edge_trace, edge_label_trace] + node_traces

    fig = go.Figure(data=all_traces, layout=go.Layout(
        title=dict(text=title, font=dict(size=13, color="#64748b", family="Inter")),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.01,
            xanchor="left",   x=0,
            font=dict(color="#94a3b8", size=11, family="Inter"),
            bgcolor="rgba(8,14,28,0.8)",
            bordercolor="rgba(51,65,85,0.4)",
            borderwidth=1,
        ),
        hovermode="closest",
        margin=dict(b=20, l=10, r=10, t=60),
        plot_bgcolor="#080e1c",
        paper_bgcolor="#080e1c",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=580,
    ))

    st.plotly_chart(fig, use_container_width=True)


# ─── Legend helper ────────────────────────────────────────────────────────────
def _render_legend():
    cols = st.columns(len(NODE_COLORS) - 1)
    items = [(k, v) for k, v in NODE_COLORS.items() if k != "default"]
    for col, (label, color) in zip(cols, items):
        col.markdown(
            f"<div style='display:flex;align-items:center;gap:6px;'>"
            f"<div style='width:14px;height:14px;border-radius:50%;background:{color}'></div>"
            f"<span style='font-size:0.75rem;color:#94A3B8'>{label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─── Premium CSS ─────────────────────────────────────────────────────────────
_KG_CSS = """
<style>
.kg-header {
    background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(6,182,212,0.06) 100%);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 16px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.4rem;
    position: relative;
    overflow: hidden;
}
.kg-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #6366f1, #06b6d4, transparent);
}
.kg-header h1 {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 50%, #67e8f9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 !important;
    padding: 0 !important;
    letter-spacing: -0.03em;
}
.kg-header p {
    color: #4b5563 !important;
    font-size: 0.86rem !important;
    margin: 0.4rem 0 0 0 !important;
}
.kg-status-active {
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 10px;
    padding: 0.8rem 1.2rem;
    color: #6ee7b7;
    font-size: 0.88rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.kg-status-offline {
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.25);
    border-radius: 10px;
    padding: 0.8rem 1.2rem;
    color: #fbbf24;
    font-size: 0.86rem;
    line-height: 1.6;
}
.kg-status-offline code {
    background: rgba(0,0,0,0.3);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.8rem;
    color: #fcd34d;
}
</style>
"""

# ─── Main page ────────────────────────────────────────────────────────────────
def knowledge_graph_page():
    st.markdown(_KG_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="kg-header">
        <h1>🕸️ Semantic Knowledge Graph Explorer</h1>
        <p>Visualise MySQL schema nodes · ingested documents · extracted business entities · Neo4j + ChromaDB hybrid retrieval</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Graph Status Banner ──────────────────────────────────────────────────
    status_info = get_graph_status()
    is_active   = status_info.get("graph_available", False)

    hdr_col, db_col = st.columns([3, 1])
    with hdr_col:
        if is_active:
            st.markdown(
                "<div class='kg-status-active'>🟢 <strong>Knowledge Graph Engine Active</strong> — Neo4j connected and ready</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div class='kg-status-offline'>"
                "🟠 <strong>Graph Service Offline or Not Configured</strong><br>"
                "Core NL2SQL and ingestion features still work normally via ChromaDB only.<br>"
                "To enable Neo4j: add <code>NEO4J_URI</code>, <code>NEO4J_USER</code>, <code>NEO4J_PASSWORD</code> to <code>.env</code> and restart."
                "</div>",
                unsafe_allow_html=True
            )

    with db_col:
        dbs_res     = list_databases()
        dbs         = dbs_res.get("databases", [])
        selected_db = st.selectbox("Database scope", ["(All Databases)"] + dbs, label_visibility="collapsed")
        active_db   = None if selected_db == "(All Databases)" else selected_db

    st.write("")

    # ── Schema Sync action ───────────────────────────────────────────────────
    if is_active and active_db:
        sync_col, info_col = st.columns([1, 3])
        with sync_col:
            if st.button("🔄 Sync DB Schema → Graph", key="btn_sync", use_container_width=True):
                with st.spinner(f"Syncing '{active_db}' tables & columns into Neo4j…"):
                    res = sync_schema_to_graph(active_db)
                if res.get("status") == "success":
                    st.toast(res.get("message", "Synced!"), icon="✅")
                    st.rerun()
                else:
                    st.error(res.get("error", "Sync failed. Check backend logs."))
        with info_col:
            st.markdown(
                "<div style='font-size:0.8rem;color:#4b5563;padding-top:0.6rem;'>"
                "Reads every table & column from MySQL → upserts as <code style='color:#818cf8'>DatabaseTable</code> / "
                "<code style='color:#818cf8'>DatabaseColumn</code> nodes in Neo4j. "
                "Foreign keys become <code style='color:#818cf8'>RELATED_TO</code> edges."
                "</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_view, tab_search, tab_rels, tab_debug = st.tabs([
        "🌐 Graph Visualisation",
        "🔍 Semantic Search",
        "🔗 Table Relationships",
        "🛠️ Debug / Raw Data",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — Graph Visualisation
    # ════════════════════════════════════════════════════════════════
    with tab_view:
        st.markdown(
            "**How to read this graph:** Each coloured circle is a graph node. "
            "Hover over any node to see its properties. Lines between nodes are relationships. "
            "Use the filter below to focus on a specific node type."
        )
        _render_legend()
        st.markdown("")

        f1, f2, f3 = st.columns([2, 2, 1])
        with f1:
            filter_type = st.selectbox(
                "Filter by Node Type",
                ["All Types", "DatabaseTable", "DatabaseColumn", "Document", "Entity"],
                key="filter_type",
            )
        with f2:
            max_nodes = st.slider("Max nodes to fetch from Neo4j", 20, 400, 150, 20)
        with f3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🔄 Refresh", key="btn_refresh"):
                st.rerun()

        with st.spinner("Fetching graph from Neo4j…"):
            graph_data = get_graph_data(db_name=active_db, limit=max_nodes)

        raw_nodes = graph_data.get("nodes", [])
        raw_edges = graph_data.get("edges", [])

        # Apply node-type filter
        if filter_type != "All Types":
            raw_nodes = [n for n in raw_nodes if filter_type in n.get("labels", [])]
            kept_ids  = {_node_id(n) for n in raw_nodes}
            raw_edges = [
                e for e in raw_edges
                if str(e.get("from", "")) in kept_ids
                and str(e.get("to", "")) in kept_ids
            ]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nodes", len(raw_nodes))
        m2.metric("Edges", len(raw_edges))
        m3.metric("Scope", active_db or "All DBs")
        type_counts = {}
        for n in raw_nodes:
            lbl = n.get("labels", ["?"])[0]
            type_counts[lbl] = type_counts.get(lbl, 0) + 1
        m4.metric("Node Types", len(type_counts))

        render_graph_plotly(
            raw_nodes, raw_edges,
            title=f"Knowledge Graph — {active_db or 'All Databases'} ({len(raw_nodes)} nodes)"
        )

        # Node inspector
        if raw_nodes:
            with st.expander("📋 Node Attribute Inspector", expanded=False):
                st.markdown(
                    "Select any node below to inspect its full Neo4j property set. "
                    "This is especially useful for debugging ingested entity nodes."
                )
                options = [
                    f"{n.get('name', _node_id(n))} [{', '.join(n.get('labels', []))}]"
                    for n in raw_nodes
                ]
                choice = st.selectbox("Pick a node:", options, key="node_inspector")
                if choice:
                    idx = options.index(choice)
                    sel = raw_nodes[idx]
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Node Properties**")
                        for k, v in sel.items():
                            if k != "labels":
                                st.markdown(f"- **{k}**: `{v}`")
                    with c2:
                        st.markdown("**Labels**")
                        for lbl in sel.get("labels", []):
                            color = NODE_COLORS.get(lbl, NODE_COLORS["default"])
                            st.markdown(
                                f"<span style='background:{color};color:#fff;"
                                f"border-radius:4px;padding:2px 8px;font-size:0.8rem'>{lbl}</span>",
                                unsafe_allow_html=True,
                            )
                        st.markdown("")
                        st.markdown("**Raw JSON**")
                        st.json(sel)

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — Semantic Search
    # ════════════════════════════════════════════════════════════════
    with tab_search:
        st.subheader("Extract Entities from Natural Language and Retrieve Matching Subgraph")
        st.markdown(
            """
            This is the **same hybrid-retrieval path** used by the NL→SQL engine.
            Enter any business question to see:
            1. Which **entities** the system extracts from your question.
            2. Which **graph nodes & edges** it finds as hints.
            3. The exact **context block** that gets injected into the Gemini prompt.
            """
        )

        example_q = st.selectbox(
            "Load an example question (or type your own below)",
            [
                "Custom question ↓",
                "Show total sales by customer in California for 2024",
                "Which vendors supply high-priority electronic components?",
                "List all employees who joined after 2021 by department",
                "Top 10 products by revenue last month",
            ],
        )
        if example_q == "Custom question ↓":
            question = st.text_input(
                "Your question",
                placeholder="e.g. How many orders are pending for each vendor?",
            )
        else:
            question = st.text_input("Your question", value=example_q)

        if st.button("🚀 Extract Entities & Retrieve Subgraph", key="btn_sem"):
            if not question.strip():
                st.warning("Please enter a question first.")
            else:
                with st.spinner("Querying graph…"):
                    sem_res = semantic_search_graph(question, db_name=active_db)

                ents   = sem_res.get("entities_found", [])
                s_nodes = sem_res.get("nodes", [])
                s_edges = sem_res.get("edges", [])

                st.markdown(f"**Extracted entities:** `{ents}`")

                if not is_active:
                    st.info(
                        "Graph layer is offline — connect Neo4j to see graph hints here. "
                        "The NL2SQL engine still works using ChromaDB only."
                    )
                elif s_nodes:
                    st.success(
                        f"Found **{len(s_nodes)} nodes** and **{len(s_edges)} edges** "
                        f"relevant to this question."
                    )
                    render_graph_plotly(
                        s_nodes, s_edges,
                        title=f"Hybrid Retrieval Subgraph: \"{question[:50]}…\""
                    )

                    with st.expander("📄 Context block injected into Gemini prompt"):
                        lines = ["Knowledge Graph context (use as hints only):"]
                        for n in s_nodes:
                            lbl = (n.get("labels") or ["Entity"])[0]
                            lines.append(f"  • [{lbl}] {n.get('name', _node_id(n))}")
                        for e in s_edges:
                            lines.append(f"  • {e.get('from')} --[{e.get('type')}]--> {e.get('to')}")
                        st.code("\n".join(lines), language="yaml")
                else:
                    st.info(
                        "No matching graph nodes found for those entities. "
                        "Sync the DB schema or ingest files first to populate the graph."
                    )

        # Text search
        st.markdown("---")
        st.subheader("🔎 Entity Name Search")
        st.markdown("Search for any entity by name substring across the entire knowledge graph.")
        search_q = st.text_input("Search entities", placeholder="e.g. customer, vendor, product…", key="ent_search")
        etype_filter = st.selectbox("Entity type filter", ["(Any type)", "Entity", "DatabaseTable", "Document"], key="etype_sel")
        if st.button("Search", key="btn_ent_search") and search_q.strip():
            etype = None if etype_filter == "(Any type)" else etype_filter
            with st.spinner("Searching…"):
                res = search_graph_entities(search_q, entity_type=etype)
            results = res.get("results", [])
            if results:
                st.markdown(f"**{len(results)} results:**")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No entities found matching that name.")

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — Table Relationships
    # ════════════════════════════════════════════════════════════════
    with tab_rels:
        st.subheader("Table-to-Table Relationships (Foreign Keys & Semantic Links)")
        st.markdown(
            "These relationships are stored in Neo4j as `RELATED_TO` edges between "
            "`DatabaseTable` nodes. They come from two sources:\n"
            "- **`foreign_key`** — detected directly from MySQL `INFORMATION_SCHEMA`\n"
            "- **`semantic`** — inferred by the entity extractor from cross-column references"
        )

        if not active_db:
            st.info("Select a specific database from the top dropdown to view its schema relationships.")
        else:
            with st.spinner(f"Fetching relationships for '{active_db}'…"):
                rels_data = get_table_relationships(active_db)
            rels = rels_data.get("relationships", [])

            if rels:
                df_rels = pd.DataFrame(rels)
                st.dataframe(df_rels, use_container_width=True)

                # Mini relationship graph
                st.markdown("**Relationship Graph (Tables only)**")
                rel_nodes_raw = []
                seen = set()
                rel_edges_raw = []
                for r in rels:
                    for tname in (r.get("from_table"), r.get("to_table")):
                        if tname and tname not in seen:
                            seen.add(tname)
                            rel_nodes_raw.append({
                                "id": f"{active_db}.{tname}",
                                "name": tname,
                                "labels": ["DatabaseTable"],
                                "unique_key": f"{active_db}.{tname}",
                            })
                    rel_edges_raw.append({
                        "from": f"{active_db}.{r.get('from_table')}",
                        "to":   f"{active_db}.{r.get('to_table')}",
                        "type": r.get("source", "RELATED_TO").upper(),
                    })
                if rel_nodes_raw:
                    render_graph_plotly(rel_nodes_raw, rel_edges_raw, title=f"Table Relationships — {active_db}")
            else:
                st.info(
                    f"No table relationships in Neo4j for `{active_db}` yet.\n\n"
                    "**To create them:** click **🔄 Sync DB Schema → Graph** at the top of this page. "
                    "Foreign keys detected in MySQL will automatically become `RELATED_TO` edges."
                )

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — Debug / Raw Data
    # ════════════════════════════════════════════════════════════════
    with tab_debug:
        st.subheader("🛠️ Raw Graph API Response Debugger")
        st.markdown(
            "Inspect the exact JSON returned by the backend graph API. "
            "Useful for diagnosing data quality or node ID mismatches."
        )

        debug_limit = st.slider("Fetch limit", 5, 100, 20, key="debug_limit")
        if st.button("Fetch Raw Graph Data", key="btn_debug_fetch"):
            with st.spinner("Fetching…"):
                raw = get_graph_data(db_name=active_db, limit=debug_limit)
            raw_nodes_d = raw.get("nodes", [])
            raw_edges_d = raw.get("edges", [])

            st.markdown(f"**{len(raw_nodes_d)} nodes, {len(raw_edges_d)} edges**")

            with st.expander("Node list (first 30)", expanded=True):
                for n in raw_nodes_d[:30]:
                    nid = _node_id(n)
                    st.markdown(
                        f"`{nid}` → labels: **{n.get('labels')}**, name: `{n.get('name')}`"
                    )

            with st.expander("Edge list (first 30)"):
                for e in raw_edges_d[:30]:
                    st.markdown(
                        f"`{e.get('from')}` --[**{e.get('type')}**]--> `{e.get('to')}`"
                    )

            with st.expander("Full raw JSON"):
                st.json(raw)
