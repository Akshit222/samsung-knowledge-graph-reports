"""
Semantic Engine for Knowledge Graph Construction & Ingestion
Provides W3C Direct Mapping, R2RML Generation, RDF Triplification (Turtle / JSON-LD),
Column Type Annotation (CTA), Column Property Annotation (CPA), and Interactive Graph Visualization.
"""
import re
import json
import networkx as nx
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional

def sanitize_term(name: str) -> str:
    """Turn arbitrary column or table names into clean URI-safe identifiers."""
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip())
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    return cleaned or "property"

def to_pascal_case(name: str) -> str:
    """Convert snake_case or regular string to PascalCase for OWL Classes."""
    words = re.findall(r'[a-zA-Z0-9]+', str(name))
    if not words:
        return "Concept"
    return "".join(w.capitalize() for w in words)

def annotate_columns(columns: List[str], sample_rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Performs CTA (Column Type Annotation) and CPA (Column Property Annotation).
    Maps raw table attributes to:
      - OWL Property Type (DatatypeProperty vs ObjectProperty)
      - XSD Datatype (xsd:string, xsd:integer, xsd:decimal, xsd:dateTime)
      - Schema.org / Linked Data Concept
    """
    annotations = []
    sample_rows = sample_rows or []

    for col in columns:
        col_clean = str(col).strip()
        col_lower = col_clean.lower()
        
        # Inspect sample values if available
        sample_vals = [r.get(col) for r in sample_rows if col in r and r.get(col) is not None]
        first_val = sample_vals[0] if sample_vals else None
        
        is_id = bool(re.search(r'(^id$|_id$|^pk$|code$|guid$|uuid$)', col_lower))
        is_name = bool(re.search(r'(name|title|label|desc|description)', col_lower))
        is_price = bool(re.search(r'(price|salary|cost|amount|revenue|total|fee|tax|rate)', col_lower))
        is_date = bool(re.search(r'(date|time|created|updated|year|timestamp|day|month)', col_lower))
        is_email = bool(re.search(r'(email|mail)', col_lower))
        is_phone = bool(re.search(r'(phone|tel|mobile|contact)', col_lower))
        is_location = bool(re.search(r'(city|country|state|address|location|zip|postal)', col_lower))
        is_url = bool(re.search(r'(url|link|website|uri)', col_lower))
        
        # Determine XSD Datatype & OWL Property Type
        if is_id and col_lower not in ('name', 'title'):
            if col_lower == 'id' or col_lower.startswith('pk'):
                owl_type = "owl:FunctionalProperty"
                xsd_type = "xsd:string" if isinstance(first_val, str) else "xsd:integer"
                schema_map = "schema:identifier"
                cpa_role = "Primary Entity Identifier (Subject URI anchor)"
            else:
                owl_type = "owl:ObjectProperty"
                xsd_type = "xsd:anyURI"
                # Target class guess from foreign key name (e.g. dept_id -> Department)
                target_cls = to_pascal_case(re.sub(r'(_id|id)$', '', col_lower) or "Entity")
                schema_map = f":has{target_cls}"
                cpa_role = f"Foreign Relation to :{target_cls}"
        elif is_price:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:decimal"
            schema_map = "schema:price" if "price" in col_lower or "cost" in col_lower else "schema:baseSalary"
            cpa_role = "Monetary / Quantitative Attribute"
        elif is_date:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:dateTime" if "time" in col_lower else "xsd:date"
            schema_map = "schema:dateCreated" if "create" in col_lower else "schema:temporalCoverage"
            cpa_role = "Temporal Annotation"
        elif is_email:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:string"
            schema_map = "schema:email"
            cpa_role = "Contact Communication Property"
        elif is_phone:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:string"
            schema_map = "schema:telephone"
            cpa_role = "Contact Communication Property"
        elif is_location:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:string"
            schema_map = "schema:Place"
            cpa_role = "Spatial / Geographic Attribute"
        elif is_url:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:anyURI"
            schema_map = "schema:url"
            cpa_role = "Web Resource Reference"
        elif is_name:
            owl_type = "owl:DatatypeProperty"
            xsd_type = "xsd:string"
            schema_map = "schema:name"
            cpa_role = "Human-Readable Concept Label (rdfs:label)"
        else:
            # Type inference from sample value
            if first_val is not None and isinstance(first_val, (int, float)):
                xsd_type = "xsd:integer" if isinstance(first_val, int) else "xsd:float"
                owl_type = "owl:DatatypeProperty"
                schema_map = f"schema:value"
                cpa_role = "Numeric Measure"
            elif first_val is not None and isinstance(first_val, bool):
                xsd_type = "xsd:boolean"
                owl_type = "owl:DatatypeProperty"
                schema_map = f"schema:flag"
                cpa_role = "Boolean Condition"
            else:
                xsd_type = "xsd:string"
                owl_type = "owl:DatatypeProperty"
                schema_map = f"schema:Text"
                cpa_role = "Descriptive Literal Property"

        annotations.append({
            "column": col_clean,
            "sanitized_predicate": f":has_{sanitize_term(col_clean)}",
            "owl_type": owl_type,
            "xsd_type": xsd_type,
            "schema_concept": schema_map,
            "cpa_role": cpa_role
        })

    return annotations


def generate_r2rml(table_name: str, annotations: List[Dict[str, Any]]) -> str:
    """
    Generates valid W3C R2RML (Relational to RDF Mapping Language) mapping in Turtle format.
    Standardized by W3C REC-r2rml-20120927.
    """
    safe_table = sanitize_term(table_name)
    class_name = to_pascal_case(safe_table)
    
    # Identify primary key column if available, else first column
    pk_col = annotations[0]["column"] if annotations else "id"
    for ann in annotations:
        if ann["owl_type"] == "owl:FunctionalProperty":
            pk_col = ann["column"]
            break

    r2rml_lines = [
        "@prefix rr: <http://www.w3.org/ns/r2rml#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix schema: <http://schema.org/> .",
        f"@prefix : <http://example.org/ontology/{safe_table}#> .",
        f"@prefix data: <http://example.org/data/{safe_table}/> .",
        "",
        f"<#TriplesMap_{safe_table}>",
        "    a rr:TriplesMap ;",
        "    rr:logicalTable [",
        f'        rr:tableName "{table_name}"',
        "    ] ;",
        "    rr:subjectMap [",
        f'        rr:template "http://example.org/data/{safe_table}/{{{pk_col}}}" ;',
        f"        rr:class :{class_name} ;",
        "    ] ;"
    ]

    for ann in annotations:
        col = ann["column"]
        predicate = ann["sanitized_predicate"]
        xsd_type = ann["xsd_type"]
        owl_type = ann["owl_type"]

        if owl_type == "owl:ObjectProperty":
            target_class = to_pascal_case(re.sub(r'(_id|id)$', '', col.lower()) or "Resource")
            r2rml_lines.extend([
                "    rr:predicateObjectMap [",
                f"        rr:predicate {predicate} ;",
                "        rr:objectMap [",
                f'            rr:template "http://example.org/data/{target_class.lower()}/{{{col}}}" ;',
                "            rr:termType rr:IRI ;",
                "        ] ;",
                "    ] ;"
            ])
        else:
            r2rml_lines.extend([
                "    rr:predicateObjectMap [",
                f"        rr:predicate {predicate} ;",
                "        rr:objectMap [",
                f'            rr:column "{col}" ;',
                f"            rr:datatype {xsd_type} ;",
                "        ] ;",
                "    ] ;"
            ])

    # Replace last semicolon with period
    if r2rml_lines[-1] == "    ] ;":
        r2rml_lines[-1] = "    ] ."

    return "\n".join(r2rml_lines)


def generate_rdf_triples(
    table_name: str,
    annotations: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    limit: int = 5
) -> Dict[str, Any]:
    """
    Generates W3C RDF Triples (Turtle format & JSON-LD) from actual table rows.
    """
    safe_table = sanitize_term(table_name)
    class_name = to_pascal_case(safe_table)
    
    # Identify subject key column
    pk_col = annotations[0]["column"] if annotations else "id"
    for ann in annotations:
        if ann["owl_type"] == "owl:FunctionalProperty":
            pk_col = ann["column"]
            break

    turtle_prefixes = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix schema: <http://schema.org/> .",
        f"@prefix : <http://example.org/ontology/{safe_table}#> .",
        f"@prefix data: <http://example.org/data/{safe_table}/> .",
        ""
    ]
    
    triple_blocks = []
    json_ld_nodes = []
    total_triples_count = 0

    display_rows = rows[:limit] if rows else []

    for idx, row in enumerate(display_rows):
        subject_id = row.get(pk_col)
        if subject_id is None or str(subject_id).strip() == "":
            subject_id = f"row_{idx + 1}"
        else:
            subject_id = sanitize_term(str(subject_id))

        subject_uri = f"data:{safe_table}_{subject_id}"
        
        # Turtle block
        ttl_lines = [f"{subject_uri} a :{class_name} ;"]
        total_triples_count += 1
        
        # JSON-LD dict
        json_ld_node = {
            "@id": f"http://example.org/data/{safe_table}/{subject_id}",
            "@type": f"http://example.org/ontology/{safe_table}#{class_name}"
        }

        prop_statements = []
        for ann in annotations:
            col = ann["column"]
            val = row.get(col)
            if val is None or str(val).strip() == "":
                continue

            pred = ann["sanitized_predicate"]
            xsd_type = ann["xsd_type"]
            owl_type = ann["owl_type"]

            # Format value
            if owl_type == "owl:ObjectProperty":
                target_cls = to_pascal_case(re.sub(r'(_id|id)$', '', col.lower()) or "Resource")
                obj_str = f"data:{target_cls.lower()}_{sanitize_term(str(val))}"
                json_ld_node[pred] = {"@id": f"http://example.org/data/{target_cls.lower()}/{val}"}
            elif xsd_type in ("xsd:integer", "xsd:float", "xsd:decimal") and isinstance(val, (int, float)):
                obj_str = f'"{val}"^^{xsd_type}'
                json_ld_node[pred] = val
            elif xsd_type == "xsd:boolean" and isinstance(val, bool):
                obj_str = f'"{str(val).lower()}"^^xsd:boolean'
                json_ld_node[pred] = val
            else:
                # String or escaped literal
                escaped_val = str(val).replace('"', '\\"')
                obj_str = f'"{escaped_val}"^^{xsd_type}'
                json_ld_node[pred] = str(val)

            prop_statements.append(f"    {pred} {obj_str} ;")
            total_triples_count += 1

        if prop_statements:
            prop_statements[-1] = prop_statements[-1][:-1] + "."
            ttl_lines.extend(prop_statements)
        else:
            ttl_lines[-1] = ttl_lines[-1][:-1] + "."

        triple_blocks.append("\n".join(ttl_lines))
        json_ld_nodes.append(json_ld_node)

    full_turtle = "\n".join(turtle_prefixes) + "\n\n".join(triple_blocks)
    
    full_json_ld = {
        "@context": {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "schema": "http://schema.org/",
            ":": f"http://example.org/ontology/{safe_table}#",
            "data": f"http://example.org/data/{safe_table}/"
        },
        "@graph": json_ld_nodes
    }

    return {
        "turtle": full_turtle,
        "json_ld": json.dumps(full_json_ld, indent=2),
        "triples_preview_count": total_triples_count,
        "sample_individuals_count": len(display_rows)
    }


def generate_knowledge_graph_figure(
    table_name: str,
    annotations: List[Dict[str, Any]],
    other_tables: Optional[List[str]] = None
) -> go.Figure:
    """
    Creates an interactive, aesthetic Knowledge Graph (NetworkX + Plotly)
    visualizing the induced TBox (OWL Classes and Properties).
    """
    G = nx.DiGraph()
    safe_table = sanitize_term(table_name)
    main_class_node = f":{to_pascal_case(safe_table)}"

    # Add Class Node
    G.add_node(
        main_class_node,
        node_type="Class",
        category="OWL Class (TBox)",
        label=f"owl:Class\n{main_class_node}",
        color="#8B5CF6",  # Violet / Indigo
        size=36
    )

    other_tables = other_tables or []
    connected_other_classes = set()

    for ann in annotations:
        col = ann["column"]
        pred_label = ann["sanitized_predicate"]
        xsd_type = ann["xsd_type"]
        owl_type = ann["owl_type"]
        prop_node_name = f"{pred_label}\n({xsd_type})"

        if owl_type == "owl:ObjectProperty":
            # Target class node
            target_cls = to_pascal_case(re.sub(r'(_id|id)$', '', col.lower()) or "Entity")
            target_class_node = f":{target_cls}"
            connected_other_classes.add(target_class_node)

            if target_class_node not in G:
                G.add_node(
                    target_class_node,
                    node_type="Class",
                    category="Linked OWL Class",
                    label=f"owl:Class\n{target_class_node}",
                    color="#EC4899",  # Pink / Rose
                    size=30
                )
            # Edge from main class to linked class
            G.add_edge(main_class_node, target_class_node, relation=pred_label, rel_type="owl:ObjectProperty")
        else:
            # Datatype property node
            G.add_node(
                prop_node_name,
                node_type="Property",
                category="owl:DatatypeProperty",
                label=f"{pred_label}\n({xsd_type})",
                color="#06B6D4",  # Cyan
                size=20
            )
            G.add_edge(main_class_node, prop_node_name, relation="hasProperty", rel_type="owl:DatatypeProperty")

    # Add 1-2 existing tables as context if not already linked
    for ot in other_tables[:3]:
        ot_class = f":{to_pascal_case(sanitize_term(ot))}"
        if ot_class != main_class_node and ot_class not in G:
            G.add_node(
                ot_class,
                node_type="Class",
                category="Existing Knowledge Graph Class",
                label=f"owl:Class\n{ot_class}",
                color="#64748B",  # Slate gray
                size=24
            )

    # Compute Layout
    pos = nx.spring_layout(G, k=0.9, seed=42)

    # Extract edge traces
    edge_x = []
    edge_y = []
    edge_text = []
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_text.append(edge[2].get("relation", ""))

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.5, color="#475569"),
        hoverinfo='none',
        mode='lines'
    )

    # Extract node traces
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []
    hover_text = []

    for node in G.nodes(data=True):
        x, y = pos[node[0]]
        node_x.append(x)
        node_y.append(y)
        meta = node[1]
        node_color.append(meta.get("color", "#8B5CF6"))
        node_size.append(meta.get("size", 24))
        node_text.append(meta.get("label", node[0]))
        hover_text.append(
            f"<b>Node:</b> {node[0]}<br>"
            f"<b>Type:</b> {meta.get('node_type')}<br>"
            f"<b>Category:</b> {meta.get('category')}<br>"
            f"<b>Standard:</b> W3C OWL / RDF Specification"
        )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[n.split('\n')[0] for n in node_text],
        textposition="bottom center",
        textfont=dict(size=11, color="#E2E8F0"),
        hovertext=hover_text,
        marker=dict(
            showscale=False,
            color=node_color,
            size=node_size,
            line=dict(width=2, color='#FFFFFF')
        )
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f"<b>Dynamic OWL Ontology & Knowledge Graph: :{to_pascal_case(safe_table)}</b>",
                font=dict(size=16, color="#F8FAFC"),
                x=0.05
            ),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=10, r=10, t=50),
            paper_bgcolor="#0F172A",  # Slate 900
            plot_bgcolor="#0F172A",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=440
        )
    )

    return fig
