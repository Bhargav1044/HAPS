from flask import Flask, render_template, request, jsonify # type: ignore
from supabase import create_client # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
import os
from datetime import datetime
import certifi
import ssl

ssl_context = ssl.create_default_context(cafile=certifi.where())

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
    {"email": "admin@company.com", "password": "company123"}
]

USER_PORTAL = {"email": "user@company.com", "password": "company123"}


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

@app.route("/user-dashboard")
def user_dashboard():
    return render_template("user_dashboard.html")

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
            "periodicity": _clean(data.get("periodicity")) # type: ignore
        }

        months = data.get("months")
        if isinstance(months, list):
            clean_months = [_clean(m) for m in months if _clean(m)] # type: ignore
        else:
            clean_months = []

        if clean_months:
            rows = [{**base_payload, "month": month} for month in clean_months]
            response = supabase.table("gstr1_form3b").insert(rows).execute()
        else:
            response = supabase.table("gstr1_form3b").insert({
                **base_payload,
                "month": _clean(data.get("month")) # type: ignore
            }).execute()

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
            "periodicity": _clean(data.get("periodicity"))
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
        response = supabase.table("gstr1_form3b").select("*").order("created_at", desc=True).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cmp/list", methods=["GET"])
def cmp_list():
    try:
        response = supabase.table("cmp08").select("*").order("created_at", desc=True).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr4/list", methods=["GET"])
def gstr4_list():
    try:
        response = supabase.table("gstr4").select("*").order("created_at", desc=True).execute()
        return jsonify({"success": True, "data": response.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/gstr9/list", methods=["GET"])
def gstr9_list():
    try:
        response = supabase.table("gstr9_9c").select("*").order("created_at", desc=True).execute()
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
        supabase.table("gstr4").delete().eq("id", data["id"]).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/data/delete_gstr9", methods=["POST"])
def admin_delete_gstr9():
    try:
        data = request.json
        supabase.table("gstr9_9c").delete().eq("id", data["id"]).execute()
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