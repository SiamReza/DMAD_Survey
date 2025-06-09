"""
Flask survey application — minimal, self‑contained.
Folder layout assumed:
    survey-app/
    ├─ app.py                  (this file)
    ├─ static/images/<folders> (all source images)
    └─ results/                (per‑participant CSVs)
"""

import csv
import os
from uuid import uuid4
from typing import List, Tuple

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    abort,
)

###############################################################################
# Configuration & constants
###############################################################################

# Root paths (relative to project root)
STATIC_DIR = "static"
IMAGE_ROOT = os.path.join(STATIC_DIR, "images")  # static/images/
RESULTS_DIR = "results"

# Ensure critical paths exist at start‑up
os.makedirs(RESULTS_DIR, exist_ok=True)

###############################################################################
# Build comparison list (100 pairs)
###############################################################################

def _make_pair(group: str, folder_a: str, suffix_a: str, folder_b: str, suffix_b: str) -> List[Tuple[str, str, str]]:
    """Return 10 (group, img1, img2) tuples for indexes 1‑10."""
    pairs = []
    for i in range(1, 11):
        img1 = f"images/{folder_a}/{i}_{suffix_a}.jpg"  # path is relative to static/
        img2 = f"images/{folder_b}/{i}_{suffix_b}.jpg"
        pairs.append((group, img1, img2))
    return pairs

# Define the 10 comparison schemas (each yields 10 rows)
COMPARISON_SCHEMAS = [
    ("bonafide S1 vs S2", "S1_BF", "s1_bf", "S2_BF", "s2_bf"),
    ("bonafide vs MorDiff", "S1_BF", "s1_bf", "MorDiff", "mordiff"),
    ("bonafide vs US", "S1_BF", "s1_bf", "US", "us"),
    ("bonafide vs USFD", "S1_BF", "s1_bf", "USFD", "usfd"),
    ("bonafide vs PuLID", "S1_BF", "s1_bf", "PuLID", "pulid"),
    ("bonafide vs Ace", "S1_BF", "s1_bf", "Ace", "ace"),
    ("MorDiff vs US", "MorDiff", "mordiff", "US", "us"),
    ("MorDiff vs USFD", "MorDiff", "mordiff", "USFD", "usfd"),
    ("MorDiff vs PuLID", "MorDiff", "mordiff", "PuLID", "pulid"),
    ("MorDiff vs Ace", "MorDiff", "mordiff", "Ace", "ace"),
]

# Flatten to a single ordered list
comparisons: List[Tuple[str, str, str]] = []
for group, folder_a, suff_a, folder_b, suff_b in COMPARISON_SCHEMAS:
    comparisons.extend(_make_pair(group, folder_a, suff_a, folder_b, suff_b))

assert len(comparisons) == 100, "Expected exactly 100 comparison rows"

###############################################################################
# Flask app
###############################################################################

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CHANGE_ME")  # Replace in production

###############################################################################
# Helper functions
###############################################################################

def _current_uuid() -> str:
    return session.get("uuid", "")

def _participant_csv_path(uuid_str: str) -> str:
    return os.path.join(RESULTS_DIR, f"{uuid_str}.csv")

def _write_csv_row(row: List[str]) -> None:
    """Append `row` to the participant‑specific CSV, creating header if needed."""
    uuid_str = row[0]
    csv_path = _participant_csv_path(uuid_str)

    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf‑8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["uuid", "gender", "age", "group", "image1", "image2", "rating"])
        writer.writerow(row)

###############################################################################
# Routes
###############################################################################

@app.route("/", methods=["GET", "POST"])
def demographics():
    if request.method == "GET":
        return render_template("demographics.html")

    # POST – validate inputs
    gender = request.form.get("gender", "").strip()
    age = request.form.get("age", "").strip()

    if not gender or not age.isdigit():
        abort(400, description="Invalid demographic data")

    # Store in session
    session.clear()
    session["uuid"] = str(uuid4())
    session["gender"] = gender
    session["age"] = age

    return redirect(url_for("compare", i=0))

@app.route("/compare/<int:i>", methods=["GET", "POST"])
def compare(i: int):
    uuid_str = _current_uuid()
    if not uuid_str:
        return redirect(url_for("demographics"))  # No session – restart

    if i >= len(comparisons):
        return redirect(url_for("finish"))

    # Handle form submission
    if request.method == "POST":
        rating = request.form.get("rating", "").strip()
        if rating not in {"1", "2", "3", "4", "5"}:
            abort(400, description="Invalid rating value")

        group, img1, img2 = comparisons[i]
        _write_csv_row([
            uuid_str,
            session.get("gender", ""),
            session.get("age", ""),
            group,
            img1,
            img2,
            rating,
        ])
        return redirect(url_for("compare", i=i + 1))

    # GET – render comparison page
    group, img1, img2 = comparisons[i]
    return render_template(
        "compare.html",
        index=i,
        total=len(comparisons),
        img1=img1,
        img2=img2,
        group=group,
    )

@app.route("/finish")
def finish():
    if not _current_uuid():
        return redirect(url_for("demographics"))
    return render_template("finish.html")

###############################################################################
# Entrypoint
###############################################################################

if __name__ == "__main__":
    # Enable reloader/debug only for local development
    app.run(debug=True, port=5000)
