# 🧠 NL2SQL Intelligence — Full Project Explanation

> **What is this project?**
> A Samsung-grade AI-powered platform that lets any user ask questions in plain English about their structured business data — and get real SQL results back. It ingests any Excel, CSV, or PDF file, understands its meaning semantically, stores it in MySQL, and surfaces it through a conversational query interface backed by Google Gemini, ChromaDB vector search, a Neo4j Knowledge Graph, and a full W3C Semantic Web layer.

---

## Table of Contents

1. [Project Architecture Overview](#1-project-architecture-overview)
2. [Tech Stack](#2-tech-stack)
3. [Data Ingestion Pipeline](#3-data-ingestion-pipeline)
4. [Semantic Features Added During Ingestion](#4-semantic-features-added-during-ingestion)
5. [Knowledge Graph (Neo4j)](#5-knowledge-graph-neo4j)
6. [Query Pipeline (NL to SQL)](#6-query-pipeline-nl-to-sql)
7. [Frontend Components](#7-frontend-components)
8. [ChromaDB — The Semantic Memory Layer](#8-chromadb--the-semantic-memory-layer)
9. [Data Flow Diagram](#9-data-flow-diagram)
10. [Key Design Decisions](#10-key-design-decisions)

---

## 1. Project Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Streamlit)                      │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────────────────┐  │
│  │ NL Query │  │ Data Ingest   │  │  Knowledge Graph Explorer│  │
│  │ UI       │  │ + Semantic UI │  │  (Neo4j Visualizer)      │  │
│  └────┬─────┘  └──────┬────────┘  └──────────┬───────────────┘  │
└───────┼────────────────┼─────────────────────┼─────────────────┘
        │   REST API     │                      │
┌───────▼────────────────▼──────────────────────▼─────────────────┐
│                     BACKEND (FastAPI / Python)                    │
│                                                                   │
│  ┌──────────────────────┐   ┌──────────────────────────────────┐ │
│  │ Intelligent Ingestion│   │      NL2SQL Service              │ │
│  │ Service              │   │  - Schema RAG (ChromaDB)         │ │
│  │ - Gemini AI Analysis │   │  - Few-Shot Retrieval (ChromaDB) │ │
│  │ - ChromaDB Matching  │   │  - Graph Context (Neo4j)         │ │
│  │ - MySQL Upsert       │   │  - Gemini SQL Generation         │ │
│  └──────────┬───────────┘   └──────────────┬───────────────────┘ │
│             │                              │                      │
│  ┌──────────▼───────────┐   ┌─────────────▼──────────────────┐  │
│  │  Entity Extractor    │   │  Graph Service                 │  │
│  │  (Gemini NER)        │   │  (Neo4j Cypher Queries)        │  │
│  └──────────┬───────────┘   └─────────────┬──────────────────┘  │
└─────────────┼─────────────────────────────┼────────────────────┘
              │                             │
   ┌──────────▼────────┐      ┌─────────────▼──────────────────┐
   │   MySQL Database  │      │    ChromaDB (Vector Store)     │
   │   (Structured     │      │  - Schema Embeddings           │
   │    Data Store)    │      │  - Few-Shot Examples           │
   └───────────────────┘      │  - Intro Fingerprints          │
                               └────────────────────────────────┘
                               ┌────────────────────────────────┐
                               │   Neo4j Knowledge Graph        │
                               │  - DatabaseTable nodes         │
                               │  - DatabaseColumn nodes        │
                               │  - Entity nodes                │
                               │  - Document nodes              │
                               └────────────────────────────────┘
```

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **LLM** | Google Gemini 2.5 Flash | Table naming, schema analysis, PDF chunking, entity extraction, SQL generation, summarization |
| **Embeddings** | HuggingFace all-MiniLM-L6-v2 | Sentence-level semantic embeddings for ChromaDB |
| **Vector Store** | ChromaDB | Schema similarity search, few-shot example retrieval, intro fingerprinting |
| **Knowledge Graph** | Neo4j | Persistent graph of tables, columns, entities and their relationships |
| **Relational DB** | MySQL | Actual data storage with full SQL query capability |
| **Backend** | FastAPI (Python) | REST API layer connecting all services |
| **Frontend** | Streamlit | Interactive UI for ingestion, querying, and graph exploration |
| **PDF Parsing** | pdfplumber | Text and table extraction from PDF documents |
| **Data Wrangling** | Pandas, SQLAlchemy | DataFrame manipulation and DB I/O |
| **Semantic Web** | W3C R2RML, RDF, OWL | Knowledge Graph standards compliance |
| **Graph Visualization** | Plotly, NetworkX | Interactive graph rendering in browser |

---

## 3. Data Ingestion Pipeline

### 3.1 Excel / CSV Ingestion Flow

When a user uploads an .xlsx, .xls, or .csv file:

```
Upload File
    │
    ▼
Clean DataFrame (sanitize column names, drop empty rows)
    │
    ▼
Gemini: classify_file_type()
  → Is this a "report", "log", "audit_record", or "other"?
  → Uses first 1000 chars of data as context
    │
    ▼
Gemini: analyze_excel_with_gemini()
  → Extracts: table_name, primary_identifier, column descriptions
  → Prefers domain-appropriate abstract noun column names
    │
    ▼
Gemini: analyze_excel_schema_with_gemini()
  → Maps original Excel headers → clean snake_case column names
  → Ignores unnamed / empty columns
    │
    ▼
Build "Intro Fingerprint" from filename + column names + top 3 rows
    │
    ▼
find_table_by_intro_similarity()  ← ChromaDB cosine similarity
  → Match: append to existing table (upsert mode)
  → No match → _fallback_match_by_name() → name string similarity
  → Still no match → create NEW table in MySQL
    │
    ▼
For each column in new data:
  → If table existed: find_matching_columns() → cosine match to existing columns
  → New columns → ALTER TABLE ADD COLUMN
    │
    ▼
Write data to MySQL (df.to_sql → replace or append)
    │
    ▼
sync_chroma_schema_embeddings()  ← Update ChromaDB with new schema
    │
    ▼
store_table_intro_fingerprint()  ← Store fingerprint for future matching
    │
    ▼
Return: { table_name, rows_added, columns, matches }
```

### 3.2 PDF Ingestion Flow

PDF files are fundamentally different — they are unstructured text, not rows and columns. The pipeline handles this with a **chunked extraction** approach:

```
Upload PDF
    │
    ▼
pdfplumber: extract full text page by page
    │
    ▼
classify_file_type() → "report" / "log" / "audit_record"
    │
    ▼
chunk_text_words() → Split text into 300-word chunks with 50-word overlap
    │
    ▼
For each chunk (i of N):
    Gemini: Extract structured rows + columns from this chunk
    → Prompt includes: file type, known columns from previous chunks,
      preferred semantic column names for the file type
    → Output: { table_name, primary_identifier, parsed_columns, rows }
    → Merge new columns into known_columns list
    │
    ▼
Deduplication:
  → By primary_identifier value (if available)
  → By dict string representation (if no identifier)
    │
    ▼
Fallback: if no rows extracted → try pdfplumber table extraction
    │
    ▼
Convert to DataFrame → sanitize column names → clean data
    │
    ▼
Same matching logic as Excel:
  → find_table_by_intro_similarity() (intro = first page text)
  → Column matching → create or upsert table
    │
    ▼
Return: { table_name, rows_added, columns, matches }
```

**Why chunk with overlap?**
PDFs often have data spanning multiple pages. Overlapping chunks (50 words) ensure that rows that appear on page boundaries are not missed. The deduplication step removes any duplicates this creates.

### 3.3 Semantic Table Matching with ChromaDB

This is one of the most important features. Instead of just checking if a table name exists, the system asks: *"Does incoming data semantically belong to an existing table?"*

**How it works:**

```python
search_text = f"Table: {table_name} {description}"
results = store.similarity_search_with_score(search_text, k=10)

# Convert ChromaDB cosine distance → similarity score
# Distance: 0 = identical, 2 = opposite
# Similarity = 1.0 - (distance / 2.0)
similarity = 1.0 - (distance / 2.0)
```

**Thresholds:**
- TABLE_SIMILARITY_THRESHOLD = 0.5 — if cosine similarity >= 0.5, match to existing table
- COLUMN_SIMILARITY_THRESHOLD = 0.6 — for column-level matching
- INTRO_SIMILARITY_THRESHOLD = 0.6 — for intro fingerprint matching

**Multi-signal matching in find_table_by_subject_or_column_similarity():**
The system takes the MAX of three independent similarity signals:
1. Table title/subject similarity
2. Best individual column similarity
3. Average column similarity

This means a table can be matched even if only its columns are similar (even if the table name differs).

### 3.4 Semantic Column Matching

When appending to an existing table, the system must map incoming columns to existing columns:

```python
# Create embedding of the incoming column name + description
search_embedding = embedding_model.embed_query(f"{column_name} {column_description}")

# For each existing column in the table:
col_embedding = embedding_model.embed_query(f"{col_name} {col_type} {table_name}")

# Manual cosine similarity
similarity = np.dot(search_embedding, col_embedding) / (
    np.linalg.norm(search_embedding) * np.linalg.norm(col_embedding)
)

# Boost for partial name matches
if col_name.lower() == column_name.lower():
    similarity = min(1.0, similarity + 0.15)  # Exact name boost
elif partial_match:
    similarity = min(1.0, similarity + 0.10)  # Partial match boost
```

### 3.5 Intro Fingerprinting

Every ingested file gets a context fingerprint — a compact textual summary of its first few lines/columns — stored in ChromaDB. When a new file arrives, its fingerprint is compared against all stored fingerprints.

**For Excel:** fingerprint = filename + column names + top 3 data rows
**For PDF:** fingerprint = first page text (first 1000 chars)

This solves the problem: **if a user uploads two versions of the same monthly report, the system recognizes they belong to the same table and appends instead of creating a duplicate.**

### 3.6 Name-based Fallback

If cosine similarity fails entirely (ChromaDB is empty or all similarities are below threshold), the system falls back to Python's SequenceMatcher:

```python
def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()
# NAME_MATCH_THRESHOLD = 0.6
```

---

## 4. Semantic Features Added During Ingestion

### 4.1 Column Type Annotation (CTA)

After ingestion, the Semantic Engine analyzes every column and assigns:

| Annotation | Description | Example |
|---|---|---|
| owl_type | OWL ontology property type | owl:DatatypeProperty or owl:ObjectProperty |
| xsd_type | W3C XML Schema Datatype | xsd:string, xsd:integer, xsd:date, xsd:decimal |
| schema_concept | Schema.org alignment | schema:name, schema:identifier, schema:dateTime |
| cpa_role | Column Property Annotation | identifier, measure, dimension, link |
| sanitized_predicate | Clean RDF predicate URI | ex:sales_amount |

### 4.2 Ontology Induction (TBox)

Each ingested table becomes an OWL Class in a dynamically induced ontology.

The UI shows this as an **interactive Plotly graph** where:
- **Violet nodes** = OWL Classes (tables)
- **Cyan nodes** = Datatype Properties (simple columns)
- **Pink nodes** = Object Properties (foreign key links)

### 4.3 ABox Triplification — RDF Triples

Each row in the database becomes a Named Individual in RDF. Available export formats:
- **Turtle (.ttl)** — human-readable RDF
- **JSON-LD** — machine-readable, compatible with web APIs

### 4.4 W3C R2RML Mapping Generation

The system auto-generates a complete R2RML document for every ingested table.
This document is:
- Downloadable as a .ttl file
- Importable into Ontop, D2RQ, Apache Jena for SPARQL querying
- The foundation for the Virtual Knowledge Graph (VKG) / OBDA pattern

### 4.5 Entity Extraction for Knowledge Graph

During and after ingestion, the entity_extractor.py module uses Gemini to extract business entities from the data:

```python
# Gemini prompt extracts entities of types:
# Person, Organization, Product, Technology,
# BusinessConcept, Event, Location, Date
# → Written to Neo4j as Entity nodes with sha256 hashed IDs
```

---

## 5. Knowledge Graph (Neo4j)

### 5.1 Node Types and Relationships

```
Node Labels:
  • Document       → A processed file / data source
  • Entity         → A business entity extracted from the data
  • DatabaseTable  → A MySQL table (schema node)
  • DatabaseColumn → A column within a MySQL table

Relationship Types:
  • CONTAINS      → Document → Entity / DatabaseTable → DatabaseColumn
  • RELATED_TO   → Entity ↔ Entity / Table ↔ Table (semantic or FK)
  • BELONGS_TO   → Entity → Document (back-reference)
  • REFERENCES   → Entity → DatabaseTable (provenance link)
```

### 5.2 Schema Sync to Graph

The "Sync DB Schema → Graph" button triggers sync_schema_to_graph() which:
1. Reads all tables from MySQL using SQLAlchemy inspector
2. Creates DatabaseTable nodes with unique_key = "db.table_name"
3. Creates DatabaseColumn nodes with CONTAINS_COLUMN edges
4. Creates RELATED_TO edges from foreign keys detected in INFORMATION_SCHEMA

### 5.3 Semantic Entity Linking

The semantic_search_entities() function combines:
1. Entity name extraction from the user's NL question (via Gemini NER)
2. Fuzzy Neo4j search — case-insensitive pattern matching
3. Neighbor expansion — fetches 1-hop neighbors of matched entities

---

## 6. Query Pipeline (NL to SQL)

### 6.1 ChromaDB Schema Retrieval (RAG)

```python
schema_store = sync_chroma_schema_embeddings(db_name)
schema_hits = schema_store.similarity_search(question, k=3)
relevant_tables = [doc.metadata["table"] for doc in schema_hits]
```
Only the 3 most semantically relevant tables are sent to Gemini.

### 6.2 Few-Shot Example Retrieval

```python
example_store = build_fewshot_example_store()  # Persistent ChromaDB
fewshot_hits = example_store.similarity_search(question, k=3)
```
Pre-loaded examples cover: sales queries, movie/cast queries, t-shirt inventory, customer segmentation.

### 6.3 Knowledge Graph Context Enrichment

Before generating SQL, the system enriches the prompt with graph hints:
- Extract entity names from the question (Gemini NER)
- Search Neo4j for relevant nodes and their relationships
- Format as context block injected into Gemini prompt

### 6.4 Gemini LLM SQL Generation

The final prompt includes:
- Schema context (top-k relevant tables + columns)
- Optional Knowledge Graph hints (entity nodes + relationships)
- Few-shot SQL examples (top-3 most similar)
- The user's actual question
- Instructions to only use listed tables/columns and return pure MySQL

### 6.5 Follow-up Queries

The followup_ui component prepends the previous SQL query to the new question context, enabling multi-turn conversational querying.

### 6.6 Result Summarization & Visualization

After executing SQL, clicking "Generate Natural Language Summary" sends the SQL + results to Gemini, which returns:
- A plain-English summary of what the data shows
- A Plotly chart specification (JSON) rendered directly in the UI

---

## 7. Frontend Components

| Component | File | Purpose |
|---|---|---|
| App Router | frontend/app.py | Page navigation (Main Dashboard / Ingest Data / Knowledge Graph) |
| Sidebar | components/sidebar.py | Database + table selector, schema refresh, table preview |
| NL Query | components/nl_query.py | Text input → NL2SQL → display SQL code block |
| SQL Editor | components/sql_editor.py | Editable SQL, run query, display results + line chart |
| Follow-up | components/followup.py | Context-aware follow-up question → SQL → results |
| Result Viewer | components/result_viewer.py | Generate Summary → NL summary + Plotly chart |
| Data Ingestion | components/data_ingestion.py | File upload → ingestion → Semantic Web artifacts display |
| Knowledge Graph | components/knowledge_graph.py | Neo4j graph visualization, semantic search, table relationships |

---

## 8. ChromaDB — The Semantic Memory Layer

ChromaDB serves three distinct purposes:

**Purpose 1: Schema Embeddings (Schema RAG)**
- Collection: schema_{db_name} per database
- Documents: "Table: {name}\nColumns: {col1}, {col2}\nTypes: VARCHAR, INTEGER"
- Used for: Finding relevant tables for a user's NL query

**Purpose 2: Few-Shot Example Store**
- Collection: fewshot_examples
- Documents: "Q: {question}\nSQL: {sql_query}"
- Used for: Retrieving similar SQL examples to guide Gemini

**Purpose 3: Intro Fingerprints**
- Collection: schema_{db_name} (same as schema store, type=table_intro)
- Documents: "TABLE_INTRO: {first_lines_of_file}" with table metadata
- Used for: Detecting if an uploaded file is an update vs. a new dataset

---

## 9. Data Flow Diagram

```
USER UPLOADS FILE
       │
       ▼
  [Gemini AI]
  → Classify file type (report/log/audit)
  → Extract table name + column schema
  → For PDFs: chunk → extract rows per chunk
       │
       ▼
  [ChromaDB - Intro Fingerprint Search]
  → Compare file context with stored fingerprints
  → Match found? → Append to existing table
  → No match?   → Create new table
       │
       ├──→ [MySQL] Store structured data
       │
       ├──→ [ChromaDB] Update schema embeddings
       │            + Store intro fingerprint
       │
       └──→ [Entity Extractor - Gemini]
              → Extract entities (Person, Product, Org...)
                     │
                     ▼
              [Neo4j] Write Entity + Document nodes
              [Neo4j] Create CONTAINS / RELATED_TO edges


USER ASKS QUESTION
       │
       ▼
  [ChromaDB Schema RAG]
  → Find top 3 most relevant tables
       │
       ▼
  [ChromaDB Few-Shot RAG]
  → Find top 3 similar SQL examples
       │
       ▼
  [Neo4j - Entity Extraction + Graph Search]
  → Extract entities from question
  → Fetch relevant graph subgraph
       │
       ▼
  [Build Gemini Prompt]
  Schema context + Graph hints + Few-shot examples + User question
       │
       ▼
  [Gemini 2.5 Flash]
  → Generate MySQL query
       │
       ▼
  [MySQL] Execute query → Return rows
       │
       ▼
  [Gemini] Summarize results + generate Plotly chart spec
       │
       ▼
  [Frontend] Display: SQL code, DataFrame, NL summary, Chart
```

---

## 10. Key Design Decisions

**Why ChromaDB for table matching instead of just string matching?**
String matching ("sales_2024" != "sales_report") would fail for semantically identical tables with different names. ChromaDB uses sentence embeddings to understand that "Monthly Sales Data" and "sales_records" are semantically related, enabling intelligent deduplication.

**Why Neo4j in addition to ChromaDB?**
ChromaDB does vector similarity — it finds similar things. Neo4j stores explicit relationships — it knows that sales references customers via a foreign key. Graph traversal lets the NL2SQL engine follow these links during prompt construction.

**Why not just send the full schema to Gemini?**
Large databases may have 50+ tables with hundreds of columns. The ChromaDB Schema RAG selects only the 3 most relevant tables for each question, reducing cost, latency, and hallucination risk.

**Why chunk PDFs with overlap?**
PDF text flows continuously across pages. A data row might start on page 2 and end on page 3. The 50-word overlap ensures no data boundary is missed. Deduplication then handles double-extraction.

**Why is the Semantic Web layer (R2RML, RDF, OWL) included?**
This transforms the system into a W3C-compliant Knowledge Graph platform:
- R2RML enables SPARQL querying of MySQL data via tools like Ontop
- OWL classes make the schema machine-interpretable by semantic reasoners
- RDF triples are the universal format for Linked Data and data exchange
- This is the Ontology-Based Data Access (OBDA) architecture

---

*Generated from the codebase on 2026-10-24. All file paths are relative to the project root QueryBasedReports/*
