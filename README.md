# Context-Aware SQL Analytics — Intelligent Ingestion, Hybrid Retrieval & Semantic Knowledge Graph

*Transform unstructured and tabular enterprise data into intelligent, queryable insights with Natural Language to SQL, Vector Search, and Knowledge Graphs.*

---

## 📺 Complete Project Demo
![Project Demo](https://github.ecodesamsung.com/SRIB-PRISM/QueryBasedReports/assets/38880/4db00dd3-6754-4ba0-99c6-798ecf3d0e3a)

Watch the walkthrough on YouTube: **[Demo & Explanation Video](https://youtu.be/5Ied6-Ck5FE)**

---

## 🌟 What This System Does

Ask your databases and spreadsheets complex business questions in plain English and receive accurate, executable SQL, tabular answers, and executive summaries.

1. **Intelligent Ingestion** — Drop in Excel (`.xlsx`, `.xls`), CSV, or PDF documents. The system analyzes schemas, deduplicates entities, creates or appends SQL tables dynamically, and indexes schema metadata.
2. **Semantic Knowledge Graph Layer (Neo4j)** — Automatically extracts business entities, cross-table relationships, and document provenance into a graph database with W3C RDF/OWL semantic standards.
3. **Hybrid Retrieval (ChromaDB + Neo4j)** — Combines dense vector similarity search (ChromaDB embeddings) with structured graph traversal (Neo4j) to select the right tables and columns for ambiguous prompts.
4. **Context-Aware NL2SQL Generation** — Formulates high-precision MySQL queries using Google Gemini with dynamic few-shot examples and graph hints.
5. **Interactive Streamlit Explorer** — Features an interactive graph visualizer, SQL workbench, and AI-driven narrative summarizer.

---

## 🏗️ System Architecture & Workflow

```
                                      ┌─────────────────────────────────┐
                                      │   User Query / Raw Documents    │
                                      └────────────────┬────────────────┘
                                                       │
                     ┌─────────────────────────────────┴─────────────────────────────────┐
                     ▼                                                                   ▼
       [Intelligent File Ingestion]                                        [Natural Language Query]
                     │                                                                   │
          ┌──────────┴──────────┐                                                        ▼
          ▼                     ▼                                           Extract Question Entities
   MySQL Database       Entity Extraction                                                │
   (Structured Tables)   & Relationship Mapping                                          │
          ▲                     │                                                        ▼
          │                     ▼                                              [Hybrid Retrieval]
          │             Neo4j Knowledge Graph                             ┌──────────────┴──────────────┐
          │             - Nodes: Document, Entity,                        ▼                             ▼
          │               DatabaseTable, DatabaseColumn              ChromaDB (Vectors)       Neo4j (Knowledge Graph)
          │             - Edges: CONTAINS, RELATED_TO,              [Schema Embeddings]       [Entity & Rel Hints]
          │               REFERENCES, CONTAINS_COLUMN                     └──────────────┬──────────────┘
          │                                                                              │
          │                                                                              ▼
          │                                                                  Assemble Prompt Context
          │                                                                              │
          │                                                                              ▼
          │                                                                   Google Gemini (LLM)
          │                                                                              │
          │                                                                              ▼
          │                                                                   Generate Precision SQL
          │                                                                              │
          └─────────────────────────────────────────────────────────────────────── Execute Query
                                                                                         │
                                                                                         ▼
                                                                             Interactive Results & Summary
```

---

## 📁 Project Structure

```
QueryBasedReports/
│
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   └── query.py                    # Pydantic models for queries & requests
│   │   ├── routes/
│   │   │   ├── db_meta.py                  # Database metadata & SHOW TABLES endpoints
│   │   │   ├── debug_chroma.py             # ChromaDB vector store diagnostics
│   │   │   ├── execute_query.py            # SQL query execution engine
│   │   │   ├── graph.py                    # Knowledge Graph API endpoints
│   │   │   ├── intelligent_ingest.py       # Smart Excel/CSV/PDF ingestion endpoint
│   │   │   ├── nl2sql.py                   # Natural Language to SQL generation
│   │   │   ├── refresh_schema.py           # Schema cache & vector embedding refresh
│   │   │   ├── summarize.py                # AI-driven query result summarization
│   │   │   └── upload_excel.py             # File upload handling
│   │   ├── services/
│   │   │   ├── intelligent_ingestion_service.py # Ingestion & Graph extraction hooks
│   │   │   ├── nl2sql_service.py           # Hybrid vector+graph NL2SQL engine
│   │   │   ├── summarize_service.py        # Executive summary generator
│   │   │   └── upload_service.py           # Excel parser service
│   │   ├── utils/
│   │   │   ├── chroma_utils.py             # ChromaDB schema vector embeddings
│   │   │   ├── db_utils.py                 # SQLAlchemy schema inspector & cache
│   │   │   ├── db.py                       # MySQL database connection pool
│   │   │   ├── entity_extractor.py         # Business entity & relationship extractor
│   │   │   ├── fewshot_utils.py            # Dynamic few-shot prompt manager
│   │   │   ├── graph_service.py            # Neo4j Knowledge Graph service
│   │   │   └── main.py                     # Utility helpers
│   │   └── main.py                         # FastAPI application entry point
│   └── requirements.txt
│
├── frontend/
│   ├── components/
│   │   ├── data_ingestion.py               # Ingestion UI with W3C RDF/OWL visualizer
│   │   ├── file_upload.py                  # File upload widget
│   │   ├── followup.py                     # Conversational follow-up query UI
│   │   ├── knowledge_graph.py              # Interactive Plotly Knowledge Graph Explorer
│   │   ├── nl_query.py                     # Natural language query input component
│   │   ├── result_viewer.py                # SQL result table & AI summary viewer
│   │   ├── sidebar.py                      # Database & table selector sidebar
│   │   └── sql_editor.py                   # Interactive SQL code editor & runner
│   │
│   ├── utils/
│   │   ├── api.py                          # Frontend HTTP client (including Graph API)
│   │   ├── app.py                          # Streamlit application helpers
│   │   └── semantic_engine.py              # W3C OWL/RDF & R2RML semantic engine
│   │
│   └── app.py                              # Main Streamlit dashboard
│
├── Testing Dataset/                        # Sample data for tests (Chrome, Teams, WhatsApp)
├── docker-compose.yml                      # Containerized orchestration
├── .env.example                            # Template environment variables
├── requirements.txt                        # Master Python dependencies
└── README.md                               # Project documentation
```

---

## ⚙️ Installation & Setup Guide

### 1. Prerequisites
- **Python 3.10+**
- **MySQL Server** (local or remote)
- **Docker Desktop** (optional, recommended for Neo4j)
- **Google Gemini API Key** ([Get free key here](https://aistudio.google.com/))

---

### 2. Configure Environment (`.env`)
Copy `.env.example` to create your `.env` in the project root:

```ini
# MySQL Database Credentials
DB_USER="root"
DB_PASS="your_mysql_password"
DB_HOST="localhost"
DB_PORT="3306"
DB_NAME="file2sql"

# Google Gemini API
GOOGLE_API_KEY="AIzaSy..."

# Neo4j Graph Database (Semantic Knowledge Graph)
# Optional: If omitted, the app degrades gracefully with full NL2SQL functionality
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password123"
```

---

### 3. Start Neo4j Graph Database (Docker)
Run Neo4j with a single command:

```bash
docker run -d --name neo4j-kg -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:latest
```
- **Neo4j Browser UI**: [http://localhost:7474](http://localhost:7474) (Username: `neo4j`, Password: `password123`)
- **Bolt Port**: `7687`

> **Note on Graceful Degradation:** If Neo4j is offline or unconfigured, the application runs normally in fallback mode. Graph queries are skipped without causing crashes.

---

### 4. Install Python Dependencies
Set up and activate a virtual environment:

```powershell
# Create venv
python -m venv venv

# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate venv (macOS/Linux)
# source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

### 5. Start the Application

#### Start Backend (Terminal 1)
```powershell
.\venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/api/graph/status](http://127.0.0.1:8000/api/graph/status)

#### Start Frontend (Terminal 2)
```powershell
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```
- Web Application: [http://localhost:8501](http://localhost:8501)

---

## 🧪 Step-by-Step Testing Guide

Follow these steps to test every capability of the application:

### Step 1: Verify Knowledge Graph Status
1. Open [http://localhost:8501](http://localhost:8501) in your browser.
2. In the left sidebar radio button, click **Knowledge Graph**.
3. Confirm the status header displays:
   > 🟢 **Knowledge Graph Engine Active: Neo4j connected ✅**

---

### Step 2: Synchronize Database Schema into Graph Nodes
1. In the **Knowledge Graph** page, select your database (e.g. `file2sql`) from the dropdown.
2. Click **"🔄 Sync DB Schema to Graph"**.
3. In the **Graph Visualization** tab:
   - Tables (`DatabaseTable` nodes in Cyan) and columns (`DatabaseColumn` nodes in Slate) will be displayed.
   - Use the **Filter by Node Type** dropdown or drag nodes around the force-directed canvas.
   - Inspect attributes of any node in the **Node Details & Attribute Inspector**.
4. Check the **Table Relationships & Schema Graph** tab to review detected foreign keys.

---

### Step 3: Ingest a Dataset (Excel, CSV, or PDF)
1. In the sidebar radio, switch to **Ingest Data**.
2. Select your target database and upload a file from `Testing Dataset/` or your own spreadsheets.
3. Click **"Ingest File"**.
4. **What happens under the hood:**
   - Table schema is created or merged into MySQL.
   - Embeddings are indexed in ChromaDB.
   - A `Document` node is created in Neo4j.
   - Business entities (e.g., categories, departments, vendors) and row relationships are extracted and linked to the document and tables.
   - W3C RDF Triples and OWL Ontologies are generated in the UI.

---

### Step 4: Test Hybrid Retrieval with Natural Language Queries
1. In the sidebar radio, click **Main Dashboard**.
2. Select your database from the sidebar.
3. In the query box, enter a natural language question, for example:
   ```text
   "Show total sales by customer name in 2024 order by highest amount"
   ```
4. Click **"Generate SQL"**.
5. Observe the execution flow:
   - **Entity Extraction**: Keywords (`sales`, `customer name`, `2024`) are extracted.
   - **Graph Traversal**: Related table and column nodes are pulled from Neo4j.
   - **ChromaDB**: Top matching schema vectors are retrieved.
   - **Prompt Fusion**: Both context hints are sent to Gemini.
   - **SQL Execution**: The query executes against MySQL, displaying the interactive table and AI-generated summary.

---

### Step 5: Test Semantic Question Subgraph Extraction
1. Return to the **Knowledge Graph** tab and switch to the **"🔍 Semantic Search & Question Answering"** tab.
2. Enter any hypothetical query:
   ```text
   "Which vendors deliver high-priority orders to California?"
   ```
3. Click **"🚀 Analyze Entities & Retrieve Subgraph"**.
4. The system will visualize the exact subgraph (nodes and edges) retrieved and show the YAML context injected into the NL2SQL engine.

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/` | List available MySQL databases |
| `GET` | `/api/{db_name}` | List tables in database |
| `POST` | `/api/ingest/` | Intelligent Excel/CSV/PDF file ingestion |
| `POST` | `/api/nl2sql/` | Generate SQL from natural language (with Graph context) |
| `POST` | `/api/execute/` | Execute SQL query on database |
| `POST` | `/api/summarize/` | Generate natural language summary of query results |
| `POST` | `/api/refresh/` | Refresh schema cache, ChromaDB embeddings, and Neo4j graph |
| `GET` | `/api/graph/status` | Neo4j connectivity status |
| `GET` | `/api/graph/` | Sampled graph nodes and edges for visualization |
| `GET` | `/api/graph/entities/{id}/neighbors` | Multi-hop entity neighborhood traversal |
| `GET` | `/api/graph/search` | Search entities by substring |
| `POST` | `/api/graph/semantic-search` | Entity extraction and subgraph retrieval from natural text |
| `GET` | `/api/graph/tables/{db_name}/relationships` | Table foreign-key relationships |
| `POST` | `/api/graph/sync-schema/{db_name}` | Manual relational schema-to-graph synchronization |

---

## 🛠️ Troubleshooting FAQ

| Problem | Cause | Solution |
|---------|-------|----------|
| **"Graph Service Offline or Not Configured"** | Neo4j container not running or `.env` missing credentials | Run `docker start neo4j-kg` and ensure `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` are set in `.env`. |
| **"Cannot connect to backend"** in frontend | FastAPI server is not running | Start backend with `cd backend; uvicorn main:app --reload`. |
| **MySQL Access Denied (1045)** | Incorrect database credentials | Check `DB_USER` and `DB_PASS` in `.env`. |
| **"No few-shot examples available"** | ChromaDB collections not initialized | Ingest a file or click "Refresh Schema" in the sidebar. |
| **Gemini API Rate Limit / Error** | Missing or exhausted Gemini key | Verify `GOOGLE_API_KEY` in `.env` is valid and active. |

---

*Built with FastAPI, Streamlit, Neo4j, ChromaDB, and Google Gemini.*
