import json
import os
import re
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, send_from_directory, flash, get_flashed_messages, abort
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change-this-secret-key-to-something-random"

# Change this to your own passphrase before running.
ADMIN_PASSWORD = "changeme"

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "vouches.json")
SCHEM_DIR = os.path.join(BASE_DIR, "uploads", "schematics")
os.makedirs(SCHEM_DIR, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload cap

VOUCH_CATEGORIES = [
    {"key": "gambling", "label": "Gambling Vouches"},
    {"key": "smp", "label": "SMP Vouches"},
    {"key": "other", "label": "Vouches"},
]

ALLOWED_SCHEM_EXT = {"schem", "schematic", "litematic", "nbt"}

EMPTY_DATA = {"gambling": [], "smp": [], "other": [], "schematics": [], "videos": []}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {k: [] for k in EMPTY_DATA}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Backfill any keys missing from an older data file.
    for key in EMPTY_DATA:
        data.setdefault(key, [])
    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin"))
        return view(*args, **kwargs)
    return wrapped


def allowed_schem(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_SCHEM_EXT


def human_size(num_bytes):
    for unit in ["B", "KB", "MB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} GB"


YOUTUBE_PATTERNS = [
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtube\.com/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})",
]


def extract_youtube_id(url):
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@app.route("/")
def index():
    data = load_data()
    vouch_total = sum(len(data[c["key"]]) for c in VOUCH_CATEGORIES)
    return render_template(
        "index.html",
        data=data,
        categories=VOUCH_CATEGORIES,
        total=vouch_total,
    )


@app.route("/download/schematic/<entry_id>")
def download_schematic(entry_id):
    data = load_data()
    entry = next((s for s in data["schematics"] if s["id"] == entry_id), None)
    if not entry:
        abort(404)
    return send_from_directory(
        SCHEM_DIR,
        entry["stored_filename"],
        as_attachment=True,
        download_name=entry["original_name"],
    )


@app.route("/admin", methods=["GET"])
def admin():
    errors = get_flashed_messages()
    if session.get("is_admin"):
        data = load_data()
        return render_template(
            "admin.html",
            logged_in=True,
            data=data,
            categories=VOUCH_CATEGORIES,
            error=errors[0] if errors else None,
        )
    return render_template("admin.html", logged_in=False, error=None)


@app.route("/admin/login", methods=["POST"])
def admin_login():
    password = request.form.get("password", "")
    if password == ADMIN_PASSWORD:
        session["is_admin"] = True
        return redirect(url_for("admin"))
    return render_template("admin.html", logged_in=False, error="Wrong passphrase — try again.")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin"))


# ---------- Vouches (gambling / smp / other) ----------

@app.route("/admin/add", methods=["POST"])
@login_required
def admin_add():
    category = request.form.get("category", "other")
    text = request.form.get("text", "").strip()
    author = request.form.get("author", "").strip() or "Anonymous"

    if category not in {c["key"] for c in VOUCH_CATEGORIES}:
        category = "other"

    if text:
        data = load_data()
        data[category].insert(0, {
            "id": uuid.uuid4().hex[:8],
            "text": text,
            "author": author,
            "date": datetime.now().strftime("%b %d, %Y"),
        })
        save_data(data)

    return redirect(url_for("admin"))


@app.route("/admin/delete/<category>/<vouch_id>", methods=["POST"])
@login_required
def admin_delete(category, vouch_id):
    data = load_data()
    if category in data:
        data[category] = [v for v in data[category] if v["id"] != vouch_id]
        save_data(data)
    return redirect(url_for("admin"))


# ---------- Schematics ----------

@app.route("/admin/schematics/add", methods=["POST"])
@login_required
def admin_add_schematic():
    file = request.files.get("schematic_file")
    description = request.form.get("description", "").strip()
    author = request.form.get("author", "").strip() or "Anonymous"

    if not file or file.filename == "":
        flash("Choose a schematic file first.")
        return redirect(url_for("admin"))

    if not allowed_schem(file.filename):
        flash("That file type isn't allowed. Use .schem, .schematic, .litematic or .nbt.")
        return redirect(url_for("admin"))

    original_name = secure_filename(file.filename)
    stored_filename = f"{uuid.uuid4().hex[:10]}_{original_name}"
    save_path = os.path.join(SCHEM_DIR, stored_filename)
    file.save(save_path)

    data = load_data()
    data["schematics"].insert(0, {
        "id": uuid.uuid4().hex[:8],
        "stored_filename": stored_filename,
        "original_name": original_name,
        "description": description,
        "author": author,
        "date": datetime.now().strftime("%b %d, %Y"),
        "size": human_size(os.path.getsize(save_path)),
    })
    save_data(data)
    return redirect(url_for("admin"))


@app.route("/admin/schematics/delete/<entry_id>", methods=["POST"])
@login_required
def admin_delete_schematic(entry_id):
    data = load_data()
    entry = next((s for s in data["schematics"] if s["id"] == entry_id), None)
    if entry:
        file_path = os.path.join(SCHEM_DIR, entry["stored_filename"])
        if os.path.exists(file_path):
            os.remove(file_path)
        data["schematics"] = [s for s in data["schematics"] if s["id"] != entry_id]
        save_data(data)
    return redirect(url_for("admin"))


# ---------- Videos ----------

@app.route("/admin/videos/add", methods=["POST"])
@login_required
def admin_add_video():
    url = request.form.get("youtube_url", "").strip()
    title = request.form.get("title", "").strip() or "Untitled"
    author = request.form.get("author", "").strip() or "Anonymous"

    video_id = extract_youtube_id(url)
    if not video_id:
        flash("That doesn't look like a valid YouTube link.")
        return redirect(url_for("admin"))

    data = load_data()
    data["videos"].insert(0, {
        "id": uuid.uuid4().hex[:8],
        "video_id": video_id,
        "url": url,
        "title": title,
        "author": author,
        "date": datetime.now().strftime("%b %d, %Y"),
    })
    save_data(data)
    return redirect(url_for("admin"))


@app.route("/admin/videos/delete/<entry_id>", methods=["POST"])
@login_required
def admin_delete_video(entry_id):
    data = load_data()
    data["videos"] = [v for v in data["videos"] if v["id"] != entry_id]
    save_data(data)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
