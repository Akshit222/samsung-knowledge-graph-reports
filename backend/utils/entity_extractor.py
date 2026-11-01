"""
Entity Extractor — uses Gemini to extract structured entities and relationships
from tabular data (DataFrame rows) and raw text (PDF content).

Output is validated before being written to the graph — no raw LLM output
is executed as code or Cypher.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI

# ─── LLM singleton (reuse existing GOOGLE_API_KEY) ────────────────────────────
_llm: Optional[ChatGoogleGenerativeAI] = None


def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return _llm


# ─── Allowed entity types (whitelist) ─────────────────────────────────────────
ALLOWED_ENTITY_TYPES = {
    "Person", "Organization", "Product", "Technology",
    "BusinessConcept", "Event", "Location", "Date",
    "DatabaseTable", "DatabaseColumn", "Other",
}

ALLOWED_REL_TYPES = {"RELATED_TO", "BELONGS_TO", "REFERENCES", "PART_OF"}


# ─── ID generation ────────────────────────────────────────────────────────────

def _make_id(namespace: str, *parts: str) -> str:
    raw = f"{namespace}::" + "::".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── Schema / text extraction ─────────────────────────────────────────────────

def extract_from_dataframe(
    df: pd.DataFrame,
    table_name: str,
    db_name: str,
    doc_id: str,
    max_rows: int = 20,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract entities and relationships from a DataFrame sample.

    Returns:
        entities    — list of {id, name, type, source_doc, source_row, properties}
        relations   — list of {from_id, to_id, rel_type, evidence, confidence}
    """
    try:
        sample = df.head(max_rows)
        col_names = list(sample.columns)
        rows_preview = sample.to_dict(orient="records")
        rows_text = json.dumps(rows_preview, default=str)[:3000]

        prompt = f"""You are a knowledge extraction system. Analyse this database table data.

Table name: {table_name}
Database: {db_name}
Columns: {col_names}
Sample rows (JSON):
{rows_text}

Extract:
1. Named entities (people, organisations, products, technologies, business concepts, locations, events).
2. Meaningful relationships BETWEEN those entities.

Return a single valid JSON object with this exact structure:
{{
  "entities": [
    {{"name": "...", "type": "Person|Organization|Product|Technology|BusinessConcept|Event|Location|Other", "evidence": "which column/value"}}
  ],
  "relationships": [
    {{"from": "entity_name", "to": "entity_name", "type": "RELATED_TO|BELONGS_TO|REFERENCES|PART_OF", "evidence": "brief reason"}}
  ]
}}

Rules:
- Only include entities clearly visible in the data.
- Only include relationships supported by the data.
- Do NOT invent entities or relationships.
- Keep entity names concise (< 60 chars).
- Return ONLY the JSON, no markdown, no commentary.
"""
        llm = _get_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        parsed = json.loads(content)
        raw_entities = parsed.get("entities", [])
        raw_rels = parsed.get("relationships", [])

    except Exception as exc:
        print(f"[EntityExtractor] LLM extraction failed for {table_name}: {exc}")
        # Graceful fallback: derive simple entities from column names
        raw_entities = [
            {"name": col, "type": "BusinessConcept", "evidence": "column name"}
            for col in df.columns[:10]
        ]
        raw_rels = []

    entities: List[Dict] = []
    name_to_id: Dict[str, str] = {}

    for raw in raw_entities:
        name = str(raw.get("name", "")).strip()
        etype = str(raw.get("type", "Other")).strip()
        if not name:
            continue
        # Validate type
        if etype not in ALLOWED_ENTITY_TYPES:
            etype = "Other"

        eid = _make_id(db_name, table_name, name)
        name_to_id[name] = eid
        entities.append({
            "id":         eid,
            "name":       name,
            "type":       etype,
            "source_doc": doc_id,
            "source_row": None,
            "properties": {"evidence": raw.get("evidence", ""), "source_db": db_name},
        })

    relations: List[Dict] = []
    for raw in raw_rels:
        from_name = str(raw.get("from", "")).strip()
        to_name   = str(raw.get("to", "")).strip()
        rel_type  = str(raw.get("type", "RELATED_TO")).strip()
        evidence  = str(raw.get("evidence", "")).strip()

        if rel_type not in ALLOWED_REL_TYPES:
            rel_type = "RELATED_TO"

        from_id = name_to_id.get(from_name)
        to_id   = name_to_id.get(to_name)
        if not from_id or not to_id or from_id == to_id:
            continue

        relations.append({
            "from_id":    from_id,
            "to_id":      to_id,
            "rel_type":   rel_type,
            "evidence":   evidence,
            "confidence": 0.85,
        })

    print(
        f"[EntityExtractor] {table_name}: {len(entities)} entities, "
        f"{len(relations)} relationships extracted."
    )
    return entities, relations


