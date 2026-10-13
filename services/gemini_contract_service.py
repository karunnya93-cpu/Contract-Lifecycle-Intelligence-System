from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from flask import current_app


class GeminiAnalysisError(RuntimeError):
    pass


class GeminiTemporarilyUnavailableError(GeminiAnalysisError):
    """Raised after all bounded retries for a transient Gemini outage fail."""

    pass


@dataclass
class ContractAnalysis:
    executive_summary: str
    agreement_type: str
    key_parties: list[str]
    business_purpose: str
    effective_date: str
    expiry_date: str
    contract_value: str
    risk_score: int
    risks: list[dict[str, str]]
    alerts: list[dict[str, str]]
    timeline: list[dict[str, str]]
    compliance: list[dict[str, str]]
    negotiation: list[dict[str, str]]


class GeminiContractAnalyzer:

    MAX_RETRIES = 3
    RETRY_DELAYS_SECONDS = (2, 4, 8)

    REQUIRED_KEYS = {
        "executive_summary",
        "agreement_type",
        "key_parties",
        "business_purpose",
        "effective_date",
        "expiry_date",
        "contract_value",
        "risk_score",
        "risks",
        "alerts",
        "timeline",
        "compliance",
        "negotiation",
    }

    @staticmethod
    def analyze_contract(text: str) -> ContractAnalysis:
        api_key = (
            current_app.config.get("GEMINI_API_KEY") or ""
        ).strip()

        if not api_key:
            raise GeminiAnalysisError(
                "Gemini is not configured. Add GEMINI_API_KEY "
                "to the project's .env file and restart the application."
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiAnalysisError(
                "google-genai is not installed."
            ) from exc

        client = genai.Client(api_key=api_key)

        response = GeminiContractAnalyzer._generate_content_with_retry(
            client,
            model=current_app.config["GEMINI_MODEL"],
            contents=GeminiContractAnalyzer._build_prompt(
                text[: current_app.config["CONTRACT_TEXT_LIMIT"]]
            ),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        payload = GeminiContractAnalyzer._parse_json(
            response.text or ""
        )

        return ContractAnalysis(
            executive_summary=GeminiContractAnalyzer._clean(
                payload["executive_summary"]
            ),
            agreement_type=GeminiContractAnalyzer._clean(
                payload["agreement_type"]
            ),
            key_parties=GeminiContractAnalyzer._string_list(
                payload["key_parties"]
            ),
            business_purpose=GeminiContractAnalyzer._clean(
                payload["business_purpose"]
            ),
            effective_date=GeminiContractAnalyzer._clean(
                payload["effective_date"]
            ),
            expiry_date=GeminiContractAnalyzer._clean(
                payload["expiry_date"]
            ),
            contract_value=GeminiContractAnalyzer._clean(
                payload["contract_value"]
            ),
            risk_score=GeminiContractAnalyzer._risk_score(
                payload["risk_score"]
            ),
            risks=GeminiContractAnalyzer._object_list(
                payload["risks"],
                {"title", "severity", "description"},
            ),
            alerts=GeminiContractAnalyzer._object_list(
                payload["alerts"],
                {"title", "message"},
            ),
            timeline=GeminiContractAnalyzer._object_list(
                payload["timeline"],
                {"title", "date"},
            ),
            compliance=GeminiContractAnalyzer._object_list(
                payload["compliance"],
                {"clause", "status"},
            ),
            negotiation=GeminiContractAnalyzer._object_list(
                payload["negotiation"],
                {"suggestion", "reason"},
            ),
        )

    @staticmethod
    def answer_contract_question(
        contract_text: str,
        question: str,
    ) -> str:

        api_key = (
            current_app.config.get("GEMINI_API_KEY") or ""
        ).strip()

        if not api_key:
            raise GeminiAnalysisError(
                "Gemini is not configured."
            )

        try:
            from google import genai
        except ImportError as exc:
            raise GeminiAnalysisError(
                "google-genai is not installed."
            ) from exc

        prompt = (
            "Answer the user's question using only the uploaded "
            "contract text.\n"
            "Use very simple and easy-to-understand English.\n"
            "Do not use complicated legal language.\n"
            "Keep the answer short, direct, and factually complete.\n"
            "Return Markdown only; never return HTML.\n"
            "Start with one short introductory sentence.\n"
            "When the answer has multiple clauses, obligations, risks, "
            "deadlines, parties, conditions, or exceptions, use a numbered "
            "list with a bold heading for each major point.\n"
            "Put supporting details beneath each numbered point as bullet "
            "points indented by four spaces, and leave a blank line between "
            "numbered sections.\n"
            "Use a simple bullet list when the answer is naturally a list.\n"
            "Preserve important contract terminology, dates, amounts, "
            "percentages, obligations, risks, conditions, and exceptions.\n"
            "Do not repeat unnecessary information or merge separate facts "
            "into one large paragraph.\n"
            "If the answer is not found in the contract, say exactly: "
            "\"This information is not available in the contract.\"\n\n"
            f"Contract text:\n"
            f"{contract_text[:current_app.config['CONTRACT_TEXT_LIMIT']]}"
            "\n\n"
            f"Question: {question}"
        )

        response = GeminiContractAnalyzer._generate_content_with_retry(
            genai.Client(api_key=api_key),
            model=current_app.config["GEMINI_MODEL"],
            contents=prompt,
        )

        answer = (response.text or "").strip()

        if not answer:
            raise GeminiAnalysisError(
                "Gemini returned an empty answer."
            )

        return answer

    @staticmethod
    def _generate_content_with_retry(client: Any, **request_kwargs: Any) -> Any:
        """Call Gemini with bounded retries for transient service failures only."""
        for retry_number, delay in enumerate(
            GeminiContractAnalyzer.RETRY_DELAYS_SECONDS,
            start=1,
        ):
            try:
                return client.models.generate_content(**request_kwargs)
            except Exception as exc:
                if not GeminiContractAnalyzer._is_retryable_error(exc):
                    raise GeminiAnalysisError(
                        "Gemini could not complete this request. Please try again later."
                    ) from exc

                current_app.logger.warning(
                    "Gemini request failed with %s. Retrying %s/%s in %s seconds.",
                    GeminiContractAnalyzer._error_code(exc),
                    retry_number,
                    GeminiContractAnalyzer.MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)

        try:
            return client.models.generate_content(**request_kwargs)
        except Exception as exc:
            if GeminiContractAnalyzer._is_retryable_error(exc):
                current_app.logger.warning(
                    "Gemini request remained unavailable after %s retries (status %s).",
                    GeminiContractAnalyzer.MAX_RETRIES,
                    GeminiContractAnalyzer._error_code(exc),
                )
                raise GeminiTemporarilyUnavailableError(
                    "AI analysis is temporarily unavailable because the Gemini service "
                    "is experiencing high demand. Please try again in a few moments."
                ) from exc
            raise GeminiAnalysisError(
                "Gemini could not complete this request. Please try again later."
            ) from exc

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        status = str(getattr(exc, "status", "")).upper()
        return code in {408, 429, 500, 502, 503, 504} or status in {
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "RATE_LIMIT_EXCEEDED",
            "TOO_MANY_REQUESTS",
            "DEADLINE_EXCEEDED",
        }

    @staticmethod
    def _error_code(exc: Exception) -> str:
        return str(getattr(exc, "code", None) or getattr(exc, "status", None) or "unknown")

    @staticmethod
    def _build_prompt(contract_text: str) -> str:

        return f"""
You are a senior legal contract analyst.

Analyze only the contract provided below.

Return ONLY one valid JSON object.

Do not use Markdown.
Do not use code fences.
Do not add commentary.
Do not add extra keys.

Use "Not found" when a scalar value is unavailable.

Use [] when no list items are supported by the contract.

Do not invent facts.

Keep dates and monetary values exactly as stated where possible.

risk_score must be an integer from 0 to 100.

Risk severity must be:
High, Medium, or Low.

Compliance status must be:
Present, Missing, or Needs Review.

Include Contract Start, Renewal Notice, Expiry Date,
and any other material milestones in timeline only when
supported by the contract.

Return this exact JSON structure:

{{
    "executive_summary": "",
    "agreement_type": "",
    "key_parties": [],
    "business_purpose": "",
    "effective_date": "",
    "expiry_date": "",
    "contract_value": "",
    "risk_score": 0,
    "risks": [
        {{
            "title": "",
            "severity": "High",
            "description": ""
        }}
    ],
    "alerts": [
        {{
            "title": "",
            "message": ""
        }}
    ],
    "timeline": [
        {{
            "title": "",
            "date": ""
        }}
    ],
    "compliance": [
        {{
            "clause": "",
            "status": "Present"
        }}
    ],
    "negotiation": [
        {{
            "suggestion": "",
            "reason": ""
        }}
    ]
}}

Contract text:

{contract_text}
"""

    @staticmethod
    def _parse_json(raw_text: str) -> dict[str, Any]:

        try:
            payload = json.loads(raw_text.strip())

        except json.JSONDecodeError as exc:
            raise GeminiAnalysisError(
                "Gemini returned invalid analysis data. "
                "Please try the upload again."
            ) from exc

        if not isinstance(payload, dict):
            raise GeminiAnalysisError(
                "Gemini returned an invalid analysis format."
            )

        missing = (
            GeminiContractAnalyzer.REQUIRED_KEYS.difference(
                payload
            )
        )

        if missing:
            raise GeminiAnalysisError(
                "Gemini response is missing fields: "
                + ", ".join(sorted(missing))
                + "."
            )

        return payload

    @staticmethod
    def _clean(value: Any) -> str:

        if value is None:
            return "Not found"

        cleaned = str(value).strip()

        if not cleaned:
            return "Not found"

        return cleaned

    @staticmethod
    def _string_list(value: Any) -> list[str]:

        if not isinstance(value, list):
            raise GeminiAnalysisError(
                "Gemini returned invalid key parties data."
            )

        return [
            GeminiContractAnalyzer._clean(item)
            for item in value
            if str(item).strip()
        ]

    @staticmethod
    def _risk_score(value: Any) -> int:

        try:
            score = int(value)

        except (TypeError, ValueError) as exc:
            raise GeminiAnalysisError(
                "Gemini returned an invalid risk score."
            ) from exc

        if not 0 <= score <= 100:
            raise GeminiAnalysisError(
                "Gemini returned a risk score outside 0-100."
            )

        return score

    @staticmethod
    def _object_list(
        value: Any,
        keys: set[str],
    ) -> list[dict[str, str]]:

        if not isinstance(value, list):
            raise GeminiAnalysisError(
                "Gemini returned invalid list analysis data."
            )

        items: list[dict[str, str]] = []

        for item in value:

            if (
                not isinstance(item, dict)
                or not keys.issubset(item)
            ):
                raise GeminiAnalysisError(
                    "Gemini returned incomplete list analysis data."
                )

            items.append(
                {
                    key: GeminiContractAnalyzer._clean(item[key])
                    for key in keys
                }
            )

        return items
