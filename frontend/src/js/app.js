/**
 * app.js — entry point, wires all modules together
 *
 * SSE event sequence handled:
 *   job_started       → show progress bar
 *   row_started       → create skeleton row
 *   row_text_done     → populate row with text content and detail panel
 *   row_image_generating → (no-op, skeleton already shown)
 *   row_image_done    → inject real image thumbnail
 *   row_video_generating → (no-op)
 *   row_video_done    → inject video player into detail panel
 *   row_done          → mark row done, tick progress, store complete asset
 *   row_error         → show error badge, tick progress
 *   job_complete      → hide progress bar, show results header
 */

import { postCSV } from "./api.js";
import {
  _assets,
  hideError,
  hideProgress,
  markCardDone,
  markCardError,
  removeCard,
  renderCard,
  resetUI,
  setDeleteCallback,
  showError,
  showProgress,
  showResults,
  updateCardImage,
  updateCardText,
  updateCardVideo,
  updateProgress,
} from "./ui.js";
import { initUploader } from "./uploader.js";
import {
  initAuth,
  onAuthStateChange,
  signInWithGoogle,
  signInWithEmail,
  signUpWithEmail,
  signOut,
  getUser,
} from "./auth.js";

const generateBtn = document.getElementById("generate-btn");
const exportBtn = document.getElementById("export-btn");

let selectedFile = null;
let totalRows = 0;
let doneRows = 0;

// ---- Table state (search / sort / pagination) ----

const _tableState = {
  allRows: [],      // array of { productId, name, receivedAt } in insertion order
  filtered: [],     // after search + sort applied
  currentPage: 1,
  pageSize: 5,
};

// ---- Pagination / search DOM refs ----

const _searchInput = document.getElementById("search-input");
const _sortSelect = document.getElementById("sort-select");
const _prevBtn = document.getElementById("prev-btn");
const _nextBtn = document.getElementById("next-btn");
const _pageIndicator = document.getElementById("page-indicator");
const _paginationInfo = document.getElementById("pagination-info");
const _paginationEl = document.getElementById("pagination");

/**
 * Rebuild the visible rows based on current search query, sort order, and page.
 * Shows/hides <tr> elements directly in the DOM.
 */
function _rebuildTable() {
  const query = (_searchInput ? _searchInput.value : "").trim().toLowerCase();
  const sortOrder = _sortSelect ? _sortSelect.value : "asc";

  // 1. Filter
  _tableState.filtered = _tableState.allRows.filter(({ productId, name }) => {
    if (!query) return true;
    return (
      String(productId).toLowerCase().includes(query) ||
      (name || "").toLowerCase().includes(query)
    );
  });

  // 2. Sort by receivedAt
  _tableState.filtered.sort((a, b) => {
    return sortOrder === "desc"
      ? b.receivedAt - a.receivedAt
      : a.receivedAt - b.receivedAt;
  });

  // 3. Clamp page
  const totalPages = Math.max(1, Math.ceil(_tableState.filtered.length / _tableState.pageSize));
  if (_tableState.currentPage > totalPages) _tableState.currentPage = totalPages;

  const start = (_tableState.currentPage - 1) * _tableState.pageSize;
  const end = start + _tableState.pageSize;

  // Build a set of productIds visible on the current page
  const visibleIds = new Set(
    _tableState.filtered.slice(start, end).map((r) => r.productId)
  );

  // 4. Show/hide rows — also collapse open detail rows on page change
  _tableState.allRows.forEach(({ productId }) => {
    const mainRow = document.getElementById(`row-${productId}`);
    const detailRow = document.getElementById(`row-detail-${productId}`);
    const visible = visibleIds.has(productId);

    if (mainRow) mainRow.style.display = visible ? "" : "none";
    if (detailRow) {
      if (!visible) {
        // Collapse detail row when row goes off-page
        detailRow.classList.remove("open");
        detailRow.style.display = "none";
        const btn = document.querySelector(`[data-product-id="${productId}"].expand-btn`);
        if (btn) btn.innerHTML = "&#9660;";
      } else {
        // Restore display (open class controls visibility via CSS)
        detailRow.style.display = "";
      }
    }
  });

  // 5. Reorder visible rows in the DOM to match the current sort order.
  // appendChild moves an existing node to the end, so iterating in sorted
  // order physically rearranges the rows without any flicker.
  const resultsTbody = document.getElementById("results-tbody");
  if (resultsTbody) {
    _tableState.filtered.slice(start, end).forEach(({ productId }) => {
      const mainRow = document.getElementById(`row-${productId}`);
      const detailRow = document.getElementById(`row-detail-${productId}`);
      if (mainRow) resultsTbody.appendChild(mainRow);
      if (detailRow) resultsTbody.appendChild(detailRow);
    });
  }

  // 6. Update pagination UI
  const total = _tableState.filtered.length;

  if (_paginationEl) {
    _paginationEl.style.display = total > 0 ? "" : "none";
  }

  if (_paginationInfo) {
    if (total === 0) {
      _paginationInfo.textContent = "No results";
    } else {
      const from = start + 1;
      const to = Math.min(end, total);
      _paginationInfo.textContent = `Showing ${from}–${to} of ${total} result${total !== 1 ? "s" : ""}`;
    }
  }

  if (_pageIndicator) {
    _pageIndicator.textContent = `Page ${_tableState.currentPage} of ${totalPages}`;
  }

  if (_prevBtn) _prevBtn.disabled = _tableState.currentPage <= 1;
  if (_nextBtn) _nextBtn.disabled = _tableState.currentPage >= totalPages;
}

