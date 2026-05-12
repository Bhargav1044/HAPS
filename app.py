from flask import Flask, render_template, request, jsonify, session, redirect # type: ignore
from db import create_client # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
import os
from datetime import datetime, timedelta
import json

# ================= CONFIG / TERM SETTINGS =================
# Default term is stored in config.json as a fallback.
# Each login session gets its OWN independent term via Flask session.
import platform
if platform.system() == "Windows":
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
else:
    CONFIG_FILE = "/tmp/config.json"

def _get_default_term():
    """Read the global default term from config.json (used for new sessions)."""
    if not os.path.exists(CONFIG_FILE):
        return "2026-27"
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("current_term", "2026-27")
    except:
        return "2026-27"

def _set_default_term(term):
    """Update the global default term in config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"current_term": term}, f)

def get_current_term():
    """Get the term for the CURRENT session (per-user, independent)."""
    return session.get("current_term", _get_default_term())

def set_current_term(term):
    """Set the term for the CURRENT session only (does NOT affect other users)."""
    session["current_term"] = term

# ================= POSTGRESQL CONFIG =================

supabase = create_client()  # connects to local PostgreSQL (see db.py for config)

app = Flask(__name__)
app.secret_key = "haps-secret-key-2026-do-not-share"  # Required for Flask session
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Make sessions permanent (survive browser close) with 30-day lifetime
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ================= LOGIN CREDENTIALS =================

ADMIN_CREDENTIALS = [
    {"email": "amit@cahaps.in", "password": "Bajarang@$%*2026"}
]

USER_PORTAL = {"email": "accounts@cahaps.in", "password": "ARNForHaps@2026"}


# ================= HELPERS =================

def _body():
    """Safely get JSON body"""
    if request.is_json:
        return request.get_json()
    return {}

def _clean(value):
    """Clean string input"""
    if value is None:
        return None
    return str(value).strip()

def _clean_gst(value):
    """Clean GST number (uppercase + trim)"""
    if value is None:
        return None
    return str(value).strip().upper()

# ================= PAGE ROUTES =================

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/portal")
def portal_page():
    return render_template("portal.html")

@app.route("/signin")
def signin_page():
    return render_template("signin.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/admin")
def admin_page():
    if session.get("role") != "admin":
        return redirect("/login")
    return render_template("admin.html")

@app.route("/admin/users")
def admin_users_page():
    return render_template("admin_users.html")

@app.route("/admin/dashboard")
def admin_dashboard_page():
    return render_template("admin_dashboard.html")

@app.route("/user-dashboard")
def user_dashboard():
    if not session.get("role"):
        return redirect("/login")
    return render_template("user_dashboard.html")

@app.route("/api/settings/term", methods=["GET", "POST"])
def manage_term():
    if request.method == "POST":
        data = _body()
        term = data.get("term")
        set_current_term(term)  # Only changes THIS session's term
        # Also update global default if coming from admin rollover
        if data.get("set_default"):
            _set_default_term(term)
        return jsonify({"success": True})
    return jsonify({"success": True, "term": get_current_term()})

@app.route("/api/clients/unique", methods=["GET"])
def unique_clients():
    term = request.args.get("term") or get_current_term()
    clients = {} # gst_no -> obj

    def fetch_clients(table):
        res = supabase.table(table).select("name, gst_no, user_id, password, concern_person, contact_no, email_id, periodicity").eq("term", term).execute()
        for row in (res.data or []):
            if row["gst_no"] not in clients:
                clients[row["gst_no"]] = row

    fetch_clients("gstr1_form3b")
    fetch_clients("cmp08")
    fetch_clients("gstr9_9c")
    fetch_clients("gstr4")

    return jsonify({"success": True, "data": list(clients.values())})

@app.route("/api/admin/rollover", methods=["POST"])
def rollover_clients():
    data = _body()
    new_term = data.get("new_term")
    clients = data.get("clients", [])
    if not new_term:
        return jsonify({"success": False, "error": "Missing new_term param"}), 400

    try:
        parts = new_term.split("-")
        y1 = int(parts[0])
        y2 = 2000 + int(parts[1]) if len(parts[1]) == 2 else int(parts[1])

        months = [
            f"Apr {y1}", f"May {y1}", f"Jun {y1}", f"Jul {y1}", f"Aug {y1}", f"Sep {y1}", 
            f"Oct {y1}", f"Nov {y1}", f"Dec {y1}", f"Jan {y2}", f"Feb {y2}", f"Mar {y2}"
        ]
        quarters = [
            f"Apr - Jun {y1}", f"Jul - Sep {y1}", f"Oct - Dec {y1}", f"Jan - Mar {y2}"
        ]
        quarter_end = {"Jun", "Sep", "Dec", "Mar"}

        for client in clients:
            gst = client.get("gst_no")
            if not gst: continue
            
            p = client.get("periodicity", "Monthly")
            # Category override from frontend: "gstr1" or "cmp08"
            category = client.get("category", "gstr1" if p == "Monthly" else "cmp08")
            base = {
                "name": client.get("name"), "gst_no": gst, "user_id": client.get("user_id"),
                "password": client.get("password"), "concern_person": client.get("concern_person"),
                "contact_no": client.get("contact_no"), "email_id": client.get("email_id"),
                "periodicity": p, "term": new_term
            }

            if category == "gstr1":
                # Build monthly rows; auto-NA GSTR1 ARN for quarterly non-quarter-end months
                gstr1_rows = []
                for m in months:
                    row = {**base, "month": m}
                    if p == "Quarterly":
                        mp = m.split(" ")[0]
                        if mp not in quarter_end:
                            row["gstr1_arn_no"] = "NA"
                            row["gstr1_filing_date"] = "NA"
                    gstr1_rows.append(row)
                supabase.table("gstr1_form3b").insert(gstr1_rows).execute()
                supabase.table("gstr9_9c").insert(base).execute()
            elif category == "cmp08":
                cmp_rows = [{**base, "quarter": q} for q in quarters]
                supabase.table("cmp08").insert(cmp_rows).execute()
                supabase.table("gstr4").insert(base).execute()

        set_current_term(new_term)
        _set_default_term(new_term)  # Rollover also updates the global default
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/term/has-data", methods=["GET"])
def term_has_data():
    """Check if any table already has data for the given term."""
    term = request.args.get("term")
    if not term:
        return jsonify({"success": False, "error": "Missing term"}), 400
    try:
        for table in ["gstr1_form3b", "gstr9_9c", "cmp08", "gstr4"]:
            res = supabase.table(table).select("id").eq("term", term).limit(1).execute()
            if res.data and len(res.data) > 0:
                return jsonify({"success": True, "has_data": True})
        return jsonify({"success": True, "has_data": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/master-file", methods=["POST"])
def add_master_file():
    data = _body() # type: ignore
    print("MASTER DATA RECEIVED:", data)
    return jsonify({"success": True, "data": data})
    
@app.route("/GSTR1_Form3B/add")
def gstr1_add():
    return render_template("GSTR1_Form3B/add.html")

@app.route("/GSTR1_Form3B/arn")
def gstr1_arn():
    return render_template("GSTR1_Form3B/arn.html")

@app.route("/GSTR1_Form3B/form3b")
def gstr1_form3b():
    return render_template("GSTR1_Form3B/form3b.html")

# ✅ NEW ROUTE (SEARCH)
@app.route("/GSTR1_Form3B/search")
def gstr1_search():
    return render_template("GSTR1_Form3B/search.html")

# ✅ NEW ROUTE (VIEW)
@app.route("/GSTR1_Form3B/view")
def gstr1_view():
    return render_template("GSTR1_Form3B/view.html")

@app.route("/gstr9/arn")
def gstr9_arn():
    return render_template("GSTR9/arn.html")

@app.route("/gstr9/view")
def gstr9_view():
    return render_template("GSTR9/view.html")

@app.route("/gstr4/arn")
def gstr4_arn():
    return render_template("GSTR4/arn.html")

@app.route("/gstr4/view")
def gstr4_view():
    return render_template("GSTR4/view.html")

# ===== CMP =====
@app.route("/cmp/add")
def cmp_add():
    return render_template("CMP-08/add.html")

@app.route("/cmp/arn")
def cmp_arn():
    return render_template("CMP-08/arn.html")

@app.route("/cmp/search")
def cmp_search():
    return render_template("CMP-08/search.html")

@app.route("/cmp/view")
def cmp_view():
    return render_template("CMP-08/view.html")

@app.route("/api/gstr1/add", methods=["POST"])
def add_gstr1():
    try:
        data = _body() # type: ignore
        base_payload = {
            "name": _clean(data.get("name")), # type: ignore
            "gst_no": _clean_gst(data.get("gst_no")), # type: ignore
            "user_id": _clean(data.get("user_id")), # type: ignore
            "password": _clean(data.get("password")), # type: ignore
            "concern_person": _clean(data.get("concern_person")), # type: ignore
            "contact_no": _clean(data.get("contact_no")), # type: ignore
            "email_id": _clean(data.get("email_id")), # type: ignore
            "periodicity": _clean(data.get("periodicity")), # type: ignore
            "term": get_current_term()
        }

        months = data.get("months")
        if isinstance(months, list):
            clean_months = [_clean(m) for m in months if _clean(m)] # type: ignore
        else:
            clean_months = []

        # Quarter-end months: only these need manual ARN entry for Quarterly
        quarter_end = {"Jun", "Sep", "Dec", "Mar"}

        # ── DUPLICATE CHECK: gst_no + month + term must be unique ──
        gst_no = base_payload["gst_no"]
        term = base_payload["term"]
        months_to_check = clean_months if clean_months else [_clean(data.get("month"))]
        months_to_check = [m for m in months_to_check if m]  # remove None

        if months_to_check:
            existing = supabase.table("gstr1_form3b").select("month").eq("gst_no", gst_no).eq("term", term).execute()
            existing_months = {r["month"] for r in (existing.data or [])}
            duplicates = [m for m in months_to_check if m in existing_months]
            if duplicates:
                return jsonify({
                    "success": False,
                    "error": f"GST {gst_no} already has entries for: {', '.join(duplicates)} in term {term}. Delete existing entries first or use Search & Update."
                }), 400

        if clean_months:
            rows = []
            for month in clean_months:
                row = {**base_payload, "month": month}
                # Auto-fill NA for non-quarter-end months when Quarterly
                if base_payload.get("periodicity") == "Quarterly":
                    month_prefix = month.split(" ")[0] if " " in month else month
                    if month_prefix not in quarter_end:
                        row["gstr1_arn_no"] = "NA"
                        row["gstr1_filing_date"] = "NA"
            
                rows.append(row)
            response = supabase.table("gstr1_form3b").insert(rows).execute()
        else:
            single_row = {
                **base_payload,
                "month": _clean(data.get("month")) # type: ignore
            }
            # Auto-fill NA for single month if Quarterly and not quarter-end
            if base_payload.get("periodicity") == "Quarterly":
                m = _clean(data.get("month")) or ""
                month_prefix = m.split(" ")[0] if " " in m else m
                if month_prefix not in quarter_end:
                    single_row["gstr1_arn_no"] = "NA"
                    single_row["gstr1_filing_date"] = "NA"
            response = supabase.table("gstr1_form3b").insert(single_row).execute()

        # ── AUTO-LINK: upsert consolidated row into gstr9_9c ──
        gstr9_payload = {
            "name": base_payload["name"],
            "gst_no": base_payload["gst_no"],
            "user_id": base_payload["user_id"],
            "password": base_payload["password"],
            "concern_person": base_payload["concern_person"],
            "contact_no": base_payload["contact_no"],
            "email_id": base_payload["email_id"],
            "periodicity": base_payload["periodicity"],
            "term": base_payload["term"]
        }
        existing = supabase.table("gstr9_9c").select("id").eq("gst_no", base_payload["gst_no"]).eq("term", term).execute()
        if existing.data:
            supabase.table("gstr9_9c").update(gstr9_payload).eq("gst_no", base_payload["gst_no"]).eq("term", term).execute()
        else:
            supabase.table("gstr9_9c").insert(gstr9_payload).execute()

        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/cmp/add", methods=["POST"])
def add_cmp():
    try:
        data = _body()
        base_payload = {
            "name": _clean(data.get("name")),
            "gst_no": _clean_gst(data.get("gst_no")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "term": get_current_term()
        }

        quarters = data.get("quarters")
        if isinstance(quarters, list):
            clean_quarters = [_clean(q) for q in quarters if _clean(q)]
        else:
            clean_quarters = []

        # ── DUPLICATE CHECK: gst_no + quarter + term must be unique ──
        gst_no = base_payload["gst_no"]
        term = base_payload["term"]
        quarters_to_check = clean_quarters if clean_quarters else [_clean(data.get("quarter"))]
        quarters_to_check = [q for q in quarters_to_check if q]  # remove None

        if quarters_to_check:
            existing = supabase.table("cmp08").select("quarter").eq("gst_no", gst_no).eq("term", term).execute()
            existing_quarters = {r["quarter"] for r in (existing.data or [])}
            duplicates = [q for q in quarters_to_check if q in existing_quarters]
            if duplicates:
                return jsonify({
                    "success": False,
                    "error": f"GST {gst_no} already has entries for: {', '.join(duplicates)} in term {term}. Delete existing entries first or use Search & Update."
                }), 400

        if clean_quarters:
            rows = [{**base_payload, "quarter": quarter} for quarter in clean_quarters]
            response = supabase.table("cmp08").insert(rows).execute()
        else:
            response = supabase.table("cmp08").insert({
                **base_payload,
                "quarter": _clean(data.get("quarter"))
            }).execute()

        # ── AUTO-LINK: upsert consolidated row into gstr4 ──
        gstr4_payload = {
            "name": base_payload["name"],
            "gst_no": base_payload["gst_no"],
            "user_id": base_payload["user_id"],
            "password": base_payload["password"],
            "concern_person": base_payload["concern_person"],
            "contact_no": base_payload["contact_no"],
            "email_id": base_payload["email_id"],
            "periodicity": base_payload["periodicity"],
            "term": base_payload["term"]
        }
        existing = supabase.table("gstr4").select("id").eq("gst_no", base_payload["gst_no"]).eq("term", term).execute()
        if existing.data:
            supabase.table("gstr4").update(gstr4_payload).eq("gst_no", base_payload["gst_no"]).eq("term", term).execute()
        else:
            supabase.table("gstr4").insert(gstr4_payload).execute()

        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr1/list", methods=["GET"])
def gstr1_list():
    try:
        term = get_current_term()
        response = supabase.table("gstr1_form3b").select("*").eq("term", term).order("created_at", desc=False).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cmp/list", methods=["GET"])
def cmp_list():
    try:
        term = get_current_term()
        response = supabase.table("cmp08").select("*").eq("term", term).order("created_at", desc=False).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr4/list", methods=["GET"])
def gstr4_list():
    try:
        term = get_current_term()
        response = supabase.table("gstr4").select("*").eq("term", term).order("created_at", desc=False).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr9/list", methods=["GET"])
def gstr9_list():
    try:
        term = get_current_term()
        response = supabase.table("gstr9_9c").select("*").eq("term", term).order("created_at", desc=False).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr1/by-gst", methods=["GET"])
def gstr1_by_gst():
    try:
        gst_no = _clean_gst(request.args.get("gst_no"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400
        response = supabase.table("gstr1_form3b").select("*").eq("gst_no", gst_no).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cmp/by-gst", methods=["GET"])
def cmp_by_gst():
    try:
        gst_no = _clean_gst(request.args.get("gst_no"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400
        response = supabase.table("cmp08").select("*").eq("gst_no", gst_no).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr1/update-profile", methods=["POST"])
def gstr1_update_profile():
    try:
        data = _body()
        gst_no = _clean_gst(data.get("gst_no"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        payload = {
            "name": _clean(data.get("name")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Update ALL rows matching this GST number (across all months)
        response = supabase.table("gstr1_form3b").update(payload).eq("gst_no", gst_no).execute()

        # ── AUTO-LINK: cascade profile update to gstr9_9c ──
        gstr9_payload = {k: v for k, v in payload.items() if k != "updated_at"}
        supabase.table("gstr9_9c").update(gstr9_payload).eq("gst_no", gst_no).execute()

        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cmp/update-profile", methods=["POST"])
def cmp_update_profile():
    try:
        data = _body()
        gst_no = _clean_gst(data.get("gst_no"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        payload = {
            "name": _clean(data.get("name")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Update ALL rows matching this GST number (across all quarters)
        response = supabase.table("cmp08").update(payload).eq("gst_no", gst_no).execute()

        # ── AUTO-LINK: cascade profile update to gstr4 ──
        gstr4_payload = {k: v for k, v in payload.items() if k != "updated_at"}
        supabase.table("gstr4").update(gstr4_payload).eq("gst_no", gst_no).execute()

        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr1/update-arn", methods=["POST"])
def gstr1_update_arn():
    try:
        data = _body()
        gst_no = _clean_gst(data.get("gst_no"))
        month = _clean(data.get("month"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        # ── LOCK CHECK: block updates on auto-filled NA months (quarterly) ──
        if month:
            quarter_end = {"Jun", "Sep", "Dec", "Mar"}
            month_prefix = month.split(" ")[0] if " " in month else month
            existing = supabase.table("gstr1_form3b").select("periodicity, gstr1_arn_no, gstr1_filing_date").eq("gst_no", gst_no).eq("month", month).execute()
            if existing.data:
                row = existing.data[0]
                if row.get("periodicity") == "Quarterly" and month_prefix not in quarter_end:
                    if row.get("gstr1_arn_no") == "NA" and row.get("gstr1_filing_date") == "NA":
                        return jsonify({
                            "success": False,
                            "error": f"Cannot update {month} — this is an auto-filled NA entry for a Quarterly client. Only quarter-end months (Jun, Sep, Dec, Mar) can be updated."
                        }), 400

        payload = {
            "gstr1_arn_no": _clean(data.get("arn")),
            "gstr1_filing_date": _clean(data.get("date")),
            "updated_at": datetime.utcnow().isoformat()
        }

        query = supabase.table("gstr1_form3b").update(payload).eq("gst_no", gst_no)
        if month:
            query = query.eq("month", month)
        response = query.execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr1/update-form3b", methods=["POST"])
def gstr1_update_form3b():
    try:
        data = _body()
        gst_no = _clean_gst(data.get("gst_no"))
        month = _clean(data.get("month"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        # ── LOCK CHECK: block updates on auto-filled NA months (quarterly) ──
        if month:
            quarter_end = {"Jun", "Sep", "Dec", "Mar"}
            month_prefix = month.split(" ")[0] if " " in month else month
            existing = supabase.table("gstr1_form3b").select("periodicity, gstr1_arn_no, gstr1_filing_date").eq("gst_no", gst_no).eq("month", month).execute()
            if existing.data:
                row = existing.data[0]
                if row.get("periodicity") == "Quarterly" and month_prefix not in quarter_end:
                    if row.get("gstr1_arn_no") == "NA" and row.get("gstr1_filing_date") == "NA":
                        return jsonify({
                            "success": False,
                            "error": f"Cannot update {month} — this is an auto-filled NA entry for a Quarterly client. Only quarter-end months (Jun, Sep, Dec, Mar) can be updated."
                        }), 400

        payload = {
            "form3b_arn_no": _clean(data.get("arn")),
            "form3b_filing_date": _clean(data.get("date")),
            "updated_at": datetime.utcnow().isoformat()
        }

        query = supabase.table("gstr1_form3b").update(payload).eq("gst_no", gst_no)
        if month:
            query = query.eq("month", month)
        response = query.execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cmp/update-arn", methods=["POST"])
def cmp_update_arn():
    try:
        data = _body()
        gst_no = _clean_gst(data.get("gst_no"))
        quarter = _clean(data.get("quarter"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        payload = {
            "cmp08_arn_no": _clean(data.get("arn")),
            "cmp08_filing_date": _clean(data.get("date")),
            "updated_at": datetime.utcnow().isoformat()
        }

        query = supabase.table("cmp08").update(payload).eq("gst_no", gst_no)
        if quarter:
            query = query.eq("quarter", quarter)
        response = query.execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dashboard-counts", methods=["GET"])
def dashboard_counts():
    try:
        term = get_current_term()
        gstr1 = supabase.table("gstr1_form3b").select("id").eq("term", term).execute()
        gstr9 = supabase.table("gstr9_9c").select("id").eq("term", term).execute()
        cmp08 = supabase.table("cmp08").select("id").eq("term", term).execute()
        gstr4 = supabase.table("gstr4").select("id").eq("term", term).execute()

        return jsonify({
            "success": True,
            "gstr1_form3b": len(gstr1.data or []),
            "gstr9_9c": len(gstr9.data or []),
            "cmp08": len(cmp08.data or []),
            "gstr4": len(gstr4.data or [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/dashboard/unfilled", methods=["GET"])
def dashboard_unfilled():
    """Return all entries AND entries with missing ARN for each GST category (current term)."""
    try:
        term = get_current_term()

        # GSTR1 / Form3B: all rows for this term
        gstr1_all = supabase.table("gstr1_form3b").select("*").eq("term", term).execute()
        gstr1_all_data = gstr1_all.data or []
        gstr1_unfilled = [r for r in gstr1_all_data if not r.get("gstr1_arn_no")]
        form3b_unfilled = [r for r in gstr1_all_data if not r.get("form3b_arn_no")]

        # GSTR9 & 9C
        gstr9_all = supabase.table("gstr9_9c").select("*").eq("term", term).execute()
        gstr9_all_data = gstr9_all.data or []
        gstr9_unfilled = [r for r in gstr9_all_data if not r.get("gstr9_arn_no") or not r.get("gstr9c_arn_no")]

        # CMP-08
        cmp_all = supabase.table("cmp08").select("*").eq("term", term).execute()
        cmp_all_data = cmp_all.data or []
        cmp_unfilled = [r for r in cmp_all_data if not r.get("cmp08_arn_no")]

        # GSTR4
        gstr4_all = supabase.table("gstr4").select("*").eq("term", term).execute()
        gstr4_all_data = gstr4_all.data or []
        gstr4_unfilled = [r for r in gstr4_all_data if not r.get("gstr4_arn_no")]

        return jsonify({
            "success": True,
            "gstr1":   {"count": len(gstr1_unfilled),  "data": gstr1_unfilled},
            "form3b":  {"count": len(form3b_unfilled),  "data": form3b_unfilled},
            "gstr9":   {"count": len(gstr9_unfilled),   "data": gstr9_unfilled},
            "cmp08":   {"count": len(cmp_unfilled),     "data": cmp_unfilled},
            "gstr4":   {"count": len(gstr4_unfilled),   "data": gstr4_unfilled},
            "all_gstr1": gstr1_all_data,
            "all_cmp08": cmp_all_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/gstr4/update-arn", methods=["POST"])
def update_gstr4():
    data = request.json

    response = supabase.table("gstr4").update({
        "gstr4_arn_no": data.get("arn"),
        "gstr4_filing_date": data.get("date"),
        "updated_at": datetime.utcnow().isoformat()
    }).eq("gst_no", data.get("gst_no")).execute()

    return jsonify(response.data)

@app.route("/api/gstr9/update-arn", methods=["POST"])
def update_gstr9():
    data = request.json

    response = supabase.table("gstr9_9c").update({
        "gstr9_arn_no": data.get("gstr9_arn"),
        "gstr9_filing_date": data.get("gstr9_date"),
        "gstr9c_arn_no": data.get("gstr9c_arn"),
        "gstr9c_filing_date": data.get("gstr9c_date"),
        "updated_at": datetime.utcnow().isoformat()
    }).eq("gst_no", data.get("gst_no")).execute()

    return jsonify(response.data)

# ================= IMPORT ENDPOINTS =================

@app.route("/api/gstr1/import", methods=["POST"])
def import_gstr1():
    try:
        data = _body()
        payload = {
            "name": _clean(data.get("name")),
            "gst_no": _clean_gst(data.get("gst_no")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "month": _clean(data.get("month")),
            "term": get_current_term()
        }

        # ── DUPLICATE CHECK: skip if gst_no + month + term already exists ──
        term = payload["term"]
        existing_row = supabase.table("gstr1_form3b").select("id").eq("gst_no", payload["gst_no"]).eq("month", payload["month"]).eq("term", term).execute()
        if existing_row.data:
            return jsonify({"success": True, "skipped": True, "message": f"Entry for {payload['gst_no']} / {payload['month']} already exists — skipped"})

        response = supabase.table("gstr1_form3b").insert(payload).execute()
        
        # ── AUTO-LINK: upsert consolidated row into gstr9_9c ──
        existing = supabase.table("gstr9_9c").select("id").eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        gstr9_payload = {k: v for k, v in payload.items() if k != "month"}
        if existing.data:
            supabase.table("gstr9_9c").update(gstr9_payload).eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        else:
            supabase.table("gstr9_9c").insert(gstr9_payload).execute()

        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/cmp/import", methods=["POST"])
def import_cmp():
    try:
        data = _body()
        payload = {
            "name": _clean(data.get("name")),
            "gst_no": _clean_gst(data.get("gst_no")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "quarter": _clean(data.get("quarter")),
            "term": get_current_term()
        }

        # ── DUPLICATE CHECK: skip if gst_no + quarter + term already exists ──
        term = payload["term"]
        existing_row = supabase.table("cmp08").select("id").eq("gst_no", payload["gst_no"]).eq("quarter", payload["quarter"]).eq("term", term).execute()
        if existing_row.data:
            return jsonify({"success": True, "skipped": True, "message": f"Entry for {payload['gst_no']} / {payload['quarter']} already exists — skipped"})

        response = supabase.table("cmp08").insert(payload).execute()
        
        # ── AUTO-LINK: upsert consolidated row into gstr4 ──
        existing = supabase.table("gstr4").select("id").eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        gstr4_payload = {k: v for k, v in payload.items() if k != "quarter"}
        if existing.data:
            supabase.table("gstr4").update(gstr4_payload).eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        else:
            supabase.table("gstr4").insert(gstr4_payload).execute()

        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/gstr9/import", methods=["POST"])
def import_gstr9():
    try:
        data = _body()
        payload = {
            "name": _clean(data.get("name")),
            "gst_no": _clean_gst(data.get("gst_no")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "term": get_current_term()
        }
        term = get_current_term()
        existing = supabase.table("gstr9_9c").select("id").eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        if existing.data:
            supabase.table("gstr9_9c").update(payload).eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        else:
            supabase.table("gstr9_9c").insert(payload).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/gstr4/import", methods=["POST"])
def import_gstr4():
    try:
        data = _body()
        payload = {
            "name": _clean(data.get("name")),
            "gst_no": _clean_gst(data.get("gst_no")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "term": get_current_term()
        }
        term = get_current_term()
        existing = supabase.table("gstr4").select("id").eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        if existing.data:
            supabase.table("gstr4").update(payload).eq("gst_no", payload["gst_no"]).eq("term", term).execute()
        else:
            supabase.table("gstr4").insert(payload).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ================= FIRST LOGIN =================

@app.route("/api/first-login", methods=["POST"])
def first_login():
    data = request.json
    email = data["email"]
    password = data["password"]

    if any(a["email"] == email and a["password"] == password for a in ADMIN_CREDENTIALS):
        session.permanent = True
        session["role"] = "admin"
        return jsonify({"role": "admin"})

    if email == USER_PORTAL["email"] and password == USER_PORTAL["password"]:
        session.permanent = True
        session["role"] = "user"
        return jsonify({"role": "user"})

    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


# ================= USER =================

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    username = data["username"]
    password = data["password"]

    # Check approved users
    existing = supabase.table("users").select("*").eq("username", username).execute()
    if existing.data:
        return jsonify({"error": "User already exists"}), 400

    # Check pending
    pending = supabase.table("signup_requests").select("*").eq("username", username).execute()
    if pending.data:
        return jsonify({"error": "Signup request already pending"}), 400

    hashed_password = generate_password_hash(password)

    supabase.table("signup_requests").insert({
        "username": username,
        "password_hash": hashed_password
    }).execute()

    return jsonify({"success": True})


@app.route("/api/signin", methods=["POST"])
def signin():
    data = request.json
    username = data["username"]
    password = data["password"]

    user = supabase.table("users").select("*").eq("username", username).execute()

    if user.data:
        user = user.data[0]

        if user.get("blocked"):
            return jsonify({"error": "Account blocked"}), 403

        if not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify({
            "success": True,
            "username": username
            })

    # Check pending
    pending = supabase.table("signup_requests").select("*").eq("username", username).execute()

    if pending.data:
        return jsonify({"error": "Account pending approval"}), 403

    return jsonify({"error": "Invalid credentials"}), 401


# ================= ADMIN =================

@app.route("/api/admin/data/delete_gstr1", methods=["POST"])
def admin_delete_gstr1():
    try:
        data = request.json
        supabase.table("gstr1_form3b").delete().eq("id", data["id"]).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/data/delete_cmp", methods=["POST"])
def admin_delete_cmp():
    try:
        data = request.json
        supabase.table("cmp08").delete().eq("id", data["id"]).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/data/delete_gstr4", methods=["POST"])
def admin_delete_gstr4():
    try:
        data = request.json
        record_id = data.get("id")
        
        record = supabase.table("gstr4").select("gst_no").eq("id", record_id).execute()
        supabase.table("gstr4").delete().eq("id", record_id).execute()
        
        if record.data and record.data[0].get("gst_no"):
            gst_no = record.data[0]["gst_no"]
            supabase.table("cmp08").delete().eq("gst_no", gst_no).execute()
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/data/delete_gstr9", methods=["POST"])
def admin_delete_gstr9():
    try:
        data = request.json
        record_id = data.get("id")
        
        record = supabase.table("gstr9_9c").select("gst_no").eq("id", record_id).execute()
        supabase.table("gstr9_9c").delete().eq("id", record_id).execute()
        
        if record.data and record.data[0].get("gst_no"):
            gst_no = record.data[0]["gst_no"]
            supabase.table("gstr1_form3b").delete().eq("gst_no", gst_no).execute()
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/adminpanel", methods=["GET"])
def adminpanel():
    try:
        pending_response = supabase.table("signup_requests").select("*").execute()
        approved_response = supabase.table("users").select("*").execute()

        pending_users = pending_response.data or []
        approved_users = approved_response.data or []

        return jsonify({
            "approved_count": len(approved_users),
            "pending_count": len(pending_users),
            "approved_users": approved_users,
            "pending_users": pending_users
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/approve_user/<user_id>", methods=["POST"])
def approve_user(user_id):
    try:
        response = supabase.table("signup_requests") \
            .select("*") \
            .eq("id", user_id) \
            .execute()

        if not response.data:
            return jsonify({"success": False, "error": "User not found"}), 404

        user = response.data[0]

        supabase.table("users").insert({
            "username": user["username"],
            "password_hash": user["password_hash"],
            "approved": True,
            "blocked": False,
            "approved_at": datetime.utcnow().isoformat()
        }).execute()

        supabase.table("signup_requests") \
            .delete() \
            .eq("id", user_id) \
            .execute()

        return jsonify({"success": True})

    except Exception as e:
        print("Approve error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/reject_user/<user_id>", methods=["POST"])
def reject_user(user_id):
    try:
        response = supabase.table("signup_requests") \
            .delete() \
            .eq("id", user_id) \
            .execute()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/block", methods=["POST"])
def block_user():
    username = request.json["username"]

    user = supabase.table("users").select("blocked").eq("username", username).execute()

    if not user.data:
        return jsonify({"error": "User not found"}), 404

    current_status = user.data[0]["blocked"]

    supabase.table("users") \
        .update({"blocked": not current_status}) \
        .eq("username", username) \
        .execute()

    return jsonify({"success": True})


@app.route("/api/admin/remove", methods=["POST"])
def remove_user():
    username = request.json["username"]

    supabase.table("users") \
        .delete() \
        .eq("username", username) \
        .execute()

    return jsonify({"success": True})


@app.route("/api/admin/edit", methods=["POST"])
def edit_user():
    old_username = request.json["oldUsername"]
    new_username = request.json["newUsername"]
    new_password = request.json["newPassword"]

    hashed_password = generate_password_hash(new_password)

    supabase.table("users") \
        .update({
            "username": new_username,
            "password_hash": hashed_password
        }) \
        .eq("username", old_username) \
        .execute()

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)