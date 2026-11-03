import hmac
import os
import re
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(test_config=None):
    app = Flask(__name__, template_folder=".")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        DATABASE=os.environ.get(
            "DATABASE", str(Path(__file__).with_name("subscribers.sqlite3"))
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    def connect_db():
        database_path = Path(app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    with connect_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                subscribed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return session["_csrf_token"]

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token}

    def require_csrf():
        token = request.form.get("csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not token or not expected or not hmac.compare_digest(token, expected):
            abort(400, description="Invalid form token.")

    def is_admin():
        return session.get("is_admin") is True

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/subscribe")
    def subscribe():
        require_csrf()
        email = request.form.get("email", "").strip().lower()
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            flash("Enter a valid email address.", "error")
            return redirect(url_for("index"))

        with connect_db() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO subscribers (email) VALUES (?)", (email,)
            )
        if cursor.rowcount:
            flash("You’re subscribed. Watch your inbox for updates.", "success")
        else:
            flash("That email is already subscribed.", "info")
        return redirect(url_for("index"))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if is_admin():
            return redirect(url_for("admin"))
        if request.method == "POST":
            require_csrf()
            password = request.form.get("password", "")
            configured_password = app.config["ADMIN_PASSWORD"]
            if configured_password and hmac.compare_digest(
                password, configured_password
            ):
                session.clear()
                session["is_admin"] = True
                return redirect(url_for("admin"))
            flash("Unable to sign in.", "error")
        return render_template("admin_login.html")

    @app.get("/admin")
    def admin():
        if not is_admin():
            return redirect(url_for("admin_login"))
        with connect_db() as connection:
            subscribers = connection.execute(
                "SELECT id, email, subscribed_at FROM subscribers "
                "ORDER BY subscribed_at DESC, id DESC"
            ).fetchall()
        return render_template("admin.html", subscribers=subscribers)

    @app.post("/admin/subscribers/<int:subscriber_id>/delete")
    def delete_subscriber(subscriber_id):
        require_csrf()
        if not is_admin():
            abort(403)
        with connect_db() as connection:
            connection.execute(
                "DELETE FROM subscribers WHERE id = ?", (subscriber_id,)
            )
        flash("Subscriber removed.", "success")
        return redirect(url_for("admin"))

    @app.post("/admin/logout")
    def admin_logout():
        require_csrf()
        if not is_admin():
            abort(403)
        session.clear()
        return redirect(url_for("admin_login"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
