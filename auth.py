"""Shared authentication for the SEO tools web applications."""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


auth_bp = Blueprint("auth", __name__)
INITIAL_USERS = ("admin", "yesblue0342")
# Bootstrap credential is represented only as a scrypt hash; plaintext is never stored.
DEFAULT_INITIAL_PASSWORD_HASH = "scrypt:32768:8:1$8BJ7Gd9AecFFx3Pd$d77ae4be44cc16c662b327e1e66c479b098e8492af29cfc1668765b26ec67a7e1375b850c778d52412ea26ac1bd55ae268aa4f7e1831a5f94fc69c54a875bcc6"
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5


def _connect() -> sqlite3.Connection:
    path = Path(current_app.config["AUTH_DB_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth(app) -> None:
    """Register auth hooks and create the local account database."""
    app.config.setdefault("AUTH_DB_PATH", os.path.join(app.config["DATA_DIR"], "auth.db"))
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(hours=8))
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_SECURE", os.environ.get("SEO_COOKIE_SECURE", "1") == "1")
    app.config.setdefault("SESSION_COOKIE_PATH", "/")
    app.register_blueprint(auth_bp)
    app.before_request(load_current_user)
    app.context_processor(lambda: {"csrf_token": csrf_token, "current_user": getattr(g, "user", None)})

    with app.app_context():
        init_auth_db()
        seed_initial_users()


def init_auth_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                password_changed_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                attempt_key TEXT PRIMARY KEY,
                failures INTEGER NOT NULL,
                first_attempt INTEGER NOT NULL,
                locked_until INTEGER NOT NULL DEFAULT 0
            );
            """
        )


def seed_initial_users() -> int:
    """Seed both required accounts, preferring an operator-supplied password."""
    initial_password = os.environ.get("SEO_INITIAL_PASSWORD", "")
    password_hash = (
        generate_password_hash(initial_password, method="scrypt")
        if initial_password
        else DEFAULT_INITIAL_PASSWORD_HASH
    )
    now = int(time.time())
    created = 0
    with _connect() as conn:
        for username in INITIAL_USERS:
            cur = conn.execute(
                """INSERT OR IGNORE INTO users
                   (username, password_hash, must_change_password, created_at)
                   VALUES (?, ?, 1, ?)""",
                (username, password_hash, now),
            )
            created += cur.rowcount
    return created


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf() -> None:
    expected = session.get("csrf_token", "")
    provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    if not expected or not provided or not secrets.compare_digest(expected, provided):
        abort(400, description="요청 보안 토큰이 유효하지 않습니다. 페이지를 새로고침해 주세요.")


def load_current_user() -> None:
    g.user = None
    user_id = session.get("user_id")
    version = session.get("session_version")
    if not user_id or version is None:
        return
    with _connect() as conn:
        user = conn.execute(
            """SELECT id, username, must_change_password, session_version
               FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()
    if not user or user["session_version"] != version:
        session.clear()
        return
    g.user = user


def _safe_next(value: str | None) -> str:
    if not value:
        return url_for("g_drive_page")
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or not value.startswith("/") or value.startswith("//"):
        return url_for("g_drive_page")
    return value


def _attempt_key(username: str) -> str:
    ip = request.remote_addr or "unknown"
    return hashlib.sha256(f"{ip}|{username.lower()}".encode()).hexdigest()


def _is_locked(key: str, now: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT locked_until FROM login_attempts WHERE attempt_key = ?", (key,)
        ).fetchone()
    return max(0, int(row["locked_until"]) - now) if row else 0


def _record_failure(key: str, now: int) -> None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT failures, first_attempt FROM login_attempts WHERE attempt_key = ?", (key,)
        ).fetchone()
        if not row or now - int(row["first_attempt"]) > LOGIN_WINDOW_SECONDS:
            failures, first = 1, now
        else:
            failures, first = int(row["failures"]) + 1, int(row["first_attempt"])
        locked_until = now + LOGIN_WINDOW_SECONDS if failures >= LOGIN_MAX_FAILURES else 0
        conn.execute(
            """INSERT INTO login_attempts(attempt_key, failures, first_attempt, locked_until)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(attempt_key) DO UPDATE SET
                 failures=excluded.failures,
                 first_attempt=excluded.first_attempt,
                 locked_until=excluded.locked_until""",
            (key, failures, first, locked_until),
        )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def app_access_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["must_change_password"]:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "먼저 초기 비밀번호를 변경해 주세요."}), 403
            flash("계속하려면 초기 비밀번호를 먼저 변경해 주세요.", "warning")
            return redirect(url_for("auth.change_password"))
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            validate_csrf()
        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and g.user is not None:
        if g.user["must_change_password"]:
            return redirect(url_for("auth.change_password"))
        return redirect(_safe_next(request.args.get("next")))
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        key = _attempt_key(username)
        now = int(time.time())
        wait = _is_locked(key, now)
        if wait:
            flash(f"로그인 시도가 잠겼습니다. {max(1, wait // 60)}분 후 다시 시도해 주세요.", "error")
        else:
            with _connect() as conn:
                user = conn.execute(
                    """SELECT id, username, password_hash, must_change_password, session_version
                       FROM users WHERE username = ? COLLATE NOCASE""",
                    (username,),
                ).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                with _connect() as conn:
                    conn.execute("DELETE FROM login_attempts WHERE attempt_key = ?", (key,))
                session.clear()
                session.permanent = True
                session["user_id"] = user["id"]
                session["session_version"] = user["session_version"]
                csrf_token()
                if user["must_change_password"]:
                    return redirect(url_for("auth.change_password"))
                return redirect(_safe_next(request.form.get("next")))
            _record_failure(key, now)
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "error")
    return render_template("login.html", next_path=_safe_next(request.args.get("next") or request.form.get("next")))


@auth_bp.post("/logout")
@login_required
def logout():
    validate_csrf()
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        validate_csrf()
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        with _connect() as conn:
            user = conn.execute(
                "SELECT password_hash, session_version FROM users WHERE id = ?", (g.user["id"],)
            ).fetchone()
            error = None
            if not check_password_hash(user["password_hash"], current):
                error = "현재 비밀번호가 올바르지 않습니다."
            elif len(new) < 10 or not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
                error = "새 비밀번호는 영문과 숫자를 포함해 10자 이상이어야 합니다."
            elif new != confirm:
                error = "새 비밀번호 확인이 일치하지 않습니다."
            elif check_password_hash(user["password_hash"], new):
                error = "현재 비밀번호와 다른 비밀번호를 사용해 주세요."
            if error:
                flash(error, "error")
            else:
                new_version = int(user["session_version"]) + 1
                conn.execute(
                    """UPDATE users SET password_hash=?, must_change_password=0,
                       session_version=?, password_changed_at=? WHERE id=?""",
                    (generate_password_hash(new, method="scrypt"), new_version, int(time.time()), g.user["id"]),
                )
                session["session_version"] = new_version
                flash("비밀번호가 변경되었습니다.", "success")
                return redirect(url_for("g_drive_page"))
    return render_template("change_password.html")
