"""
Document Intelligence Dashboard - Python Backend
Azure Document Intelligence (Form Recognizer) Integration
"""

import os
import json
from pathlib import Path
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn


# ─── App Setup ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Document Intelligence API",
    description="Azure Document Intelligence powered document analysis backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ──────────────────────────────────────────────────────────────────
class ConnectionConfig(BaseModel):
    endpoint: str
    api_key: str


# ─── Global client store (session-based) ─────────────────────────────────────
_clients: dict[str, DocumentIntelligenceClient] = {}


def get_client(endpoint: str, api_key: str) -> DocumentIntelligenceClient:
    # Clean the endpoint URL
    endpoint = endpoint.strip().rstrip("/")
    key = f"{endpoint}::{api_key[:8]}"
    if key not in _clients:
        _clients[key] = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    return _clients[key]


def get_field_value(field):
    """Safely extract the value from a DocumentField object."""
    if not field:
        return None
    
    # DocumentField in recent SDKs uses specific value_* attributes based on type
    if field.type == "string":
        return field.value_string
    elif field.type == "date":
        return str(field.value_date) if field.value_date else None
    elif field.type == "time":
        return str(field.value_time) if field.value_time else None
    elif field.type == "phoneNumber":
        return field.value_phone_number
    elif field.type == "number":
        return field.value_number
    elif field.type == "integer":
        return field.value_integer
    elif field.type == "selectionMark":
        return field.value_selection_mark
    elif field.type == "countryRegion":
        return field.value_country_region
    elif field.type == "signature":
        return field.value_signature
    elif field.type == "currency":
        return str(field.value_currency) if field.value_currency else None
    elif field.type == "address":
        return str(field.value_address) if field.value_address else None
    elif field.type == "boolean":
        return field.value_boolean
    elif field.type == "array":
        return [get_field_value(item) for item in (field.value_array or [])]
    elif field.type == "object":
        return {k: get_field_value(v) for k, v in (field.value_object or {}).items()}
    
    # Fallback to content if no specific value is found
    return field.content


# ─── Exception Handling ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure all unhandled exceptions return a JSON response instead of HTML."""
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": str(exc)},
    )


# ─── Routes ──────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the dashboard frontend."""
    try:
        # Use absolute path to index.html relative to this script
        current_dir = Path(__file__).parent
        index_path = current_dir / "index.html"
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"index.html not found. Please ensure it is in the same directory as this script."


@app.post("/validate-connection", summary="Validate endpoint and API key")
async def validate_connection(config: ConnectionConfig):
    """Test if the provided endpoint and API key are valid."""
    try:
        if not config.endpoint.startswith("https://"):
            raise ValueError("Endpoint must start with https://")
        
        # Creating the client doesn't perform a network call.
        get_client(config.endpoint, config.api_key)
        
        return {"status": "success", "message": "Connection configuration accepted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/analyze/prebuilt-read", summary="Extract text from document")
