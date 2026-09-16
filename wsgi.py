from friendfind import create_app

app = create_app()

# --- TEMPORARY bootstrap route, remove after admin is set up ---
import os
from flask import request, url_for
from friendfind.models import db, Invite, User

BOOTSTRAP_TOKEN = os.environ.get("BOOTSTRAP_TOKEN")

@app.route("/bootstrap-setup")
def _bootstrap_setup():
    if not BOOTSTRAP_TOKEN or request.args.get("token") != BOOTSTRAP_TOKEN:
        return "Not found", 404
    action = request.args.get("action")
    if action == "invite":
        invite = Invite()
        db.session.add(invite)
        db.session.commit()
        url = url_for("auth.register", invite=invite.code, _external=True)
        return f"Invite URL: {url}"
    if action == "admin":
        email = (request.args.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            return f"No member with email {email!r}", 404
        user.is_admin = True
        db.session.commit()
        return f"{user.display_name} <{user.email}> is now an admin."
    return "Use ?action=invite or ?action=admin&email=you@example.com, plus &token=..."
# --- end temporary bootstrap route ---
