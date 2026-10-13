from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from services.auth_service import AuthService
from utils.security import is_safe_redirect_url, validate_csrf_token


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("modules.dashboard"))

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Your session expired. Please try again.", "danger")
            return render_template("register.html"), 400

        result = AuthService.register_user(request.form)
        if result.success:
            flash("Registration successful. Please sign in.", "success")
            return redirect(url_for("auth.login"))

        for error in result.errors:
            flash(error, "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("modules.dashboard"))

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token")):
            flash("Your session expired. Please try again.", "danger")
            return render_template("login.html"), 400

        result = AuthService.authenticate_user(request.form)
        if result.success and result.user:
            login_user(result.user, remember=bool(request.form.get("remember")))
            next_page = request.args.get("next")
            flash("Welcome back. You are signed in.", "success")
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for("modules.dashboard"))

        for error in result.errors:
            flash(error, "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
