// auth.js — shared by every role page (employee.html, manager.html, finance.html, admin.html)
// Include it once with <script src="{% static 'payments/auth.js' %}"></script>, before each
// page's own <script> block, then call AUTH.apiFetch(...) instead of fetch(...) everywhere.

const AUTH = (() => {
  const ACCESS_KEY = "imaraworks_access";
  const REFRESH_KEY = "imaraworks_refresh";

  // NOTE on localStorage: simplest option for a project this size, and fine here —
  // but worth knowing the honest tradeoff: tokens in localStorage are readable by any
  // JS that runs on the page (an XSS risk in a production app). The safer alternative,
  // an httpOnly cookie set by the server, is more setup than this timeline has room for.
  // Worth a one-line mention under "known limitations" in the documentation.

  function getAccess() { return localStorage.getItem(ACCESS_KEY); }
  function getRefresh() { return localStorage.getItem(REFRESH_KEY); }

  function setTokens(access, refresh) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  }

  function clearTokens() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }

  async function login(username, password) {
    const res = await fetch("/api/auth/login/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error("Login failed — check the username and password.");
    const data = await res.json();
    setTokens(data.access, data.refresh);
    return data;
  }

  function logout() {
    clearTokens();
    window.location.href = "/login/"; // adjust once the real login page route exists
  }

  async function refreshAccessToken() {
    const refresh = getRefresh();
    if (!refresh) throw new Error("No refresh token on file — need to log in again.");
    const res = await fetch("/api/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      clearTokens();
      throw new Error("Session expired — please log in again.");
    }
    const data = await res.json(); // refresh endpoint returns a new access token only
    setTokens(data.access);
    return data.access;
  }

  // The one function every page should call instead of fetch() directly.
  // Attaches the access token; if the server says it's expired (401), refreshes
  // once and retries the same request before giving up.
  async function apiFetch(url, options = {}) {
    const access = getAccess();
    const headers = { ...(options.headers || {}), Authorization: `Bearer ${access}` };
    let res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
      try {
        const newAccess = await refreshAccessToken();
        const retryHeaders = { ...(options.headers || {}), Authorization: `Bearer ${newAccess}` };
        res = await fetch(url, { ...options, headers: retryHeaders });
      } catch (err) {
        logout();
        throw err;
      }
    }
    return res;
  }

  async function getCurrentUser() {
    const res = await apiFetch("/api/auth/me/");
    if (!res.ok) throw new Error("Could not load the current user.");
    return res.json(); // { username, first_name, last_name, role }
  }

  return {
    login,
    logout,
    apiFetch,
    getCurrentUser,
    isLoggedIn: () => !!getAccess(),
  };
})();