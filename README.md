# Main subscriber app

A small Flask site for collecting email subscribers and managing the list through a password-protected admin page. Subscriber records are stored in SQLite.

## Run locally

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="choose-a-strong-password"
python app.py
```

Open `http://127.0.0.1:5000` to subscribe. Visit `/admin/login` to sign in and view or remove subscribers.

The app creates `subscribers.sqlite3` beside `app.py` by default. Set `DATABASE` to use another path. Set `SESSION_COOKIE_SECURE=1` when serving the site over HTTPS. For deployment, use HTTPS and a production WSGI server; do not expose Flask's development server to the internet.
