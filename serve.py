# serve.py - Production entrypoint for the habit tracker (used inside Docker).
# Runs the app under waitress (a real WSGI server) instead of Flask's dev server.
# Local Windows use still goes through app.py; this file is for the NAS container.

from waitress import serve

from app import app, init_db

if __name__ == "__main__":
    init_db()
    serve(app, host="0.0.0.0", port=5055)
