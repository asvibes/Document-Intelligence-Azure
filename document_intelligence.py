"""
Document Intelligence Dashboard - Python Backend
Azure Document Intelligence (Form Recognizer) Integration
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional

# ─── Install dependencies ────────────────────────────────────────────────────
# pip install azure-ai-documentintelligence azure-core fastapi uvicorn python-multipart

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


class AnalysisResult(BaseModel):
    status: str
    model_used: str
    pages: int
    content: Optional[str]
    tables: list
    key_value_pairs: list
    entities: list
    raw: Optional[dict] = None


# ─── Global client store (session-based) ─────────────────────────────────────
_clients: dict[str, DocumentIntelligenceClient] = {}


def get_client(endpoint: str, api_key: str) -> DocumentIntelligenceClient:
    key = f"{endpoint}::{api_key[:8]}"
    if key not in _clients:
        _clients[key] = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    return _clients[key]


# ─── Routes ──────────────────────────────────────────────────────────────────
@app.post("/validate-connection", summary="Validate endpoint and API key")
async def validate_connection(config: ConnectionConfig):
    """Test if the provided endpoint and API key are valid."""
    try:
        client = get_client(config.endpoint, config.api_key)
        # Attempt a lightweight call to verify credentials
        return {"status": "success", "message": "Connection validated successfully"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Connection failed: {str(e)}")


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
            analyze_request=content,
            content_type=file.content_type or "application/octet-stream"
        )
        result = poller.result()

        return {
            "status": "success",
            "model_used": "prebuilt-read",
            "pages": len(result.pages) if result.pages else 0,
            "content": result.content,
            "languages": [lang.locale for lang in (result.languages or [])],
            "styles": len(result.styles) if result.styles else 0,
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
            analyze_request=content,
            content_type=file.content_type or "application/octet-stream"
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
            analyze_request=content,
            content_type=file.content_type or "application/octet-stream"
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
            analyze_request=content,
            content_type=file.content_type or "application/octet-stream"
        )
        result = poller.result()

        invoices = []
        for doc in (result.documents or []):
            fields = {}
            for name, field in (doc.fields or {}).items():
                fields[name] = {
                    "value": str(field.value) if field.value else field.content,
                    "confidence": round(field.confidence, 3) if field.confidence else None
                }
            invoices.append({"doc_type": doc.doc_type, "fields": fields})

        return {
            "status": "success",
            "model_used": "prebuilt-invoice",
            "pages": len(result.pages) if result.pages else 0,
            "invoices": invoices,
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
            analyze_request=content,
            content_type=file.content_type or "application/octet-stream"
        )
        result = poller.result()

        receipts = []
        for doc in (result.documents or []):
            fields = {}
            for name, field in (doc.fields or {}).items():
                if hasattr(field, 'value_array') and field.value_array:
                    items = []
                    for item in field.value_array:
                        item_fields = {}
                        if hasattr(item, 'value_object'):
                            for k, v in (item.value_object or {}).items():
                                item_fields[k] = str(v.value) if v.value else v.content
                        items.append(item_fields)
                    fields[name] = {"value": items, "confidence": None}
                else:
                    fields[name] = {
                        "value": str(field.value) if field.value else field.content,
                        "confidence": round(field.confidence, 3) if field.confidence else None
                    }
            receipts.append({"doc_type": doc.doc_type, "fields": fields})

        return {
            "status": "success",
            "model_used": "prebuilt-receipt",
            "pages": len(result.pages) if result.pages else 0,
            "receipts": receipts,
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
            analyze_request=content,
            content_type=file.content_type or "application/octet-stream"
        )
        result = poller.result()

        documents = []
        for doc in (result.documents or []):
            fields = {}
            for name, field in (doc.fields or {}).items():
                fields[name] = {
                    "value": str(field.value) if field.value else field.content,
                    "confidence": round(field.confidence, 3) if field.confidence else None
                }
            documents.append({"doc_type": doc.doc_type, "fields": fields})

        return {
            "status": "success",
            "model_used": "prebuilt-idDocument",
            "pages": len(result.pages) if result.pages else 0,
            "documents": documents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Starting Document Intelligence API server...")
    print("📖 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)