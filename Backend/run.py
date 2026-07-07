"""
run.py
======
Local development entry point. `python run.py` starts Flask's built-in dev
server. In production, gunicorn imports `wsgi.py` instead (see Docker/).
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
