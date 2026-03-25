document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const authMessageDiv = document.getElementById("auth-message");
  const authContainer = document.getElementById("auth-container");
  const sessionContainer = document.getElementById("session-container");
  const sessionUser = document.getElementById("session-user");
  const logoutBtn = document.getElementById("logout-btn");
  const appContent = document.getElementById("app-content");
  const signupContainer = document.getElementById("signup-container");

  let authToken = localStorage.getItem("authToken");
  let userRole = localStorage.getItem("userRole");
  let userEmail = localStorage.getItem("userEmail");

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showMessage(target, text, type) {
    target.textContent = text;
    target.className = type;
    target.classList.remove("hidden");
  }

  function hideMessage(target) {
    target.classList.add("hidden");
  }

  function authHeaders() {
    return {
      Authorization: `Bearer ${authToken}`,
    };
  }

  function clearAuth() {
    authToken = null;
    userRole = null;
    userEmail = null;
    localStorage.removeItem("authToken");
    localStorage.removeItem("userRole");
    localStorage.removeItem("userEmail");
  }

  function updateSessionUI() {
    if (!authToken || !userRole || !userEmail) {
      authContainer.classList.remove("hidden");
      sessionContainer.classList.add("hidden");
      appContent.classList.add("hidden");
      return;
    }

    authContainer.classList.add("hidden");
    sessionContainer.classList.remove("hidden");
    appContent.classList.remove("hidden");
    sessionUser.textContent = `Signed in as ${userEmail} (${userRole})`;

    if (userRole === "student") {
      signupContainer.classList.remove("hidden");
    } else {
      signupContainer.classList.add("hidden");
    }
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    if (!authToken) {
      return;
    }

    try {
      const endpoint = userRole === "admin" ? "/admin/activities" : "/activities";
      const response = await fetch(endpoint, {
        headers: authHeaders(),
      });

      if (response.status === 401) {
        clearAuth();
        updateSessionUI();
        showMessage(authMessageDiv, "Session expired. Please login again.", "error");
        return;
      }

      if (response.status === 403) {
        const forbidden = await response.json();
        showMessage(messageDiv, forbidden.detail || "Access denied.", "error");
        return;
      }

      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - (details.participants_count || details.participants.length);

        const hasParticipants = Array.isArray(details.participants);
        const participantsHTML =
          hasParticipants && details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${escapeHtml(email)}</span><button class="delete-btn" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}">❌</button></li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : hasParticipants
              ? `<p><em>No participants yet</em></p>`
              : "";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${escapeHtml(String(spotsLeft))} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        if (userRole === "student") {
          const option = document.createElement("option");
          option.value = name;
          option.textContent = name;
          activitySelect.appendChild(option);
        }
      });

      if (userRole === "admin") {
        document.querySelectorAll(".delete-btn").forEach((button) => {
          button.addEventListener("click", handleUnregister);
        });
      }
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";

        if (response.status === 401) {
          clearAuth();
          updateSessionUI();
          showMessage(authMessageDiv, "Session expired. Please login again.", "error");
        }
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";

        if (response.status === 401) {
          clearAuth();
          updateSessionUI();
          showMessage(authMessageDiv, "Session expired. Please login again.", "error");
        }
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const result = await response.json();

      if (!response.ok) {
        showMessage(authMessageDiv, result.detail || "Login failed", "error");
        return;
      }

      authToken = result.access_token;
      userRole = result.role;
      userEmail = result.email;
      localStorage.setItem("authToken", authToken);
      localStorage.setItem("userRole", userRole);
      localStorage.setItem("userEmail", userEmail);

      loginForm.reset();
      hideMessage(authMessageDiv);
      updateSessionUI();
      fetchActivities();
    } catch (error) {
      showMessage(authMessageDiv, "Failed to login. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  logoutBtn.addEventListener("click", async () => {
    try {
      await fetch("/logout", {
        method: "POST",
        headers: authHeaders(),
      });
    } catch (_) {
      // best-effort: continue logout even if network fails or token is already expired
    }
    clearAuth();
    updateSessionUI();
    activitiesList.innerHTML = "<p>Please login to view activities.</p>";
    showMessage(authMessageDiv, "You have been logged out.", "info");
  });

  // Initialize app
  updateSessionUI();
  if (authToken) {
    fetchActivities();
  }
});
