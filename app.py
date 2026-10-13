# app.py - Minimal self-hosted habit tracker with numeric value logging.
# Stack: Flask + SQLite (stdlib sqlite3). No other dependencies.
# Run:  python app.py   (or use Docker: docker compose up -d --build)
# Open: http://127.0.0.1:5055

import csv
import io
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, Response, g, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
# Database location. Defaults to a file next to app.py (local Windows use).
# Set HABITS_DB to an absolute path to store it elsewhere (Docker volume on the NAS).
DB_PATH = Path(os.environ.get("HABITS_DB", BASE_DIR / "habits.db"))

app = Flask(__name__)

PALETTE = ["#2f6f8f", "#a63d40", "#5c7a51", "#8f6b3a", "#6b5b95", "#3a7d7c"]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit TEXT NOT NULL DEFAULT 'count',
            daily_target INTEGER NOT NULL DEFAULT 1,
            color TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (date('now','localtime')),
            archived INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
            log_date TEXT NOT NULL,
            value INTEGER NOT NULL,
            logged_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_logs_habit_date ON logs(habit_id, log_date);
        -- Per-profile settings (height for BMI, which measurement is body weight).
        CREATE TABLE IF NOT EXISTS settings (
            profile TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (profile, key)
        );
        """
    )
    # --- Migration: add sort_order if missing, backfill with id (non-destructive) ---
    cols = [r[1] for r in con.execute("PRAGMA table_info(habits)")]
    if "sort_order" not in cols:
        con.execute("ALTER TABLE habits ADD COLUMN sort_order INTEGER")
        con.execute("UPDATE habits SET sort_order = id WHERE sort_order IS NULL")
    # --- Migration: profile (CQ/TQ) and input_type (number/check), additive ---
    if "profile" not in cols:
        con.execute("ALTER TABLE habits ADD COLUMN profile TEXT NOT NULL DEFAULT 'CQ'")
    if "input_type" not in cols:
        con.execute("ALTER TABLE habits ADD COLUMN input_type TEXT NOT NULL DEFAULT 'number'")
    # --- Migration: logs.missed so a real logged 0 differs from a missed day ---
    logcols = [r[1] for r in con.execute("PRAGMA table_info(logs)")]
    if "missed" not in logcols:
        con.execute("ALTER TABLE logs ADD COLUMN missed INTEGER NOT NULL DEFAULT 0")
        # Every pre-existing value-0 row was a 'missed' day under the old model.
        con.execute("UPDATE logs SET missed = 1 WHERE value = 0")
    seed_example(con)  # Demo habits for the "Example" profile (PX), seeded once
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Example profile (PX): a few demo habits with two weeks of sample data, so a new
# user can see how the grid, streaks and totals look. Seeded once only; if the
# user deletes the demo habits they do not come back.
# ---------------------------------------------------------------------------
EXAMPLE_HABITS = [
    # name, unit, daily_target, input_type, values for the last 14 days (oldest first)
    ("Water (example)", "glasses", 8, "number", [6, 8, 8, 7, 8, 9, 8, 5, 8, 8, 8, 6, 8, 7]),
    ("Walk (example)", "min", 30, "number", [20, 35, 30, 0, 45, 30, 30, 15, 30, 40, 0, 30, 30, 25]),
    ("Read (example)", "pages", 10, "number", [10, 12, 0, 10, 15, 10, 8, 10, 0, 20, 10, 10, 12, 10]),
    ("Vitamin (example)", "dose", 1, "check", [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1]),
    # Dose habits: stored as measurements (decimal amount per day). None = no dose that day.
    ("BPC-157 (example)", "mcg", 1, "measure",
     [250, 250, 250, 250, 250, None, None, 250, 250, 250, 250, 250, None, None]),
    ("TB-500 (example)", "mg", 1, "measure",
     [2.5, None, None, 2.5, None, None, None, 2.5, None, None, 2.5, None, None, None]),
    # Response-to-treatment journal (made-up numbers showing a gradual trend).
    ("Sleep (example)", "hours", 1, "measure",
     [6.0, 6.5, 6.0, 6.5, 7.0, 6.5, 7.0, 7.0, 7.5, 7.0, 7.5, 7.5, 8.0, 7.5]),
    ("Resting HR (example)", "bpm", 1, "measure",
     [66, 65, 66, 64, 63, 64, 62, 62, 61, 60, 61, 59, 59, 58]),
    ("HRV (example)", "ms", 1, "measure",
     [41, 43, 42, 45, 46, 44, 48, 49, 50, 52, 51, 54, 55, 56]),
    ("Energy 1-10 (example)", "score", 1, "measure",
     [5, 5, 6, 5, 6, 6, 7, 6, 7, 7, 8, 7, 8, 8]),
    ("Pain 0-10 (example)", "score", 1, "measure",
     [6, 6, 5, 6, 5, 5, 4, 4, 4, 3, 3, 3, 2, 2]),
]


def seed_example(con):
    from datetime import timedelta
    done = con.execute(
        "SELECT 1 FROM settings WHERE profile = 'PX' AND key = 'example_seeded'"
    ).fetchone()
    if done:
        return
    existing = {r[0] for r in con.execute("SELECT name FROM habits")}
    nextpos = con.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM habits").fetchone()[0]
    today = date.today()
    for k, (name, unit, target, itype, values) in enumerate(EXAMPLE_HABITS):
        if name in existing:
            continue
        cur = con.execute(
            "INSERT INTO habits (name, unit, daily_target, color, sort_order, profile, input_type) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, unit, target, PALETTE[k % len(PALETTE)], nextpos + k, "PX", itype),
        )
        hid = cur.lastrowid
        for n, v in enumerate(values):
            if v is None:
                continue
            d = (today - timedelta(days=len(values) - 1 - n)).isoformat()
            con.execute(
                "INSERT INTO logs (habit_id, log_date, value, missed) VALUES (?,?,?,?)",
                (hid, d, v, 1 if v == 0 else 0),
            )
    con.execute(
        "INSERT OR REPLACE INTO settings (profile, key, value) VALUES ('PX', 'example_seeded', '1')"
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/habits", methods=["GET"])
def list_habits():
    profile = request.args.get("profile", "CQ")
    db = get_db()
    rows = db.execute(
        "SELECT id, name, unit, daily_target, color, input_type FROM habits "
        "WHERE archived = 0 AND profile = ? ORDER BY sort_order, id",
        (profile,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/habits", methods=["POST"])
def create_habit():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    unit = (data.get("unit") or "count").strip()
    target = int(data.get("daily_target") or 1)
    profile = (data.get("profile") or "CQ").strip()
    # number = additive reps; check = done/not done; measure = one decimal reading per day (weight, waist)
    input_type = data.get("input_type") if data.get("input_type") in ("check", "measure") else "number"
    if not name:
        return jsonify({"error": "Name is required."}), 400
    db = get_db()
    count = db.execute("SELECT COUNT(*) c FROM habits").fetchone()["c"]
    color = PALETTE[count % len(PALETTE)]
    nextpos = db.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 AS p FROM habits").fetchone()["p"]
    try:
        cur = db.execute(
            "INSERT INTO habits (name, unit, daily_target, color, sort_order, profile, input_type) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, unit, target, color, nextpos, profile, input_type),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "A habit with that name already exists."}), 409
    return jsonify({"id": cur.lastrowid}), 201


@app.route("/api/habits/<int:habit_id>", methods=["DELETE"])
def archive_habit(habit_id):
    db = get_db()
    db.execute("UPDATE habits SET archived = 1 WHERE id = ?", (habit_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/habits/<int:habit_id>/unarchive", methods=["POST"])
def unarchive_habit(habit_id):
    """Un-hide a previously hidden (archived) habit."""
    db = get_db()
    db.execute("UPDATE habits SET archived = 0 WHERE id = ?", (habit_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/habits/archived", methods=["GET"])
def list_archived():
    """Hidden habits for a profile, so the UI can offer to un-hide them."""
    profile = request.args.get("profile", "CQ")
    db = get_db()
    rows = db.execute(
        "SELECT id, name FROM habits WHERE archived = 1 AND profile = ? ORDER BY sort_order, id",
        (profile,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/habits/<int:habit_id>/delete", methods=["POST"])
def delete_habit(habit_id):
    """Permanent delete: removes the habit and all its logs (FK cascade)."""
    db = get_db()
    db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    db.commit()
    return jsonify({"ok": True, "deleted": habit_id})


@app.route("/api/habits/<int:habit_id>/rename", methods=["POST"])
def rename_habit(habit_id):
    name = (request.get_json(force=True).get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required."}), 400
    db = get_db()
    try:
        db.execute("UPDATE habits SET name = ? WHERE id = ?", (name, habit_id))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "A habit with that name already exists."}), 409
    return jsonify({"ok": True, "name": name})


@app.route("/api/habits/<int:habit_id>/move", methods=["POST"])
def move_habit(habit_id):
    """Swap sort position with the adjacent visible habit."""
    direction = (request.get_json(force=True).get("direction") or "").lower()
    db = get_db()
    rows = db.execute(
        "SELECT id, sort_order FROM habits WHERE archived = 0 ORDER BY sort_order, id"
    ).fetchall()
    ids = [r["id"] for r in rows]
    if habit_id not in ids:
        return jsonify({"error": "Unknown habit."}), 404
    i = ids.index(habit_id)
    j = i - 1 if direction == "up" else i + 1
    if j < 0 or j >= len(ids):
        return jsonify({"ok": True, "moved": False})  # already at an end
    a, b = rows[i], rows[j]
    db.execute("UPDATE habits SET sort_order = ? WHERE id = ?", (b["sort_order"], a["id"]))
    db.execute("UPDATE habits SET sort_order = ? WHERE id = ?", (a["sort_order"], b["id"]))
    db.commit()
    return jsonify({"ok": True, "moved": True})


@app.route("/api/log", methods=["POST"])
def add_log():
    """Additive logging: each POST appends a value; daily totals are SUM(value).
    Example: log 20 reps, then 15 reps later the same day -> day total 35."""
    data = request.get_json(force=True)
    habit_id = int(data.get("habit_id"))
    value = int(data.get("value") or 0)
    log_date = data.get("date") or date.today().isoformat()
    datetime.strptime(log_date, "%Y-%m-%d")  # validate format
    if value == 0:
        return jsonify({"error": "Value must be nonzero."}), 400
    db = get_db()
    db.execute(
        "INSERT INTO logs (habit_id, log_date, value) VALUES (?,?,?)",
        (habit_id, log_date, value),
    )
    db.commit()
    total = db.execute(
        "SELECT COALESCE(SUM(value),0) t FROM logs WHERE habit_id=? AND log_date=?",
        (habit_id, log_date),
    ).fetchone()["t"]
    return jsonify({"date": log_date, "day_total": total})


@app.route("/api/day", methods=["POST"])
def set_day():
    """Set one habit's state for one date, replacing prior entries.
    - clear == True        -> day erased (no row, blank)
    - missed == True       -> stored value 0 with missed=1, shown as a dash, excluded from totals
    - otherwise            -> logged value (may be 0, a real logged zero shown as "0")
    The additive /api/log endpoint is unaffected (Quick Log strip)."""
    data = request.get_json(force=True)
    habit_id = int(data.get("habit_id"))
    # Decimals allowed (measurements like 165.5 lbs); whole numbers stay integers.
    fv = float(data.get("value") or 0)
    value = int(fv) if fv.is_integer() else round(fv, 2)
    missed = bool(data.get("missed"))
    clear = bool(data.get("clear"))
    log_date = data.get("date") or date.today().isoformat()
    datetime.strptime(log_date, "%Y-%m-%d")  # validate format
    db = get_db()
    db.execute(
        "DELETE FROM logs WHERE habit_id=? AND log_date=?", (habit_id, log_date)
    )
    if clear:
        state = "blank"                       # erase: no row for the day
    elif missed:
        db.execute(
            "INSERT INTO logs (habit_id, log_date, value, missed) VALUES (?,?,0,1)",
            (habit_id, log_date),
        )
        state = "missed"
    else:
        db.execute(
            "INSERT INTO logs (habit_id, log_date, value, missed) VALUES (?,?,?,0)",
            (habit_id, log_date, value),
        )
        state = "logged"                      # value may be 0 (a real logged zero)
    db.commit()
    return jsonify({"date": log_date, "day_total": value, "state": state})


@app.route("/api/year/<int:year>")
def year_data(year):
    """Daily totals for every habit for one calendar year, plus aggregates."""
    profile = request.args.get("profile", "CQ")
    db = get_db()
    habits = db.execute(
        "SELECT id, name, unit, daily_target, color, input_type FROM habits "
        "WHERE archived = 0 AND profile = ? ORDER BY sort_order, id",
        (profile,),
    ).fetchall()
    out = []
    for h in habits:
        days = db.execute(
            """SELECT log_date, SUM(value) v, MAX(missed) m FROM logs
               WHERE habit_id=? AND strftime('%Y', log_date)=?
               GROUP BY log_date""",
            (h["id"], str(year)),
        ).fetchall()
        daily = {r["log_date"]: r["v"] for r in days}
        missed_days = {r["log_date"]: True for r in days if r["m"]}
        agg = db.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN log_date = date('now','localtime') THEN value END),0) AS today,
                 COALESCE(SUM(CASE WHEN log_date >= date('now','localtime','-6 days') THEN value END),0) AS week,
                 COALESCE(SUM(CASE WHEN strftime('%Y-%m',log_date)=strftime('%Y-%m','now','localtime') THEN value END),0) AS month,
                 COALESCE(SUM(CASE WHEN strftime('%Y',log_date)=? THEN value END),0) AS year
               FROM logs WHERE habit_id=?""",
            (str(year), h["id"]),
        ).fetchone()
        out.append(
            {
                "id": h["id"],
                "name": h["name"],
                "unit": h["unit"],
                "daily_target": h["daily_target"],
                "color": h["color"],
                "input_type": h["input_type"],
                "daily": daily,
                "missed": missed_days,
                "totals": dict(agg),
            }
        )
    return jsonify({"year": year, "habits": out})


