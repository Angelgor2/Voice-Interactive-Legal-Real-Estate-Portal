import re
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from config import NVIDIA_NIM_API_KEY, NVIDIA_NIM_URL, NVIDIA_MODEL

logger = logging.getLogger("llm_service")
logging.basicConfig(level=logging.INFO)


class LLMService:
    def __init__(self):
        self.api_key = NVIDIA_NIM_API_KEY
        self.nim_url = NVIDIA_NIM_URL
        self.model = NVIDIA_MODEL

    async def analyze_legal_query(
        self,
        query: str,
        retrieved_clauses: List[Dict[str, Any]],
        language: str = "en-IN"
    ) -> Dict[str, Any]:
        """
        Reason over real legal contract clauses retrieved from the document.
        Extracts:
        - 2-3 executive bullet points
        - Spoken summary for Gnani Timbre
        - Exact clause citations (clause number, page number, quote, risk level, Evon insight)
        - Actionable advice
        """
        logger.info(f"Analyzing query: '{query}' with {len(retrieved_clauses)} retrieved clauses")

        if self.api_key and not self.api_key.startswith("your_"):
            try:
                context_blocks = []
                for c in retrieved_clauses:
                    context_blocks.append(
                        f"[{c.get('clause_number', 'Clause')}] (Page {c.get('page_number', 1)}): "
                        f"\"{c.get('quote', '')}\""
                    )
                context_str = "\n".join(context_blocks)

                system_prompt = (
                    "You are Evon, an elite legal reasoning engine for Indian tenancy, lease, and property documents.\n"
                    "Analyze the provided contract clauses against the user query. Output strictly valid JSON with:\n"
                    "{\n"
                    "  \"spoken_summary\": \"A clear, 2-3 sentence conversational response suitable for TTS audio\",\n"
                    "  \"executive_bullet_points\": [\"Takeaway 1 with financial/legal impact\", \"Takeaway 2\", \"Takeaway 3\"],\n"
                    "  \"cited_clauses\": [\n"
                    "    {\n"
                    "      \"clause_id\": \"id\",\n"
                    "      \"clause_number\": \"Clause X\",\n"
                    "      \"page_number\": 1,\n"
                    "      \"title\": \"Title\",\n"
                    "      \"quote\": \"exact verbatim excerpt\",\n"
                    "      \"risk_level\": \"High Risk\" | \"Medium Risk\" | \"Safe\",\n"
                    "      \"evon_insight\": \"Specific practical explanation\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"actionable_advice\": \"Specific counter-proposal or negotiation wording\"\n"
                    "}"
                )

                user_content = f"User Question: {query}\n\nRelevant Contract Clauses:\n{context_str}"

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"}
                }

                async with httpx.AsyncClient(timeout=45.0) as client:
                    res = await client.post(self.nim_url, headers=headers, json=payload)

                if res.status_code == 200:
                    parsed = json.loads(res.json()["choices"][0]["message"]["content"])
                    return parsed
            except Exception as e:
                logger.error(f"NVIDIA NIM error, falling back to dynamic clause analyzer: {e}")

        # Dynamic reasoning analyzer operating directly on the actual retrieved clauses from the PDF
        return self._dynamic_clause_analysis(query, retrieved_clauses)

    def _dynamic_clause_analysis(self, query: str, retrieved_clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Dynamically extracts legal implications, risk ratings, and executive bullet points
        from the actual retrieved clauses and user query.
        """
        if not retrieved_clauses:
            return {
                "spoken_summary": "I searched your agreement but could not find a clause directly matching this question. Please check the contract section index.",
                "executive_bullet_points": [
                    "No direct clause found in the active document.",
                    "Review the agreement's miscellaneous covenants.",
                    "Consult your legal advisor before signing."
                ],
                "cited_clauses": [],
                "actionable_advice": "Check the agreement schedule or ask your landlord for clarification."
            }

        primary_clause = retrieved_clauses[0]
        c_num = primary_clause.get("clause_number", "Clause")
        c_title = primary_clause.get("title", "")
        c_page = primary_clause.get("page_number", 1)
        c_quote = primary_clause.get("quote", "")
        c_id = primary_clause.get("clause_id") or primary_clause.get("id") or f"c_{c_page}"
        c_risk = primary_clause.get("risk_level", "Safe")

        # Extract specific monetary amounts or numbers from the quote
        amounts = re.findall(r'(?:INR|₹|Rs\.?)\s*[\d,]+', c_quote)
        periods = re.findall(r'\d+\s*(?:months?|days?|years?)', c_quote, re.IGNORECASE)

        amount_str = f" of {amounts[0]}" if amounts else ""
        period_str = f" for {periods[0]}" if periods else ""

        # Formulate dynamic executive bullet points
        bullet_1 = f"{c_num} ({c_title}): Specifies terms on Page {c_page}{period_str}{amount_str}."
        
        if c_risk == "High Risk":
            bullet_2 = f"Elevated Risk: This clause enforces strict liabilities or forfeiture provisions that exceed standard metropolitan tenancy norms."
            bullet_3 = "Recommended Action: Negotiate this term down to mutual notice (typically 30 to 60 days) prior to signing."
            spoken = f"According to {c_num} on page {c_page}, {c_quote[:140]}... This is classified as High Risk because the penalty or lock-in is heavily biased in favor of the lessor."
            advice = "Request replacing unconditional penalty with mutual 60 days written notice or one month rent in lieu of notice."
        elif c_risk == "Medium Risk":
            bullet_2 = f"Moderate Impact: Contains obligations like security deposits or escalation that warrant careful timeline review."
            bullet_3 = "Recommended Action: Confirm refund turnaround (standard is 30 days) and ensure escalation caps do not exceed 5% to 7% annually."
            spoken = f"Under {c_num}, the agreement provides that {c_quote[:130]}... This carries a Medium Risk rating, and we recommend confirming exact refund timelines."
            advice = "Ensure security deposit refund is linked directly to physical key surrender with standard deduction caps."
        else:
            bullet_2 = f"Standard Provision: The terms for {c_title.lower()} appear clear, operational, and standard."
            bullet_3 = "Compliance Check: Ensure all utility receipts and society dues are settled up to the handover date."
            spoken = f"Under {c_num}, {c_quote[:130]}... This appears to be a standard, fair clause for your tenancy."
            advice = "Verify that past society maintenance dues are fully cleared by the landlord before taking possession."

        cited = [
            {
                "clause_id": c_id,
                "clause_number": c_num,
                "page_number": c_page,
                "title": c_title,
                "quote": c_quote,
                "risk_level": c_risk,
                "risk_badge": "HIGH RISK" if c_risk == "High Risk" else ("MEDIUM" if c_risk == "Medium Risk" else "SAFE"),
                "evon_insight": primary_clause.get("advice") or f"Governed under {c_num}. Review financial impact before executing."
            }
        ]

        # Add second retrieved clause if relevant
        if len(retrieved_clauses) > 1:
            sec_c = retrieved_clauses[1]
            cited.append({
                "clause_id": sec_c.get("clause_id") or sec_c.get("id") or f"c_{sec_c.get('page_number', 1)}_2",
                "clause_number": sec_c.get("clause_number", "Related Clause"),
                "page_number": sec_c.get("page_number", 1),
                "title": sec_c.get("title", "Related Provision"),
                "quote": sec_c.get("quote", ""),
                "risk_level": sec_c.get("risk_level", "Safe"),
                "risk_badge": "SAFE" if sec_c.get("risk_level") == "Safe" else "MEDIUM",
                "evon_insight": sec_c.get("advice") or "Complementary covenant to be read alongside the primary clause."
            })

        return {
            "spoken_summary": spoken,
            "executive_bullet_points": [bullet_1, bullet_2, bullet_3],
            "cited_clauses": cited,
            "actionable_advice": advice
        }


llm_service = LLMService()
