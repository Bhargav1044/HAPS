from flask import Flask, render_template, request, jsonify # type: ignore
from supabase import create_client # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
import os
from datetime import datetime
import certifi
import ssl
import json

ssl_context = ssl.create_default_context(cafile=certifi.where())

# ================= CONFIG / TERM SETTINGS =================
CONFIG_FILE = "/tmp/config.json"

def get_current_term():
    if not os.path.exists(CONFIG_FILE):
        return "2025-26"
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("current_term", "2025-26")
    except:
        return "2025-26"

def set_current_term(term):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"current_term": term}, f)

# ================= SUPABASE CONFIG =================

SUPABASE_URL = "https://fxzzdmpusmhroyxjzfwk.supabase.co"
SUPABASE_KEY ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ4enpkbXB1c21ocm95eGp6ZndrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyOTc3MiwiZXhwIjoyMDg3NjA1NzcyfQ.OPDu7-jmaFc4vD16zDR8BcsoJjYWRiCOfmFdKtP3ZYg"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

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
    return render_template("admin.html")

@app.route("/admin/users")
def admin_users_page():
    return render_template("admin_users.html")

@app.route("/admin/dashboard")
def admin_dashboard_page():
    return render_template("admin_dashboard.html")

@app.route("/user-dashboard")
def user_dashboard():
    return render_template("user_dashboard.html")