@app.route("/api/stats")
def stats():
    """Per-habit totals over several windows plus longest streak, for a profile.
    A streak counts consecutive calendar days whose logged total is > 0;
    a missed day (stored as 0) or an unlogged day breaks it."""
    profile = request.args.get("profile", "CQ")
    db = get_db()
    habits = db.execute(
        "SELECT id, input_type FROM habits WHERE archived = 0 AND profile = ? ORDER BY sort_order, id",
        (profile,),
    ).fetchall()
    out = {}
    for h in habits:
        hid = h["id"]
        if h["input_type"] == "measure":
            # Measurements are averaged over each window (never summed); no streak.
            agg = db.execute(
                """SELECT
                     ROUND(AVG(CASE WHEN log_date = date('now','localtime') THEN value END),1) AS today,
                     ROUND(AVG(CASE WHEN log_date >= date('now','localtime','-6 days') THEN value END),1) AS d7,
                     ROUND(AVG(CASE WHEN log_date >= date('now','localtime','-29 days') THEN value END),1) AS d30,
                     ROUND(AVG(CASE WHEN strftime('%Y',log_date)=strftime('%Y','now','localtime') THEN value END),1) AS year,
                     ROUND(AVG(value),1) AS lifetime
                   FROM logs WHERE habit_id=? AND missed=0""",
                (hid,),
            ).fetchone()
            out[hid] = {k: agg[k] for k in ("today", "d7", "d30", "year", "lifetime")}
            out[hid]["streak"] = 0
            continue
        agg = db.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN log_date = date('now','localtime') THEN value END),0) AS today,
                 COALESCE(SUM(CASE WHEN log_date >= date('now','localtime','-6 days') THEN value END),0) AS d7,
                 COALESCE(SUM(CASE WHEN log_date >= date('now','localtime','-29 days') THEN value END),0) AS d30,
                 COALESCE(SUM(CASE WHEN strftime('%Y',log_date)=strftime('%Y','now','localtime') THEN value END),0) AS year,
                 COALESCE(SUM(value),0) AS lifetime
               FROM logs WHERE habit_id=?""",
            (hid,),
        ).fetchone()
        days = [
            r["log_date"]
            for r in db.execute(
                "SELECT log_date FROM logs WHERE habit_id=? "
                "GROUP BY log_date HAVING SUM(value) > 0 ORDER BY log_date",
                (hid,),
            ).fetchall()
        ]
        longest = run = 0
        prev = None
        for ds in days:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            run = run + 1 if (prev is not None and (d - prev).days == 1) else 1
            longest = max(longest, run)
            prev = d
        out[hid] = {
            "today": agg["today"], "d7": agg["d7"], "d30": agg["d30"],
            "year": agg["year"], "lifetime": agg["lifetime"], "streak": longest,
        }
    return jsonify({"profile": profile, "year": date.today().year, "stats": out})


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Per-profile settings: height_in (inches) and weight_habit_id (for BMI)."""
    profile = request.args.get("profile", "CQ")
    rows = get_db().execute(
        "SELECT key, value FROM settings WHERE profile = ?", (profile,)
    ).fetchall()
    return jsonify({r["key"]: r["value"] for r in rows})


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.get_json(force=True)
    profile = (data.get("profile") or "CQ").strip()
    db = get_db()
    for key in ("height_in", "weight_habit_id", "display_name"):
        if key in data:
            db.execute(
                "INSERT INTO settings (profile, key, value) VALUES (?,?,?) "
                "ON CONFLICT(profile, key) DO UPDATE SET value = excluded.value",
                (profile, key, str(data[key]) if data[key] not in (None, "") else None),
            )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/profile-names")
