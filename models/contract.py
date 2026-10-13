from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, text

from models import db


class Contract(db.Model):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    executive_summary = db.Column(db.Text, nullable=True)
    agreement_type = db.Column(db.String(255), nullable=True)
    key_parties = db.Column(db.Text, nullable=True)
    business_purpose = db.Column(db.Text, nullable=True)
    effective_date = db.Column(db.String(120), nullable=True)
    expiry_date = db.Column(db.String(120), nullable=True)
    contract_value = db.Column(db.String(255), nullable=True)
    risk_score = db.Column(db.Integer, nullable=True)
    risks = db.Column(db.JSON, nullable=True)
    alerts = db.Column(db.JSON, nullable=True)
    timeline = db.Column(db.JSON, nullable=True)
    compliance = db.Column(db.JSON, nullable=True)
    negotiation = db.Column(db.JSON, nullable=True)
    analysis_status = db.Column(db.String(40), nullable=False, default="pending")
    analysis_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    analyzed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("contracts", lazy="dynamic"))

    @classmethod
    def ensure_analysis_columns(cls) -> None:
        """Add analysis columns for existing SQLite installations without data loss."""
        inspector = inspect(db.engine)
        if cls.__tablename__ not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns(cls.__tablename__)}
        columns = {
            "risk_score": "INTEGER",
            "risks": "JSON",
            "alerts": "JSON",
            "timeline": "JSON",
            "compliance": "JSON",
            "negotiation": "JSON",
        }
        for name, column_type in columns.items():
            if name not in existing_columns:
                db.session.execute(text(f"ALTER TABLE {cls.__tablename__} ADD COLUMN {name} {column_type}"))
        db.session.commit()