@app.route("/api/settings/term", methods=["GET", "POST"])
def manage_term():
    if request.method == "POST":
        data = _body()
        set_current_term(data.get("term"))
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

        for client in clients:
            gst = client.get("gst_no")
            if not gst: continue
            
            p = client.get("periodicity", "Monthly")
            base = {
                "name": client.get("name"), "gst_no": gst, "user_id": client.get("user_id"),
                "password": client.get("password"), "concern_person": client.get("concern_person"),
                "contact_no": client.get("contact_no"), "email_id": client.get("email_id"),
                "periodicity": p, "term": new_term
            }

            if p == "Monthly":
                gstr1_rows = [{**base, "month": m} for m in months]
                supabase.table("gstr1_form3b").insert(gstr1_rows).execute()
                supabase.table("gstr9_9c").insert(base).execute()
            elif p == "Quarterly":
                cmp_rows = [{**base, "quarter": q} for q in quarters]
                supabase.table("cmp08").insert(cmp_rows).execute()
                supabase.table("gstr4").insert(base).execute()

        set_current_term(new_term)
        return jsonify({"success": True})
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
                        row["form3b_arn_no"] = "NA"
                        row["form3b_filing_date"] = "NA"
            
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
                    single_row["form3b_arn_no"] = "NA"
                    single_row["form3b_filing_date"] = "NA"
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
        existing = supabase.table("gstr9_9c").select("id").eq("gst_no", base_payload["gst_no"]).execute()
        if existing.data:
            supabase.table("gstr9_9c").update(gstr9_payload).eq("gst_no", base_payload["gst_no"]).execute()
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
        existing = supabase.table("gstr4").select("id").eq("gst_no", base_payload["gst_no"]).execute()
        if existing.data:
            supabase.table("gstr4").update(gstr4_payload).eq("gst_no", base_payload["gst_no"]).execute()
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
        month = _clean(data.get("month"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        payload = {
            "name": _clean(data.get("name")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "month": month,
            "updated_at": datetime.utcnow().isoformat()
        }

        query = supabase.table("gstr1_form3b").update(payload).eq("gst_no", gst_no)
        if month:
            query = query.eq("month", month)
        response = query.execute()

        # ── AUTO-LINK: cascade profile update to gstr9_9c ──
        gstr9_payload = {k: v for k, v in payload.items() if k not in ["month", "updated_at"]}
        supabase.table("gstr9_9c").update(gstr9_payload).eq("gst_no", gst_no).execute()

        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cmp/update-profile", methods=["POST"])
def cmp_update_profile():
    try:
        data = _body()
        gst_no = _clean_gst(data.get("gst_no"))
        quarter = _clean(data.get("quarter"))
        if not gst_no:
            return jsonify({"success": False, "error": "gst_no is required"}), 400

        payload = {
            "name": _clean(data.get("name")),
            "user_id": _clean(data.get("user_id")),
            "password": _clean(data.get("password")),
            "concern_person": _clean(data.get("concern_person")),
            "contact_no": _clean(data.get("contact_no")),
            "email_id": _clean(data.get("email_id")),
            "periodicity": _clean(data.get("periodicity")),
            "quarter": quarter,
            "updated_at": datetime.utcnow().isoformat()
        }

        query = supabase.table("cmp08").update(payload).eq("gst_no", gst_no)
        if quarter:
            query = query.eq("quarter", quarter)
        response = query.execute()

        # ── AUTO-LINK: cascade profile update to gstr4 ──
        gstr4_payload = {k: v for k, v in payload.items() if k not in ["quarter", "updated_at"]}
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
        gstr1 = supabase.table("gstr1_form3b").select("id").execute()
        gstr9 = supabase.table("gstr9_9c").select("id").execute()
        cmp08 = supabase.table("cmp08").select("id").execute()
        gstr4 = supabase.table("gstr4").select("id").execute()

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
    """Return all entries with missing ARN for each GST category (current term)."""
    try:
        term = get_current_term()

        # GSTR1: rows where gstr1_arn_no is null
        gstr1_all = supabase.table("gstr1_form3b").select("*").eq("term", term).execute()
        gstr1_unfilled = [r for r in (gstr1_all.data or []) if not r.get("gstr1_arn_no")]

        # Form 3B: rows where form3b_arn_no is null
        form3b_unfilled = [r for r in (gstr1_all.data or []) if not r.get("form3b_arn_no")]

        # GSTR9 & 9C: rows where gstr9_arn_no OR gstr9c_arn_no is null
        gstr9_all = supabase.table("gstr9_9c").select("*").eq("term", term).execute()
        gstr9_unfilled = [r for r in (gstr9_all.data or []) if not r.get("gstr9_arn_no") or not r.get("gstr9c_arn_no")]

        # CMP-08: rows where cmp08_arn_no is null
        cmp_all = supabase.table("cmp08").select("*").eq("term", term).execute()
        cmp_unfilled = [r for r in (cmp_all.data or []) if not r.get("cmp08_arn_no")]

        # GSTR4: rows where gstr4_arn_no is null
        gstr4_all = supabase.table("gstr4").select("*").eq("term", term).execute()
        gstr4_unfilled = [r for r in (gstr4_all.data or []) if not r.get("gstr4_arn_no")]

        return jsonify({
            "success": True,
            "gstr1":   {"count": len(gstr1_unfilled),  "data": gstr1_unfilled},
            "form3b":  {"count": len(form3b_unfilled),  "data": form3b_unfilled},
            "gstr9":   {"count": len(gstr9_unfilled),   "data": gstr9_unfilled},
            "cmp08":   {"count": len(cmp_unfilled),     "data": cmp_unfilled},
            "gstr4":   {"count": len(gstr4_unfilled),   "data": gstr4_unfilled}
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
        response = supabase.table("gstr1_form3b").insert(payload).execute()
        
        # ── AUTO-LINK: upsert consolidated row into gstr9_9c ──
        term = get_current_term()
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
        response = supabase.table("cmp08").insert(payload).execute()
        
        # ── AUTO-LINK: upsert consolidated row into gstr4 ──
        term = get_current_term()
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
        return jsonify({"role": "admin"})

    if email == USER_PORTAL["email"] and password == USER_PORTAL["password"]:
        return jsonify({"role": "user"})

    return jsonify({"error": "Invalid credentials"}), 401


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
    app.run(debug=True)