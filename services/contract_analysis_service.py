from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from models import db
from models.contract import Contract
from services.document_service import DocumentTextExtractor
from services.gemini_contract_service import GeminiContractAnalyzer


class ContractAnalysisService:
    """Coordinates contract storage, text extraction, and Gemini analysis."""

    @staticmethod
    def create_and_analyze(
        user_id: int,
        original_filename: str,
        stored_filename: str,
        file_path: Path,
    ) -> Contract:
        """Persist an upload, then save either its analysis or a failure state."""
        contract = Contract(
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            analysis_status="pending",
        )
        db.session.add(contract)
        db.session.commit()

        return ContractAnalysisService._analyze_contract(contract, file_path)

    @staticmethod
    def retry_for_user(contract_id: int, user_id: int) -> Contract | None:
        """Re-run analysis only for the requesting user's existing contract."""
        contract = Contract.query.filter_by(id=contract_id, user_id=user_id).first()
        if not contract:
            return None
        return ContractAnalysisService._analyze_contract(contract, Path(contract.file_path))

    @staticmethod
    def _analyze_contract(contract: Contract, file_path: Path) -> Contract:
        contract.analysis_status = "pending"
        contract.analysis_error = None
        db.session.commit()

        try:
            if not contract.extracted_text:
                contract.extracted_text = DocumentTextExtractor.extract_text(file_path)
                db.session.commit()
            analysis = GeminiContractAnalyzer.analyze_contract(contract.extracted_text)

            contract.executive_summary = analysis.executive_summary
            contract.agreement_type = analysis.agreement_type
            contract.key_parties = "\n".join(analysis.key_parties)
            contract.business_purpose = analysis.business_purpose
            contract.effective_date = analysis.effective_date
            contract.expiry_date = analysis.expiry_date
            contract.contract_value = analysis.contract_value
            contract.risk_score = analysis.risk_score
            contract.risks = analysis.risks
            contract.alerts = analysis.alerts
            contract.timeline = analysis.timeline
            contract.compliance = analysis.compliance
            contract.negotiation = analysis.negotiation
            contract.analysis_status = "completed"
            contract.analysis_error = None
            contract.analyzed_at = datetime.now(timezone.utc)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception("Contract analysis failed for %s", contract.stored_filename)
            contract.analysis_status = "failed"
            contract.analysis_error = str(exc)
            db.session.commit()

        return contract

    @staticmethod
    def latest_for_user(user_id: int) -> Contract | None:
        """Return the most recently uploaded contract belonging to one user."""
        return (
            Contract.query.filter_by(user_id=user_id)
            .order_by(Contract.created_at.desc(), Contract.id.desc())
            .first()
        )