def profile_names():
    """Display names for the profile buttons (internal keys stay CQ/TQ/...)."""
    rows = get_db().execute(
        "SELECT profile, value FROM settings WHERE key = 'display_name' AND value IS NOT NULL"
    ).fetchall()
    return jsonify({r["profile"]: r["value"] for r in rows})


@app.route("/api/export/csv")
def export_csv():
    """Daily values for every visible habit in a profile: one row per date, one column per habit.
    Missed (dash) days and days with no entry are both left blank. UTF-8 with BOM so Excel opens it cleanly."""
    profile = request.args.get("profile", "CQ")
    db = get_db()
    habits = db.execute(
        "SELECT id, name, unit FROM habits WHERE archived = 0 AND profile = ? ORDER BY sort_order, id",
        (profile,),
    ).fetchall()
    by_date = {}
    for h in habits:
        for r in db.execute(
            "SELECT log_date, SUM(value) v, MAX(missed) m FROM logs WHERE habit_id = ? GROUP BY log_date",
            (h["id"],),
        ):
            if r["m"] and not r["v"]:
                continue
            by_date.setdefault(r["log_date"], {})[h["id"]] = r["v"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date"] + [f'{h["name"]} ({h["unit"]})' for h in habits])
    for d in sorted(by_date):
        w.writerow([d] + [by_date[d].get(h["id"], "") for h in habits])
    resp = Response("\ufeff" + buf.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="habit_tracker_{profile}_{date.today():%Y%m%d}.csv"'
    )
    return resp




if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5055, debug=False)
