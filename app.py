from flask import Flask, render_template, request, jsonify # type: ignore
from supabase import create_client # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
import os
from datetime import datetime
import certifi
import ssl

ssl_context = ssl.create_default_context(cafile=certifi.where())

# ================= SUPABASE CONFIG =================

SUPABASE_URL = "YOUR_URL"
SUPABASE_KEY ="YOUR_KEY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# ================= LOGIN CREDENTIALS =================

ADMIN_CREDENTIALS = [
    {"email": "admin@company.com", "password": "company123"}
]

USER_PORTAL = {"email": "user@company.com", "password": "company123"}

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

@app.route("/user-dashboard")
def user_dashboard():
    return render_template("user_dashboard.html")

@app.route("/api/master-file", methods=["POST"])
def add_master_file():
    data = request.json
    print("MASTER DATA RECEIVED:", data)  
    
@app.route("/GSTR1&Form3B/add")
def gstr1_add():
    return render_template("GSTR1&Form3B/add.html")

@app.route("/GSTR1&Form3B/arn")
def gstr1_arn():
    return render_template("GSTR1&Form3B/arn.html")

@app.route("/GSTR1&Form3B/form3b")
def gstr1_form3b():
    return render_template("GSTR1&Form3B/form3b.html")

# ✅ NEW ROUTE (SEARCH)
@app.route("/GSTR1&Form3B/search")
def gstr1_search():
    return render_template("GSTR1&Form3B/search.html")

# ✅ NEW ROUTE (VIEW)
@app.route("/GSTR1&Form3B/view")
def gstr1_view():
    return render_template("GSTR1&Form3B/view.html")

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

    response = supabase.table("master_file").insert({
        "name": data["name"],
        "gst_no": data["gst_no"],
        "id": int(data["id"]),
        "password": data["password"],
        "concern_person": data["concern_person"],
        "contact_no": data["contact_no"],
        "email_id": data["email_id"],
        "periodicity": data["periodicity"],
        "start_month": data["start_month"],
        "end_month": data["end_month"]
    }).execute()

    print("SUPABASE RESPONSE:", response)  

    return jsonify({"message": "Done"})


# ================= UPDATE =================
@app.route("/api/update-master-file", methods=["POST"])
def update_master_file():
    data = request.json

    try:
        # 1️⃣ Update main master table
        supabase.table("master_file")\
            .update({
                "id": int(data["id"]),
                "password": data["password"],
                "concern_person": data["concern_person"],
                "contact_no": data["contact_no"],
                "email_id": data["email_id"],
                "periodicity": data["periodicity"]
            })\
            .eq("gst_no", data["gst_no"])\
            .execute()

        # 2️⃣ Insert into update history table (ONLY existing columns)
        supabase.table("update_master_file").insert({
            "gst_no": data["gst_no"],
            "name": None,  # optional if not in form
            "password": data["password"],
            "concern_person": data["concern_person"],
            "contact_no": data["contact_no"],
            "email_id": data["email_id"],
            "periodicity": data["periodicity"]
        }).execute()

        return jsonify({"message": "Client updated successfully"})

    except Exception as e:
        print("Update Error:", e)
        return jsonify({"error": str(e)}), 500


# ================= GSTR1 =================
# ================= GSTR1 =================
@app.route("/api/gstr1", methods=["POST"])
def add_gstr1():
    data = request.json

    try:
        arn_status = data.get("arn_status")
        arn_no = data.get("arn_no")

        # If not manual entry, ARN number should be None
        if arn_status != "manual":
            arn_no = None

        supabase.table("gstr1_filing").insert({
            "gst_no": data["gst_no"],
            "month": data["month"],
            "arn_status": arn_status,
            "arn_no": arn_no,
            "filing_date": data["filing_date"]
        }).execute()

        return jsonify({"message": "GSTR1 saved successfully"})

    except Exception as e:
        print("GSTR1 ERROR:", e)
        return jsonify({"error": str(e)}), 500



# ================= FORM3B =================
@app.route("/api/form3b", methods=["POST"])
def add_form3b():
    data = request.json

    try:
        supabase.table("form3b_filing").insert({
            "gst_no": data["gst_no"],
            "month": data["month"],
            "arn_no": data["arn_no"],
            "filing_date": data["filing_date"]
        }).execute()

        return jsonify({"message": "Form 3B saved successfully"})

    except Exception as e:
        print("FORM3B ERROR:", e)
        return jsonify({"error": str(e)}), 500

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