import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from config import DATA_DIR, UPLOAD_DIR, QDRANT_DIR

logger = logging.getLogger("rag_service")
logging.basicConfig(level=logging.INFO)

# Risk classification heuristics for Indian lease/real-estate agreements
RISK_RULES = [
    {
        "keywords": ["penalty", "lock-in", "early exit", "early termination", "forfeit"],
        "condition": lambda text: any(p in text.lower() for p in ["6 months", "forfeited in full", "no refund", "irrespective"]),
        "level": "High Risk",
        "badge": "HIGH RISK",
        "advice": "High penalty detected. In Indian metropolitan tenancy, 1 to 2 months notice or rent penalty is customary. This clause is heavily biased towards the lessor and should be negotiated down."
    },
    {
        "keywords": ["security deposit", "refund", "interest-free"],
        "condition": lambda text: any(p in text.lower() for p in ["90 days", "6 months rent", "10 months rent", "deduct unconditionally"]),
        "level": "Medium Risk",
        "badge": "MEDIUM",
        "advice": "Security deposit holding period or amount is on the higher side. Refund period of 90 days is excessively long (standard practice is 30–45 days after key handover)."
    },
    {
        "keywords": ["maintenance", "society", "electricity", "water"],
        "condition": lambda text: "direct" in text.lower() or "actual" in text.lower(),
        "level": "Safe",
        "badge": "SAFE",
        "advice": "Clear obligation with direct payment to society or utility provider based on actuals. Standard tenancy term."
    },
    {
        "keywords": ["escalation", "increase"],
        "condition": lambda text: any(p in text.lower() for p in ["10%", "15%", "annual increase"]),
        "level": "Medium Risk",
        "badge": "MEDIUM",
        "advice": "Standard escalation in Mumbai/Bangalore residential leases is 5%–7% annually. A 10% increase compounded annually adds substantial long-term cost."
    }
]


