import os
import uuid
import shutil
import base64
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

from config import (
    UPLOAD_DIR,
    GNANI_API_KEY,
    GNANI_STT_MODEL,
    GNANI_TTS_MODEL,
    NVIDIA_NIM_API_KEY,
    NVIDIA_MODEL,
)
from services.rag_service import rag_service
from services.gnani_service import gnani_service
from services.llm_service import llm_service
from services.sample_generator import ensure_sample_pdf

app = FastAPI(
    title="LexiVoice Legal Portal API",
    description="Voice-Interactive Real Estate & Legal Document Intelligence powered by Gnani Voice AI & LexiVoice Reasoning",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Ensure sample legal document is generated and indexed on boot."""
    sample_pdf = ensure_sample_pdf()
    if "sample_andheri_lease" not in rag_service.documents:
        rag_service.parse_pdf_document(
            file_path=sample_pdf,
            doc_id="sample_andheri_lease",
            title="Andheri West Residential Lease Agreement.pdf"
        )


class TextQueryRequest(BaseModel):
    query: str
    doc_id: Optional[str] = "sample_andheri_lease"
    language_code: Optional[str] = "indic-auto"
    voice: Optional[str] = "Shivani"


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en-IN"
    voice: Optional[str] = "Shivani"
    speed: Optional[float] = 1.0


@app.get("/")
def root():
    return RedirectResponse(url="http://localhost:3000")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "gnani_stt_model": GNANI_STT_MODEL,
        "gnani_tts_model": GNANI_TTS_MODEL,
        "gnani_key_configured": bool(GNANI_API_KEY and not GNANI_API_KEY.startswith("your_")),
        "reasoning_model": NVIDIA_MODEL,
        "nvidia_key_configured": bool(NVIDIA_NIM_API_KEY and not NVIDIA_NIM_API_KEY.startswith("your_")),
        "indexed_documents": len(rag_service.documents)
    }


@app.get("/api/documents")
def list_documents():
    docs = []
    for d_id, doc in rag_service.documents.items():
        docs.append({
            "doc_id": d_id,
            "title": doc["title"],
            "filename": doc["filename"],
            "page_count": doc["page_count"],
            "total_clauses": doc["total_clauses"],
            "high_risk_count": doc["high_risk_count"],
            "medium_risk_count": doc["medium_risk_count"],
            "safe_count": doc["safe_count"],
            "overall_risk_score": doc["overall_risk_score"]
        })
    return {"documents": docs}


@app.get("/api/documents/{doc_id}")
def get_document_details(doc_id: str):
    doc = rag_service.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.get("/api/documents/{doc_id}/pdf")
def get_document_pdf(doc_id: str):
    doc = rag_service.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = UPLOAD_DIR / doc["filename"]
    if not file_path.exists():
        # Check in DATA_DIR
        file_path = ensure_sample_pdf()
        
    return FileResponse(
        path=str(file_path),
        filename=doc["filename"],
        media_type="application/pdf"
    )


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported")

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    dest_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc_info = rag_service.parse_pdf_document(
        file_path=dest_path,
        doc_id=doc_id,
        title=file.filename
    )

    return {
        "message": "Document parsed and indexed successfully",
        "document": {
            "doc_id": doc_info["doc_id"],
            "title": doc_info["title"],
            "total_clauses": doc_info["total_clauses"],
            "high_risk_count": doc_info["high_risk_count"],
            "overall_risk_score": doc_info["overall_risk_score"]
        }
    }


@app.post("/api/query/voice")
async def query_by_voice(
    audio_file: UploadFile = File(...),
    doc_id: Optional[str] = Form("sample_andheri_lease"),
    language_code: Optional[str] = Form("indic-auto"),
    voice: Optional[str] = Form("Shivani")
):
    """
    End-to-end voice pipeline:
    1. Audio -> Gnani Prisma v3.0 STT -> Transcribed text
    2. RAG Retrieval -> BAAI/bge-small-en-v1.5 + Qdrant -> Relevant clauses
    3. LLM Reasoning -> NVIDIA NIM / Nemotron / Evon -> Executive bullets & Citations
    4. Text -> Gnani Timbre v2.5/v3.0 TTS -> Spoken audio response
    """
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file uploaded")

    # Step 1: STT with Gnani Prisma v3.0
    stt_res = await gnani_service.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio_file.filename or "recording.wav",
        language_code=language_code
    )
    user_query = stt_res.get("transcript", "").strip()
    detected_lang = stt_res.get("detected_language", language_code)

    if not user_query:
        user_query = "What happens if I terminate the lease early?"

    # Step 2: Translate query to English if non-English for RAG retrieval against English contract
    from services.llm_service import translate_text, detect_query_language
    search_query = user_query
    if any(ord(c) > 127 for c in user_query):
        search_query = await translate_text(user_query, target_lang="en", source_lang="auto")
        logger.info(f"Translated query for English RAG: '{user_query}' -> '{search_query}'")

    retrieved_clauses = rag_service.search_relevant_clauses(
        query=search_query,
        doc_id=doc_id,
        top_k=4
    )

    # Step 3: LexiVoice Multilingual Reasoning
    if language_code and "auto" not in language_code.lower():
        target_lang = language_code
    elif detected_lang and "auto" not in detected_lang.lower():
        target_lang = detected_lang
    else:
        target_lang = detect_query_language(user_query) or "en-IN"

    llm_res = await llm_service.analyze_legal_query(
        query=user_query,
        retrieved_clauses=retrieved_clauses,
        language=target_lang
    )

    # Step 4: TTS with Gnani Timbre in selected language
    spoken_text = llm_res.get("spoken_summary", "Here is the summary of your contract clause.")
    tts_res = await gnani_service.synthesize_speech(
        text=spoken_text,
        language=target_lang,
        voice=voice
    )

    return {
        "user_query": user_query,
        "detected_language": detected_lang,
        "confidence": stt_res.get("confidence", 0.95),
        "stt_fallback": stt_res.get("is_fallback", False),
        "executive_bullet_points": llm_res.get("executive_bullet_points", []),
        "cited_clauses": llm_res.get("cited_clauses", []),
        "actionable_advice": llm_res.get("actionable_advice", ""),
        "spoken_summary": spoken_text,
        "audio_base64": tts_res.get("audio_base64"),
        "audio_format": tts_res.get("audio_format", "audio/wav"),
        "tts_voice": tts_res.get("voice", voice),
        "tts_fallback": tts_res.get("is_fallback", False)
    }


@app.post("/api/query/text")
async def query_by_text(req: TextQueryRequest):
    """Text-based query workflow with RAG + Reasoning + Timbre TTS."""
    user_query = req.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Translate query to English if non-English for RAG retrieval against English contract
    from services.llm_service import translate_text, detect_query_language
    search_query = user_query
    if any(ord(c) > 127 for c in user_query):
        search_query = await translate_text(user_query, target_lang="en", source_lang="auto")
        logger.info(f"Translated query for English RAG: '{user_query}' -> '{search_query}'")

    retrieved_clauses = rag_service.search_relevant_clauses(
        query=search_query,
        doc_id=req.doc_id,
        top_k=4
    )

    # Determine target language matching user selection
    target_lang = req.language_code
    if not target_lang or "auto" in target_lang.lower():
        target_lang = detect_query_language(user_query) or "en-IN"

    llm_res = await llm_service.analyze_legal_query(
        query=user_query,
        retrieved_clauses=retrieved_clauses,
        language=target_lang
    )

    spoken_text = llm_res.get("spoken_summary", "Clause analysis complete.")
    tts_res = await gnani_service.synthesize_speech(
        text=spoken_text,
        language=target_lang,
        voice=req.voice
    )

    return {
        "user_query": user_query,
        "detected_language": target_lang,
        "executive_bullet_points": llm_res.get("executive_bullet_points", []),
        "cited_clauses": llm_res.get("cited_clauses", []),
        "actionable_advice": llm_res.get("actionable_advice", ""),
        "spoken_summary": spoken_text,
        "audio_base64": tts_res.get("audio_base64"),
        "audio_format": tts_res.get("audio_format", "audio/wav"),
        "tts_voice": tts_res.get("voice", req.voice),
        "tts_fallback": tts_res.get("is_fallback", False)
    }


@app.post("/api/tts")
async def direct_tts(req: TTSRequest):
    """Direct Text-to-Speech synthesis using Gnani Timbre."""
    tts_res = await gnani_service.synthesize_speech(
        text=req.text,
        language=req.language,
        voice=req.voice,
        speed=req.speed or 1.0
    )
    return tts_res
