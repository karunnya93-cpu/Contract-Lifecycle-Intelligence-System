from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from models import db
from models.user import User
from utils.validators import normalize_email, validate_email, validate_password


@dataclass
class AuthResult:
    success: bool
    user: User | None = None
    errors: list[str] = field(default_factory=list)


class AuthService:
    @staticmethod
    def register_user(form_data: Mapping[str, str]) -> AuthResult:
        full_name = (form_data.get("full_name") or "").strip()
        email = normalize_email(form_data.get("email") or "")
        password = form_data.get("password") or ""
        confirm_password = form_data.get("confirm_password") or ""

        errors: list[str] = []
        if not full_name or len(full_name) < 2:
            errors.append("Enter your full name.")
        if not validate_email(email):
            errors.append("Enter a valid email address.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        password_errors = validate_password(password)
        errors.extend(password_errors)

        if User.query.filter_by(email=email).first():
            errors.append("An account already exists for this email address.")

        if errors:
            return AuthResult(success=False, errors=errors)

        user = User(full_name=full_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return AuthResult(success=True, user=user)

    @staticmethod
    def authenticate_user(form_data: Mapping[str, str]) -> AuthResult:
        email = normalize_email(form_data.get("email") or "")
        password = form_data.get("password") or ""

        if not validate_email(email) or not password:
            return AuthResult(success=False, errors=["Invalid email or password."])

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return AuthResult(success=False, errors=["Invalid email or password."])
        if not user.is_active:
            return AuthResult(success=False, errors=["This account has been deactivated."])

        user.mark_login()
        db.session.commit()
        return AuthResult(success=True, user=user)