class RAGService:
    def __init__(self):
        self.embedding_model_name = "BAAI/bge-small-en-v1.5"
        self._embedder: Optional[TextEmbedding] = None
        
        # Initialize local Qdrant client (in-memory for speed & zero external dependency)
        self.qdrant = QdrantClient(":memory:")
        self.collection_name = "legal_clauses"
        self._collection_initialized = False
        
        # In-memory document registry
        self.documents: Dict[str, Dict[str, Any]] = {}
        
        # Initialize
        self._ensure_collection()
        self._init_embedder()

    def _init_embedder(self):
        try:
            logger.info(f"Initializing FastEmbed model {self.embedding_model_name}...")
            self._embedder = TextEmbedding(model_name=self.embedding_model_name)
            logger.info("FastEmbed model initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not load FastEmbed ({e}). Falling back to simple lexical search.")
            self._embedder = None

    def _ensure_collection(self):
        if not self._collection_initialized:
            try:
                self.qdrant.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                self._collection_initialized = True
            except Exception as e:
                logger.error(f"Error initializing Qdrant collection: {e}")

    def compute_embedding(self, text: str) -> List[float]:
        if self._embedder:
            try:
                embeddings = list(self._embedder.embed([text]))
                return embeddings[0].tolist()
            except Exception as e:
                logger.error(f"Embedder error: {e}")
        # Deterministic 384-dim pseudo-vector fallback
        vec = [0.0] * 384
        for i, char in enumerate(text[:384]):
            vec[i] = (ord(char) % 100) / 100.0
        return vec

    def parse_pdf_document(self, file_path: Path, doc_id: str, title: str) -> Dict[str, Any]:
        """
        Extract text page-by-page using PyMuPDF (fitz), extract clauses, compute risk scores.
        """
        doc = fitz.open(file_path)
        pages_content = []
        raw_full_text = []
        clauses = []
        point_id = len(self.documents) * 1000 + 1

        clause_regex = re.compile(
            r'(?:Clause|Section|Article)\s*(\d+(?:\.\d+)*)[:\.\-\s]+([^\n\r]+)',
            re.IGNORECASE
        )

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            pages_content.append({
                "page_number": page_num + 1,
                "text": text
            })
            raw_full_text.append(text)

            # Detect clauses in page
            lines = text.split("\n")
            current_clause = None
            current_body = []

            for line in lines:
                match = clause_regex.search(line)
                if match:
                    if current_clause:
                        current_clause["quote"] = " ".join(current_body).strip()
                        self._assess_clause_risk(current_clause)
                        clauses.append(current_clause)
                    
                    c_num = match.group(1).strip()
                    c_title = match.group(2).strip()
                    current_clause = {
                        "id": f"{doc_id}_c_{c_num.replace('.', '_')}",
                        "clause_number": f"Clause {c_num}",
                        "title": c_title,
                        "page_number": page_num + 1,
                        "quote": "",
                        "risk_level": "Safe",
                        "risk_badge": "SAFE",
                        "advice": "Standard operational clause."
                    }
                    current_body = []
                elif current_clause:
                    if line.strip():
                        current_body.append(line.strip())

            if current_clause:
                current_clause["quote"] = " ".join(current_body).strip()
                self._assess_clause_risk(current_clause)
                clauses.append(current_clause)

        doc.close()

        # If no explicit "Clause" tags found, chunk by paragraphs/sections
        if not clauses:
            clauses = self._fallback_chunking(pages_content, doc_id)

        # Index clauses into Qdrant vector database
        points = []
        for i, cl in enumerate(clauses):
            c_text = f"{cl.get('clause_number', '')} {cl.get('title', '')}: {cl.get('quote', '')}"
            emb = self.compute_embedding(c_text)
            points.append(
                PointStruct(
                    id=point_id + i,
                    vector=emb,
                    payload={
                        "doc_id": doc_id,
                        "clause_id": cl.get("id"),
                        "clause_number": cl.get("clause_number"),
                        "title": cl.get("title"),
                        "page_number": cl.get("page_number", 1),
                        "quote": cl.get("quote"),
                        "risk_level": cl.get("risk_level", "Safe"),
                        "advice": cl.get("advice", "")
                    }
                )
            )

        if points:
            try:
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            except Exception as e:
                logger.error(f"Error upserting to Qdrant: {e}")

        # Compute document overall risk score
        high_risk_count = sum(1 for c in clauses if c.get("risk_level") == "High Risk")
        med_risk_count = sum(1 for c in clauses if c.get("risk_level") == "Medium Risk")
        safe_count = len(clauses) - (high_risk_count + med_risk_count)
        
        # Risk score calculation from 0 to 100
        overall_risk_score = min(98, 20 + (high_risk_count * 18) + (med_risk_count * 6))
        if high_risk_count == 0 and med_risk_count == 0:
            overall_risk_score = 15

        doc_info = {
            "doc_id": doc_id,
            "title": title,
            "filename": file_path.name,
            "page_count": len(pages_content),
            "total_clauses": len(clauses),
            "high_risk_count": high_risk_count,
            "medium_risk_count": med_risk_count,
            "safe_count": safe_count,
            "overall_risk_score": overall_risk_score,
            "clauses": clauses,
            "pages": pages_content
        }

        self.documents[doc_id] = doc_info
        return doc_info

    def _assess_clause_risk(self, clause: Dict[str, Any]):
        text = f"{clause.get('title', '')} {clause.get('quote', '')}".lower()
        for rule in RISK_RULES:
            if any(k in text for k in rule["keywords"]):
                if rule["condition"](text):
                    clause["risk_level"] = rule["level"]
                    clause["risk_badge"] = rule["badge"]
                    clause["advice"] = rule["advice"]
                    return

    def _fallback_chunking(self, pages: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        clauses = []
        count = 1
        for p in pages:
            paragraphs = p["text"].split("\n\n")
            for para in paragraphs:
                cleaned = para.strip()
                if len(cleaned) > 40:
                    c = {
                        "id": f"{doc_id}_c_{count}",
                        "clause_number": f"Section {count}",
                        "title": cleaned[:40] + ("..." if len(cleaned) > 40 else ""),
                        "page_number": p["page_number"],
                        "quote": cleaned,
                        "risk_level": "Safe",
                        "risk_badge": "SAFE",
                        "advice": "Standard document section."
                    }
                    self._assess_clause_risk(c)
                    clauses.append(c)
                    count += 1
        return clauses

    def search_relevant_clauses(self, query: str, doc_id: Optional[str] = None, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Search vector database for top matching clauses for the user query.
        """
        query_vec = self.compute_embedding(query)
        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vec,
                limit=top_k * 2
            )
            matched = []
            for hit in results:
                payload = hit.payload
                if doc_id and payload.get("doc_id") != doc_id:
                    continue
                matched.append({
                    "score": hit.score,
                    "clause_id": payload.get("clause_id"),
                    "clause_number": payload.get("clause_number"),
                    "title": payload.get("title"),
                    "page_number": payload.get("page_number"),
                    "quote": payload.get("quote"),
                    "risk_level": payload.get("risk_level"),
                    "advice": payload.get("advice")
                })
                if len(matched) >= top_k:
                    break
            if matched:
                return matched
        except Exception as e:
            logger.error(f"Vector search failed: {e}")

        # Lexical search fallback if vector search yielded nothing
        matched = []
        target_doc = self.documents.get(doc_id) if doc_id else next(iter(self.documents.values()), None)
        if target_doc:
            q_lower = query.lower()
            for c in target_doc.get("clauses", []):
                content = f"{c.get('clause_number', '')} {c.get('title', '')} {c.get('quote', '')}".lower()
                if any(w in content for w in q_lower.split() if len(w) > 3):
                    matched.append(c)
                    if len(matched) >= top_k:
                        break
        return matched or (target_doc.get("clauses", [])[:top_k] if target_doc else [])


rag_service = RAGService()