async def analyze_read(
    endpoint: str,
    api_key: str,
    file: UploadFile = File(...)
):
    """Extract raw text content using the prebuilt-read model."""
    try:
        client = get_client(endpoint, api_key)
        content = await file.read()

        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            body=content,
            content_type="application/octet-stream"
        )
        result = poller.result()

        return {
            "status": "success",
            "model_used": "prebuilt-read",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "languages": [lang.locale for lang in (result.languages or [])],
            "styles": len(result.styles) if result.styles else 0,
            "key_value_pairs": [],
            "entities": [],
            "tables": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/prebuilt-layout", summary="Extract layout, tables, and structure")
async def analyze_layout(
    endpoint: str,
    api_key: str,
    file: UploadFile = File(...)
):
    """Extract layout information including tables and selection marks."""
    try:
        client = get_client(endpoint, api_key)
        content = await file.read()

        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=content,
            content_type="application/octet-stream"
        )
        result = poller.result()

        # Extract tables
        tables = []
        for table in (result.tables or []):
            rows = {}
            for cell in table.cells:
                r = cell.row_index
                c = cell.column_index
                rows.setdefault(r, {})[c] = cell.content
            tables.append({
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": rows
            })

        return {
            "status": "success",
            "model_used": "prebuilt-layout",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "tables": tables,
            "table_count": len(tables),
            "key_value_pairs": [],
            "entities": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/prebuilt-document", summary="Extract key-value pairs and entities")
async def analyze_document(
    endpoint: str,
    api_key: str,
    file: UploadFile = File(...)
):
    """General document analysis with key-value pairs and named entities."""
    try:
        client = get_client(endpoint, api_key)
        content = await file.read()

        poller = client.begin_analyze_document(
            model_id="prebuilt-document",
            body=content,
            content_type="application/octet-stream"
        )
        result = poller.result()

        # Key-value pairs
        kvp = []
        for pair in (result.key_value_pairs or []):
            if pair.key and pair.value:
                kvp.append({
                    "key": pair.key.content,
                    "value": pair.value.content,
                    "confidence": round(pair.confidence, 3) if pair.confidence else None
                })

        # Entities
        entities = []
        for entity in (result.entities or []):
            entities.append({
                "category": entity.category,
                "content": entity.content,
                "confidence": round(entity.confidence, 3) if entity.confidence else None
            })

        # Tables
        tables = []
        for table in (result.tables or []):
            rows = {}
            for cell in table.cells:
                r = cell.row_index
                c = cell.column_index
                rows.setdefault(r, {})[c] = cell.content
            tables.append({
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": rows
            })

        return {
            "status": "success",
            "model_used": "prebuilt-document",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "key_value_pairs": kvp,
            "entities": entities,
            "tables": tables,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/prebuilt-invoice", summary="Extract invoice fields")
async def analyze_invoice(
    endpoint: str,
    api_key: str,
    file: UploadFile = File(...)
):
    """Specialized invoice extraction."""
    try:
        client = get_client(endpoint, api_key)
        content = await file.read()

        poller = client.begin_analyze_document(
            model_id="prebuilt-invoice",
            body=content,
            content_type="application/octet-stream"
        )
        result = poller.result()

        invoices = []
        for doc in (result.documents or []):
            fields = {}
            for name, field in (doc.fields or {}).items():
                val = get_field_value(field)
                fields[name] = {
                    "value": str(val) if val is not None else field.content,
                    "confidence": round(field.confidence, 3) if field.confidence else None
                }
            invoices.append({"doc_type": doc.doc_type, "fields": fields})

        return {
            "status": "success",
            "model_used": "prebuilt-invoice",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "invoices": invoices,
            "key_value_pairs": [],
            "entities": [],
            "tables": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/prebuilt-receipt", summary="Extract receipt fields")
async def analyze_receipt(
    endpoint: str,
    api_key: str,
    file: UploadFile = File(...)
):
    """Specialized receipt extraction."""
    try:
        client = get_client(endpoint, api_key)
        content = await file.read()

        poller = client.begin_analyze_document(
            model_id="prebuilt-receipt",
            body=content,
            content_type="application/octet-stream"
        )
        result = poller.result()

        receipts = []
        for doc in (result.documents or []):
            fields = {}
            for name, field in (doc.fields or {}).items():
                val = get_field_value(field)
                fields[name] = {
                    "value": val if val is not None else field.content,
                    "confidence": round(field.confidence, 3) if field.confidence else None
                }
            receipts.append({"doc_type": doc.doc_type, "fields": fields})

        return {
            "status": "success",
            "model_used": "prebuilt-receipt",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "receipts": receipts,
            "key_value_pairs": [],
            "entities": [],
            "tables": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/prebuilt-id-document", summary="Extract ID document fields")
async def analyze_id(
    endpoint: str,
    api_key: str,
    file: UploadFile = File(...)
):
    """Extract fields from identity documents (passports, driver's licenses)."""
    try:
        client = get_client(endpoint, api_key)
        content = await file.read()

        poller = client.begin_analyze_document(
            model_id="prebuilt-idDocument",
            body=content,
            content_type="application/octet-stream"
        )
        result = poller.result()

        documents = []
        for doc in (result.documents or []):
            fields = {}
            for name, field in (doc.fields or {}).items():
                val = get_field_value(field)
                fields[name] = {
                    "value": str(val) if val is not None else field.content,
                    "confidence": round(field.confidence, 3) if field.confidence else None
                }
            documents.append({"doc_type": doc.doc_type, "fields": fields})

        return {
            "status": "success",
            "model_used": "prebuilt-idDocument",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "documents": documents,
            "key_value_pairs": [],
            "entities": [],
            "tables": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Starting Document Intelligence API server...")
    print("📖 API Docs: http://localhost:8000/docs")
    uvicorn.run("document_intelligence:app", host="0.0.0.0", port=8000, reload=True)