function _goToPage(page) {
  _tableState.currentPage = page;
  _rebuildTable();
}

// Wire up search + sort
if (_searchInput) {
  _searchInput.addEventListener("input", () => {
    _tableState.currentPage = 1;
    _rebuildTable();
  });
}

if (_sortSelect) {
  _sortSelect.addEventListener("change", () => {
    _tableState.currentPage = 1;
    _rebuildTable();
  });
}

if (_prevBtn) {
  _prevBtn.addEventListener("click", () => _goToPage(_tableState.currentPage - 1));
}

if (_nextBtn) {
  _nextBtn.addEventListener("click", () => _goToPage(_tableState.currentPage + 1));
}

// ---- Uploader ----

initUploader({
  onFileSelected(file) {
    selectedFile = file;
    generateBtn.disabled = false;
    generateBtn.classList.remove("btn-cta--disabled");
  },
  onFileCleared() {
    selectedFile = null;
    generateBtn.disabled = true;
    generateBtn.classList.add("btn-cta--disabled");
    // Full reset only when user explicitly removes the file
    resetUI();
    _tableState.allRows = [];
    _tableState.filtered = [];
    _tableState.currentPage = 1;
    _rebuildTable();
  },
});

// ---- Delete record ----

setDeleteCallback(async (productId) => {
  if (!confirm(`Delete "${productId}" and its media? This cannot be undone.`)) return;

  const user = getUser();

  // Call API — show error and bail if it fails
  let ok = false;
  try {
    const res = await fetch(`/assets/${encodeURIComponent(productId)}`, {
      method: "DELETE",
      headers: user?.id ? { "X-User-Id": user.id } : {},
    });
    ok = res.ok;
    if (!ok) {
      let detail = `Server error ${res.status}`;
      try { const b = await res.json(); detail = b.detail || detail; } catch (_) {}
      showError(`Delete failed: ${detail}`);
      return;
    }
  } catch (err) {
    showError(`Delete failed: ${err.message}`);
    return;
  }

  // Remove from DOM and table state
  removeCard(productId);
  _tableState.allRows = _tableState.allRows.filter((r) => r.productId !== productId);
  _rebuildTable();

  const remaining = _tableState.allRows.length;
  if (remaining > 0) {
    showResults(remaining);
  } else {
    resetUI();
  }
});

// ---- Generate button ----

generateBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  // Soft reset: clear progress/errors only — keep existing table rows so
  // history is preserved and new rows append smoothly below them.
  hideError();
  hideProgress();

  generateBtn.disabled = true;
  generateBtn.classList.add("btn-cta--disabled");
  generateBtn.textContent = "Generating...";

  totalRows = 0;
  doneRows = 0;

  const user = getUser();

  await postCSV(selectedFile, {
    userId: user?.id || "",
    onEvent(eventName, data) {
      handleSSEEvent(eventName, data);
    },
    onError(msg) {
      showError(msg);
      restoreButton();
    },
    onComplete(_data) {
      hideProgress();
      // Show total rows in the table (history + this run)
      showResults(_tableState.allRows.length);
      restoreButton();
    },
  });
});

// ---- Export button ----

if (exportBtn) {
  exportBtn.addEventListener("click", () => {
    const rows = Object.values(_assets);
    if (rows.length === 0) return;

    const headers = [
      "product_id",
      "video_script",
      "voiceover_copy",
      "product_description",
      "image_prompt",
      "video_prompt",
      "hashtags",
      "dam_filename",
      "image_url",
      "video_url",
    ];

    const csvLines = [
      headers.join(","),
      ...rows.map((asset) =>
        headers
          .map((key) => {
            let val = asset[key] ?? "";
            if (Array.isArray(val)) val = val.join("|");
            val = String(val).replace(/"/g, '""');
            return `"${val}"`;
          })
          .join(",")
      ),
    ];

    const blob = new Blob([csvLines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `content-export-${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

// ---- SSE event router ----

function handleSSEEvent(eventName, data) {
  switch (eventName) {
    case "job_started":
      totalRows = data.rows_total ?? 0;
      showProgress(totalRows);
      break;

    case "row_started": {
      const productId = data.product_id;
      const name = data.name || data.product_id;
      // If a row already exists (e.g. loaded from history), remove it first
      // so the live run overwrites it cleanly rather than creating a duplicate id.
      const existingIdx = _tableState.allRows.findIndex((r) => r.productId === productId);
      if (existingIdx !== -1) {
        _tableState.allRows.splice(existingIdx, 1);
        removeCard(productId);
      }
      renderCard(productId, name);
      // Track in table state
      _tableState.allRows.push({ productId, name, receivedAt: Date.now() });
      _rebuildTable();
      break;
    }

    case "row_text_done":
      if (data.asset) {
        updateCardText(data.product_id, data.asset);
        _assets[data.product_id] = Object.assign(_assets[data.product_id] || {}, data.asset);
      }
      break;

    case "row_image_generating":
      // Skeleton already shown — no action needed
      break;

    case "row_image_done":
      updateCardImage(data.product_id, data.image_url || "", data.image_status || "failed");
      break;

    case "row_video_generating":
      // Skeleton already shown — no action needed
      break;

    case "row_video_done":
      updateCardVideo(data.product_id, data.video_url || "", data.video_status || "failed", data.video_error || "");
      break;

    case "row_done":
      doneRows += 1;
      updateProgress(doneRows, totalRows);
      markCardDone(data.product_id);
      // Store the complete final asset (includes image_url, video_url)
      if (data.asset) {
        _assets[data.product_id] = Object.assign(_assets[data.product_id] || {}, data.asset);
      }
      break;

    case "row_error":
      doneRows += 1;
      updateProgress(doneRows, totalRows);
      markCardError(data.product_id, data.error);
      showError(`Error on product ${data.product_id}: ${data.error}`);
      break;

    case "job_complete":
      // Handled by onComplete callback in postCSV
      break;

    default:
      break;
  }
}

// ---- Helpers ----

function restoreButton() {
  generateBtn.disabled = !selectedFile;
  if (selectedFile) generateBtn.classList.remove("btn-cta--disabled");
  generateBtn.textContent = "Generate Content";
}

// ---- Auth ----

// Track sign-in vs sign-up mode on the login page
let _authMode = "signin";

async function _initApp() {
  // Fetch public Supabase config from backend
  let config = null;
  try {
    const res = await fetch("/config");
    if (res.ok) config = await res.json();
  } catch (_) {
    // Backend not running or no config endpoint — skip auth
  }

  const hasSupabase = config?.supabase_url && config?.supabase_anon_key;

  if (hasSupabase) {
    showLoader();
    const user = await initAuth(config);
    onAuthStateChange(_handleAuthChange);
    _handleAuthChange(user);
  } else {
    _hideAuthOverlay();
  }

  // ---- Google SSO button ----
  const googleBtn = document.getElementById("google-signin-btn");
  if (googleBtn) {
    googleBtn.addEventListener("click", () => {
      showLoader();
      signInWithGoogle();
    });
  }

  // ---- Email / password form ----
  const authForm = document.getElementById("auth-form");
  if (authForm) {
    authForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("auth-email")?.value.trim() ?? "";
      const password = document.getElementById("auth-password")?.value ?? "";
      const loginBtn = document.getElementById("login-btn");
      const errorEl = document.getElementById("auth-error");
      const successEl = document.getElementById("auth-success");

      if (!email || !password) {
        _showAuthMsg(errorEl, "Please enter your email address and password.");
        return;
      }

      _hideAuthMsg(errorEl);
      _hideAuthMsg(successEl);
      if (loginBtn) {
        loginBtn.disabled = true;
        loginBtn.textContent = _authMode === "signup" ? "Creating account…" : "Logging in…";
      }

      try {
        if (_authMode === "signup") {
          const { error } = await signUpWithEmail(email, password);
          if (error) {
            _showAuthMsg(errorEl, error);
          } else {
            _showAuthMsg(successEl, "Account created! Check your email to confirm, then log in.");
            _setAuthMode("signin");
          }
        } else {
          const { error } = await signInWithEmail(email, password);
          if (error) {
            _showAuthMsg(errorEl, error);
          }
          // On success the onAuthStateChange callback fires automatically
        }
      } finally {
        if (loginBtn) {
          loginBtn.disabled = false;
          loginBtn.textContent = _authMode === "signup" ? "Sign Up" : "Log In";
        }
      }
    });
  }

  // ---- Toggle sign-in / sign-up ----
  const toggleBtn = document.getElementById("toggle-auth-mode");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      _setAuthMode(_authMode === "signin" ? "signup" : "signin");
    });
  }

  // ---- Password show/hide toggle ----
  const togglePw = document.getElementById("toggle-password");
  if (togglePw) {
    togglePw.addEventListener("click", () => {
      const pwInput = document.getElementById("auth-password");
      if (!pwInput) return;
      const showing = pwInput.type === "text";
      pwInput.type = showing ? "password" : "text";
      togglePw.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      togglePw.innerHTML = showing
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
    });
  }
}

/** Switch the auth overlay between "signin" and "signup" modes. */
function _setAuthMode(mode) {
  _authMode = mode;
  const subtitle  = document.getElementById("auth-mode-subtitle");
  const loginBtn  = document.getElementById("login-btn");
  const toggleBtn = document.getElementById("toggle-auth-mode");
  const promptEl  = document.getElementById("auth-mode-prompt");
  const errorEl   = document.getElementById("auth-error");
  const successEl = document.getElementById("auth-success");

  _hideAuthMsg(errorEl);
  _hideAuthMsg(successEl);

  if (mode === "signup") {
    if (subtitle)   subtitle.textContent  = "Create your account";
    if (loginBtn)   loginBtn.textContent  = "Sign Up";
    if (toggleBtn)  toggleBtn.textContent = "Log in instead";
    if (promptEl)   promptEl.textContent  = "Already have an account?";
  } else {
    if (subtitle)   subtitle.textContent  = "Log in to your account";
    if (loginBtn)   loginBtn.textContent  = "Log In";
    if (toggleBtn)  toggleBtn.textContent = "Create your account";
    if (promptEl)   promptEl.textContent  = "Don't have an account yet?";
  }
}

function _showAuthMsg(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
}

function _hideAuthMsg(el) {
  if (!el) return;
  el.classList.add("hidden");
  el.textContent = "";
}

function _handleAuthChange(user) {
  if (user) {
    hideLoader();
    _hideAuthOverlay();
    _renderUserProfile(user);
    _loadHistory(user.id);
  } else {
    _stopAllMedia();
    showLoader();
    setTimeout(() => {
      hideLoader();
      _showAuthOverlay();
      _clearUserProfile();
      // Clear table so next sign-in starts fresh
      resetUI();
      _tableState.allRows = [];
      _tableState.filtered = [];
      _tableState.currentPage = 1;
    }, 1200);
  }
}

/** Stop lightbox video and any inline detail-panel videos. */
function _stopAllMedia() {
  const lightboxPlayer = document.getElementById("video-lightbox-player");
  if (lightboxPlayer) {
    lightboxPlayer.pause();
    lightboxPlayer.src = "";
  }
  const videoLightbox = document.getElementById("video-lightbox");
  if (videoLightbox) videoLightbox.classList.remove("open");
  document.querySelectorAll(".detail-video").forEach((v) => v.pause());
}

function _showAuthOverlay() {
  const overlay = document.getElementById("auth-overlay");
  if (overlay) overlay.classList.remove("hidden");
}

function _hideAuthOverlay() {
  const overlay = document.getElementById("auth-overlay");
  if (overlay) overlay.classList.add("hidden");
}

let _dropdownOutsideHandler = null;

function _renderUserProfile(user) {
  const profileEl = document.getElementById("user-profile");
  if (!profileEl) return;

  const avatarUrl = user.user_metadata?.avatar_url || "";
  const name      = user.user_metadata?.full_name || user.email?.split("@")[0] || "User";
  const email     = user.email || "";
  const initials  = name.slice(0, 2).toUpperCase();

  const avatarHtml = avatarUrl
    ? `<img class="user-avatar" src="${_esc(avatarUrl)}" alt="${_esc(name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
    : "";
  const initialsHtml = `<div class="user-initials" style="${avatarUrl ? "display:none" : ""}">${_esc(initials)}</div>`;

  profileEl.innerHTML = `
    <div class="user-trigger" id="user-trigger" role="button" tabindex="0" aria-haspopup="true" aria-expanded="false">
      ${avatarHtml}${initialsHtml}
      <span class="user-trigger__name">${_esc(name)}</span>
      <svg class="user-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
    <div class="user-dropdown" id="user-dropdown" role="menu">
      <div class="user-dropdown__header">
        <div class="user-dropdown__email-label">Signed in as</div>
        <div class="user-dropdown__email-value" title="${_esc(email)}">${_esc(email)}</div>
      </div>
      <div class="user-dropdown__actions">
        <button class="user-dropdown__signout" id="signout-btn" role="menuitem">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          Sign out
        </button>
      </div>
    </div>
  `;

  const trigger  = document.getElementById("user-trigger");
  const dropdown = document.getElementById("user-dropdown");

  function _toggleDropdown(e) {
    e.stopPropagation();
    const open = dropdown.classList.toggle("open");
    trigger.setAttribute("aria-expanded", String(open));
    trigger.classList.toggle("open", open);
  }

  trigger.addEventListener("click", _toggleDropdown);
  trigger.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); _toggleDropdown(e); }
  });

  // Remove previous outside-click handler before adding a new one
  if (_dropdownOutsideHandler) {
    document.removeEventListener("click", _dropdownOutsideHandler);
  }
  _dropdownOutsideHandler = () => {
    dropdown.classList.remove("open");
    trigger.classList.remove("open");
    trigger.setAttribute("aria-expanded", "false");
  };
  document.addEventListener("click", _dropdownOutsideHandler);

  document.getElementById("signout-btn").addEventListener("click", async () => {
    await signOut();
  });
}

function _clearUserProfile() {
  const profileEl = document.getElementById("user-profile");
  if (profileEl) profileEl.innerHTML = "";
}

async function _loadHistory(userId) {
  if (!userId) return;
  showLoader();
  try {
    const res = await fetch(`/history?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) { hideLoader(); return; }
    const assets = await res.json();
    if (!Array.isArray(assets) || assets.length === 0) return;

    // De-duplicate: skip product IDs already in the table (live run)
    const existingIds = new Set(_tableState.allRows.map((r) => r.productId));

    let added = 0;
    assets.forEach((asset) => {
      const productId = asset.product_id;
      if (!productId || existingIds.has(productId)) return;

      const name = asset.name || productId;
      const receivedAt = asset.created_at
        ? new Date(asset.created_at).getTime()
        : Date.now() - added * 1000; // stagger to preserve order

      renderCard(productId, name);
      _tableState.allRows.push({ productId, name, receivedAt });
      _assets[productId] = asset;

      if (asset.video_script || asset.product_description) {
        updateCardText(productId, asset);
      }
      const imgStatus = asset.image_status || (asset.image_url ? "done" : "skipped");
      updateCardImage(productId, asset.image_url || "", imgStatus);
      updateCardVideo(productId, asset.video_url || "", asset.video_status || "skipped");
      markCardDone(productId);
      added += 1;
    });

    if (added > 0) {
      _rebuildTable();
      showResults(added);
    }
  } catch (_) {
    // History load is best-effort — don't surface errors to the user
  } finally {
    hideLoader();
  }
}

/** Simple HTML escape for user-supplied strings injected into innerHTML. */
function _esc(str) {
  if (typeof str !== "string") return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Boot
_initApp();

// ---- Experience loader ----

const _QUOTES = [
  { text: "Life is made of moments. We make them extraordinary.", author: "Smartbox" },
  { text: "Because the best gift is always an experience.", author: "Smartbox Mission" },
  { text: "Every journey deserves a story worth telling.", author: "Smartbox" },
  { text: "Creating memories that outlast any material thing.", author: "Smartbox" },
  { text: "The world's greatest gift? The gift of adventure.", author: "Smartbox" },
  { text: "From ordinary days to unforgettable experiences.", author: "Smartbox" },
  { text: "Where data becomes stories, and stories become memories.", author: "Content Engine" },
  { text: "Great content, like great experiences, takes a moment to perfect.", author: "Content Engine" },
  { text: "Turning products into stories that move people.", author: "Content Engine" },
  { text: "Adventure is not a destination — it's a way of living.", author: "Smartbox" },
  { text: "Gifting an experience is gifting a piece of yourself.", author: "Smartbox" },
  { text: "Every experience has a story. We help you tell it.", author: "Content Engine" },
];

let _quoteInterval = null;
let _quoteIndex = Math.floor(Math.random() * _QUOTES.length);

function showLoader() {
  const loader = document.getElementById("page-loader");
  if (!loader) return;
  _showQuote();
  loader.classList.remove("hidden");
  loader.classList.add("page-loader--visible");
  // Cycle quotes every 3.5 s
  _quoteInterval = setInterval(_advanceQuote, 3500);
}

function hideLoader() {
  const loader = document.getElementById("page-loader");
  if (!loader) return;
  loader.classList.remove("page-loader--visible");
  loader.classList.add("page-loader--leaving");
  clearInterval(_quoteInterval);
  _quoteInterval = null;
  setTimeout(() => {
    loader.classList.remove("page-loader--leaving");
    loader.classList.add("hidden");
  }, 500);
}

function _showQuote() {
  const q = _QUOTES[_quoteIndex % _QUOTES.length];
  const textEl = document.getElementById("loader-quote-text");
  const authorEl = document.getElementById("loader-quote-author");
  if (textEl) textEl.textContent = `"${q.text}"`;
  if (authorEl) authorEl.textContent = `— ${q.author}`;
}

function _advanceQuote() {
  _quoteIndex = (_quoteIndex + 1) % _QUOTES.length;
  const textEl = document.getElementById("loader-quote-text");
  const authorEl = document.getElementById("loader-quote-author");
  if (!textEl) return;
  // Fade out → swap → fade in
  textEl.classList.add("quote-fade-out");
  if (authorEl) authorEl.classList.add("quote-fade-out");
  setTimeout(() => {
    _showQuote();
    textEl.classList.remove("quote-fade-out");
    if (authorEl) authorEl.classList.remove("quote-fade-out");
  }, 400);
}
