"""Registration, login, logout and account management."""

from __future__ import annotations

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from ..services.validators import ValidationError, validate_user_credentials
from . import bp


@bp.route("/register", methods=["GET", "POST"])
def register():
    if not current_app.config["PRIMUS_ALLOW_REGISTRATION"]:
        abort(404)
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        try:
            data = validate_user_credentials(
                request.form.get("username", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
                current_app.config,
            )
        except ValidationError as exc:
            flash(str(exc), "error")
            return render_template("auth/register.html", form=request.form), 400

        existing = User.query.filter(
            (User.username == data["username"]) | (User.email == data["email"])
        ).first()
        if existing is not None:
            flash("That username or email is already registered.", "error")
            return render_template("auth/register.html", form=request.form), 409

        user = User(username=data["username"], email=data["email"])
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to Primus.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.username == identity) | (User.email == identity.lower())
        ).first()
        if user is not None and user.check_password(password) and user.is_active:
            login_user(user, remember=bool(request.form.get("remember")))
            flash("Signed in.", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        flash("Invalid username/email or password.", "error")
        return render_template("auth/login.html", identity=identity), 401

    return render_template("auth/login.html", identity="")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))


@bp.get("/account")
@login_required
def account():
    return render_template("auth/account.html", user=current_user)


@bp.post("/account/token")
@login_required
def rotate_token():
    current_user.rotate_api_token()
    db.session.commit()
    flash("API token rotated. Update any clients using the old token.", "success")
    return redirect(url_for("auth.account"))