def extract_from_text(
    text: str,
    doc_name: str,
    doc_id: str,
    db_name: str = "",
    max_chars: int = 4000,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract entities and relationships from free text (e.g. PDF content).
    Same output format as extract_from_dataframe.
    """
    truncated = text[:max_chars]
    try:
        prompt = f"""You are a knowledge extraction system. Analyse the following text.

Document: {doc_name}
Text:
{truncated}

Extract:
1. Named entities (people, organisations, products, technologies, business concepts, locations, events).
2. Meaningful relationships BETWEEN those entities.

Return a single valid JSON object:
{{
  "entities": [
    {{"name": "...", "type": "Person|Organization|Product|Technology|BusinessConcept|Event|Location|Other", "evidence": "quote or context"}}
  ],
  "relationships": [
    {{"from": "entity_name", "to": "entity_name", "type": "RELATED_TO|BELONGS_TO|REFERENCES|PART_OF", "evidence": "brief reason"}}
  ]
}}

Rules:
- Only extract entities clearly present in the text.
- Return ONLY the JSON, no markdown or commentary.
"""
        llm = _get_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content)
        raw_entities = parsed.get("entities", [])
        raw_rels = parsed.get("relationships", [])

    except Exception as exc:
        print(f"[EntityExtractor] Text extraction failed for {doc_name}: {exc}")
        return [], []

    entities: List[Dict] = []
    name_to_id: Dict[str, str] = {}

    for raw in raw_entities:
        name  = str(raw.get("name", "")).strip()
        etype = str(raw.get("type", "Other")).strip()
        if not name:
            continue
        if etype not in ALLOWED_ENTITY_TYPES:
            etype = "Other"
        eid = _make_id(db_name or "doc", doc_name, name)
        name_to_id[name] = eid
        entities.append({
            "id": eid, "name": name, "type": etype,
            "source_doc": doc_id, "source_row": None,
            "properties": {"evidence": raw.get("evidence", ""), "doc_name": doc_name},
        })

    relations: List[Dict] = []
    for raw in raw_rels:
        from_name = str(raw.get("from", "")).strip()
        to_name   = str(raw.get("to", "")).strip()
        rel_type  = str(raw.get("type", "RELATED_TO")).strip()
        if rel_type not in ALLOWED_REL_TYPES:
            rel_type = "RELATED_TO"
        from_id = name_to_id.get(from_name)
        to_id   = name_to_id.get(to_name)
        if not from_id or not to_id or from_id == to_id:
            continue
        relations.append({
            "from_id":    from_id,
            "to_id":      to_id,
            "rel_type":   rel_type,
            "evidence":   str(raw.get("evidence", "")),
            "confidence": 0.8,
        })

    return entities, relations


def extract_question_entities(question: str) -> List[str]:
    """
    Lightweight extraction: pull potential entity / concept names from a NL question.
    Returns a list of candidate strings for graph lookup.
    Used to inject graph context into the NL→SQL pipeline.
    """
    try:
        prompt = f"""Extract named entities and key concepts from this question.

Question: {question}

Return a JSON array of entity/concept name strings only.
Example: ["Samsung Galaxy", "Revenue", "Q3 2023"]
Return ONLY the JSON array, no other text.
"""
        llm = _get_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        result = json.loads(content)
        if isinstance(result, list):
            return [str(x).strip() for x in result if x]
    except Exception as exc:
        print(f"[EntityExtractor] Question entity extraction failed: {exc}")
    return []
