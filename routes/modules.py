from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models.contract import Contract
from services.contract_analysis_service import ContractAnalysisService
from services.gemini_contract_service import GeminiContractAnalyzer
from utils.markdown_renderer import render_contract_answer
from utils.security import validate_csrf_token


modules_bp = Blueprint("modules", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx"}


def _module_stats() -> dict[str, str | int]:
    contract_count = Contract.query.filter_by(user_id=current_user.id).count()
    latest_contract = ContractAnalysisService.latest_for_user(current_user.id)
    analysis = latest_contract if latest_contract and latest_contract.analysis_status == "completed" else None
    risks = analysis.risks or [] if analysis else []
    compliance = analysis.compliance or [] if analysis else []
    present = sum(item.get("status") == "Present" for item in compliance)
    compliance_percentage = round((present / len(compliance)) * 100) if compliance else 0
    return {
        "contracts": contract_count,
        "open_risks": sum(item.get("severity") == "High" for item in risks),
        "deadlines": len(analysis.timeline or []) if analysis else 0,
        "compliance": f"{compliance_percentage}%" if analysis else "Not analyzed",
    }


def _is_allowed_contract(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@modules_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", stats=_module_stats())


@modules_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Your session expired. Please try again.", "danger")
            return render_template("upload.html"), 400

        uploaded_file = request.files.get("contract_file")
        if not uploaded_file or not uploaded_file.filename:
            flash("Select a PDF or DOCX contract before uploading.", "warning")
            return redirect(url_for("modules.upload"))

        if not _is_allowed_contract(uploaded_file.filename):
            flash("Only PDF and DOCX contracts are supported.", "danger")
            return redirect(url_for("modules.upload"))

        filename = secure_filename(uploaded_file.filename)
        original = Path(filename)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        stored_name = f"user_{current_user.id}_{timestamp}_{original.stem}{original.suffix}"
        destination = Path(current_app.config["UPLOAD_FOLDER"]) / stored_name
        uploaded_file.save(destination)

        contract = ContractAnalysisService.create_and_analyze(
            user_id=current_user.id,
            original_filename=filename,
            stored_filename=stored_name,
            file_path=destination,
        )
        if contract.analysis_status == "completed":
            flash("Contract uploaded and analyzed successfully.", "success")
        else:
            flash(
                "Contract uploaded, but AI analysis could not be completed. Check the summary page for details.",
                "warning",
            )
        return redirect(url_for("modules.summary"))

    return render_template("upload.html")


@modules_bp.route("/summary")
@login_required
def summary():
    contract = ContractAnalysisService.latest_for_user(current_user.id)
    return render_template("summary.html", contract=contract)


@modules_bp.route("/summary/retry", methods=["POST"])
@login_required
def retry_analysis():
    if not validate_csrf_token(request.form.get("csrf_token")):
        flash("Your session expired. Please try again.", "danger")
        return redirect(url_for("modules.summary"))

    contract_id = request.form.get("contract_id", type=int)
    if not contract_id:
        flash("The contract could not be retried.", "danger")
        return redirect(url_for("modules.summary"))

    contract = ContractAnalysisService.retry_for_user(contract_id, current_user.id)
    if not contract:
        flash("The contract could not be found.", "danger")
    elif contract.analysis_status == "completed":
        flash("Contract analysis completed successfully.", "success")
    else:
        flash("AI analysis is still temporarily unavailable. Please try again in a few moments.", "warning")
    return redirect(url_for("modules.summary"))


@modules_bp.route("/risk")
@login_required
def risk():
    contract = ContractAnalysisService.latest_for_user(current_user.id)
    risks = contract.risks if contract and contract.analysis_status == "completed" else []
    return render_template("risk.html", contract=contract, risks=risks)


@modules_bp.route("/alerts")
@login_required
def alerts():
    contract = ContractAnalysisService.latest_for_user(current_user.id)
    alerts_data = contract.alerts if contract and contract.analysis_status == "completed" else []
    return render_template("alerts.html", contract=contract, alerts_data=alerts_data)


@modules_bp.route("/timeline")
@login_required
def timeline():
    contract = ContractAnalysisService.latest_for_user(current_user.id)
    milestones = contract.timeline if contract and contract.analysis_status == "completed" else []
    return render_template("timeline.html", milestones=milestones)


@modules_bp.route("/compliance")
@login_required
def compliance():
    contract = ContractAnalysisService.latest_for_user(current_user.id)
    checklist = contract.compliance if contract and contract.analysis_status == "completed" else []
    present = sum(item.get("status") == "Present" for item in checklist)
    compliance_percentage = round((present / len(checklist)) * 100) if checklist else None
    return render_template(
        "compliance.html",
        contract=contract,
        checklist=checklist,
        compliance_percentage=compliance_percentage,
    )


@modules_bp.route("/negotiation")
@login_required
def negotiation():
    contract = ContractAnalysisService.latest_for_user(current_user.id)
    suggestions = contract.negotiation if contract and contract.analysis_status == "completed" else []
    return render_template("negotiation.html", contract=contract, suggestions=suggestions)


@modules_bp.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():
    answer = None
    answer_html = None
    question = ""
    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Your session expired. Please try again.", "danger")
            return render_template("chatbot.html", answer=answer, question=question), 400

        question = (request.form.get("question") or "").strip()
        if not question:
            flash("Enter a contract question before sending.", "warning")
        else:
            contract = ContractAnalysisService.latest_for_user(current_user.id)
            if not contract or contract.analysis_status != "completed" or not contract.extracted_text:
                flash("Upload and analyze a contract before asking a question.", "warning")
            else:
                try:
                    answer = GeminiContractAnalyzer.answer_contract_question(contract.extracted_text, question)
                    answer_html = render_contract_answer(answer)
                except Exception:
                    current_app.logger.exception("Contract question failed for user %s", current_user.id)
                    flash("We couldn't answer that question right now. Please try again later.", "warning")
    return render_template(
        "chatbot.html",
        answer=answer,
        answer_html=answer_html,
        question=question,
    )
