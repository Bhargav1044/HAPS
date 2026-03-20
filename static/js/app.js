/* ================= COMMON UI ================= */

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.remove("active");
  });

  const target = document.getElementById(id);
  if (target) {
    target.classList.add("active");
  }
}

function showError(id, message) {
  const el = document.getElementById(id);
  if (!el) return;

  el.textContent = message;
  el.classList.add("show");
}

/* =====================================================
   LOGIN  (login.html)
===================================================== */

const loginForm = document.getElementById("loginForm");

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const response = await fetch("/api/first-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.getElementById("loginEmail").value,
        password: document.getElementById("loginPassword").value,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      if (data.role === "admin") {
        window.location.href = "/admin";
      } else {
        window.location.href = "/portal";
      }
    } else {
      showError("loginError", data.error);
    }
  });
}

/* =====================================================
   SIGN UP  (user.html)
===================================================== */

const signUpForm = document.getElementById("signUpForm");

if (signUpForm) {
  signUpForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("signUpName").value.trim();
    const password = document.getElementById("signUpPassword").value;
    const confirmPassword = document.getElementById(
      "signUpConfirmPassword",
    ).value;

    if (password !== confirmPassword) {
      return showError("signUpError", "Passwords do not match");
    }

    const response = await fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      const successBox = document.getElementById("signUpSuccess");
      successBox.textContent = "Request submitted!";
      successBox.classList.add("show");
    } else {
      showError("signUpError", data.error);
    }
  });
}

/* =====================================================
   SIGN IN  (user.html)
===================================================== */

const signInForm = document.getElementById("signInForm");

if (signInForm) {
  signInForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const response = await fetch("/api/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("signInName").value,
        password: document.getElementById("signInPassword").value,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      localStorage.setItem(
        "username",
        data.username || document.getElementById("signInName").value,
      );
      window.location.href = "/user-dashboard";
    } else {
      showError("signInError", data.error);
    }
  });
}

/* =====================================================
   ADMIN PANEL  (admin.html)
===================================================== */
async function loadAdminPanel() {
  const response = await fetch("/api/adminpanel");
  if (!response.ok) return;

  const data = await response.json();

  const approvedCount = data.approved_count;
  const pendingCount = data.pending_count;
  const blockedCount = data.approved_users
    ? data.approved_users.filter((u) => u.blocked).length
    : 0;

  if (document.getElementById("approvedCount")) {
    document.getElementById("approvedCount").textContent = approvedCount;
  }
  if (document.getElementById("pendingCount")) {
    document.getElementById("pendingCount").textContent = pendingCount;
  }
  if (document.getElementById("blockedCount")) {
    document.getElementById("blockedCount").textContent = blockedCount;
  }
  if (document.getElementById("pendingBadge")) {
    document.getElementById("pendingBadge").textContent = pendingCount;
  }
  if (document.getElementById("approvedBadge")) {
    document.getElementById("approvedBadge").textContent = approvedCount;
  }

  /* ================= PENDING ================= */

  const pendingList = document.getElementById("pendingList");

  if (data.pending_users.length === 0) {
    pendingList.innerHTML = `
            <div class="empty-state">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="8" y1="12" x2="16" y2="12"/>
                </svg>
                <p>No pending requests</p>
            </div>`;
  } else {
    pendingList.innerHTML = data.pending_users
      .map(
        (user) => `
            <div class="user-card">
                <div class="user-avatar">${escapeHtml(user.username.charAt(0))}</div>
                <div class="user-info">
                    <div class="user-name">${escapeHtml(user.username)}</div>
                    <div class="user-meta"><span class="badge badge-pending">Pending Approval</span></div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-approve"
                            onclick="approveUser('${escapeHtml(String(user.id))}')">
                        Approve
                    </button>
                    <button class="btn btn-sm btn-reject"
                            onclick="rejectUser('${escapeHtml(String(user.id))}')">
                        Reject
                    </button>
                </div>
            </div>
        `,
      )
      .join("");
  }

  /* ================= APPROVED ================= */

  const approvedList = document.getElementById("approvedList");

  if (data.approved_users.length === 0) {
    approvedList.innerHTML = `
            <div class="empty-state">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                </svg>
                <p>No approved users</p>
            </div>`;
  } else {
    approvedList.innerHTML = data.approved_users
      .map(
        (user) => `
            <div class="user-card">
                <div class="user-avatar">${escapeHtml(user.username.charAt(0))}</div>
                <div class="user-info">
                    <div class="user-name">${escapeHtml(user.username)}</div>
                    <div class="user-meta">
                        <span class="badge ${user.blocked ? "badge-blocked" : "badge-approved"}">
                            ${user.blocked ? "Blocked" : "Approved"}
                        </span>
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-edit"
                            onclick="editUser('${escapeHtml(user.username)}')">
                        Edit
                    </button>
                    <button class="btn btn-sm ${user.blocked ? "btn-unblock" : "btn-block"}"
                            onclick="toggleBlock('${escapeHtml(user.username)}')">
                        ${user.blocked ? "Unblock" : "Block"}
                    </button>
                    <button class="btn btn-sm btn-remove"
                            onclick="removeUser('${escapeHtml(user.username)}')">
                        Remove
                    </button>
                </div>
            </div>
        `,
      )
      .join("");
  }
}

/* =====================================================
   ADMIN ACTIONS
===================================================== */

async function approveUser(userId) {
  const response = await fetch(`/api/approve_user/${userId}`, {
    method: "POST",
  });

  const data = await response.json();

  if (data.success) {
    loadAdminPanel();
    alert("User approved successfully!");
  } else {
    alert("Error approving user");
  }
}

async function toggleBlock(username) {
  await fetch("/api/admin/block", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });

  loadAdminPanel();
}

async function removeUser(username) {
  if (!confirm("Remove this user permanently?")) return;

  await fetch("/api/admin/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });

  loadAdminPanel();
}

async function editUser(oldUsername) {
  const newUsername = prompt("Enter new username:");
  const newPassword = prompt("Enter new password:");

  if (!newUsername || !newPassword) return;

  await fetch("/api/admin/edit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      oldUsername,
      newUsername,
      newPassword,
    }),
  });

  loadAdminPanel();
}

async function rejectUser(userId) {
  if (!confirm("Reject this signup request?")) return;

  const response = await fetch(`/api/reject_user/${userId}`, {
    method: "POST",
  });

  const data = await response.json();

  if (data.success) {
    loadAdminPanel();
    alert("User request rejected.");
  } else {
    alert("Error rejecting user.");
  }
}

function togglePassword(inputId, icon) {
  const input = document.getElementById(inputId);

  if (input.type === "password") {
    input.type = "text";
    icon.textContent = "🙈";
  } else {
    input.type = "password";
    icon.textContent = "👁";
  }
}
