/**
 * ui.js — renders result table rows, progress bars, and status updates
 *
 * Responsibilities:
 * - renderCard(productId, name): create a skeleton loading row in the results tbody
 * - updateCardText(productId, asset): fill in the row with text content after row_text_done
 * - updateCardImage(productId, imageUrl, status): update the thumbnail cell
 * - updateCardVideo(productId, videoUrl, status): update the video status badge
 * - markCardDone(productId): mark row done
 * - markCardError(productId, errorMsg): mark the row with an error state
 * - updateProgress(done, total): update the progress bar and text
 * - showError(msg): display the error banner
 * - hideError(): hide the error banner
 * - showResults(count): make the results section visible
 * - showProgress(total): make the progress section visible
 * - hideProgress(): hide the progress section
 * - resetUI(): return UI to initial state
 *
 * Module-level asset store:
 * - _assets: map of product_id -> asset data (for CSV export)
 */

const progressSection = document.getElementById("progress-section");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");
const errorBanner = document.getElementById("error-banner");
const resultsSection = document.getElementById("results-section");
const resultsTbody = document.getElementById("results-tbody");
const resultsCount = document.getElementById("results-count");

// ---- Asset store (used by CSV export in app.js) ----
export const _assets = {};

// ---- Delete callback (set by app.js) ----
let _onDeleteCallback = null;
export function setDeleteCallback(fn) {
  _onDeleteCallback = fn;
}

/**
 * Remove a product row (and its detail row) from the DOM and asset store.
 */
export function removeCard(productId) {
  document.getElementById(`row-${productId}`)?.remove();
  document.getElementById(`row-detail-${productId}`)?.remove();
  delete _assets[productId];
}

// ---- Progress ----

export function showProgress(total) {
  progressText.textContent = `0 of ${total} products processed`;
  progressFill.style.width = "0%";
  progressSection.classList.remove("hidden");
}

export function updateProgress(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  progressFill.style.width = `${pct}%`;
  progressFill.closest("[role='progressbar']").setAttribute("aria-valuenow", pct);
  progressText.textContent = `${done} of ${total} products processed`;
}

export function hideProgress() {
  progressSection.classList.add("hidden");
}

// ---- Results ----

export function showResults(count) {
  resultsCount.textContent = `${count} asset${count !== 1 ? "s" : ""} generated`;
  resultsSection.classList.remove("hidden");
}

/**
 * Create a skeleton loading row for a product.
 * The row is progressively populated as SSE events arrive.
 */
export function renderCard(productId, name) {
  // Show results section as soon as first row appears
  resultsSection.classList.remove("hidden");

  // Main row
  const tr = document.createElement("tr");
  tr.id = `row-${productId}`;
  tr.setAttribute("data-received", String(Date.now()));
  tr.innerHTML = `
    <td class="col-thumb"><div class="thumb-skeleton"></div></td>
    <td class="col-id"><span class="id-badge">${escapeHtml(String(productId))}</span></td>
    <td class="col-name">${escapeHtml(name)}</td>
    <td class="col-desc"><span class="desc-preview">Generating content...</span></td>
    <td class="col-status"><span class="status-badge status-badge--loading">&#9679; Loading</span></td>
    <td class="col-actions"></td>
  `;
  resultsTbody.appendChild(tr);

  // Detail row (hidden by default)
  const detailTr = document.createElement("tr");
  detailTr.className = "row-detail";
  detailTr.id = `row-detail-${productId}`;
  detailTr.innerHTML = `<td colspan="6"></td>`;
  resultsTbody.appendChild(detailTr);

  // Initialise asset store entry
  _assets[productId] = { product_id: productId, name };
}

/**
 * Fill the row with generated text content (after row_text_done).
 * Also populates the expandable detail panel.
 */
export function updateCardText(productId, asset) {
  const tr = document.getElementById(`row-${productId}`);
  if (!tr) return;

  // Merge into asset store
  _assets[productId] = Object.assign(_assets[productId] || {}, asset);

  // Description preview (product_description preferred, fall back to video_script)
  const descText = asset.product_description || asset.video_script || "";
  const descPreview = descText.length > 120 ? descText.slice(0, 120) + "…" : descText;

  const hashtagItems = (asset.hashtags || [])
    .map((tag) => `<span class="hashtag-pill">#${escapeHtml(tag)}</span>`)
    .join("");

  // Update main row cells
  tr.querySelector(".col-desc .desc-preview").textContent = descPreview;
  tr.querySelector(".col-status").innerHTML = `<span class="status-badge status-badge--loading">&#9679; Generating</span>`;

  // Add expand + delete buttons (wrapped in a div so the td keeps normal table flow)
  const actionsCell = tr.querySelector(".col-actions");
  actionsCell.innerHTML = `
    <div class="actions-wrap">
      <button class="expand-btn" aria-label="Expand details" data-product-id="${escapeHtml(String(productId))}">&#9660;</button>
      <button class="delete-btn" aria-label="Delete record" data-product-id="${escapeHtml(String(productId))}" title="Delete this record">&#128465;</button>
    </div>
  `;
  actionsCell.querySelector(".expand-btn").addEventListener("click", () => _toggleDetail(productId));
  actionsCell.querySelector(".delete-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    _onDeleteCallback && _onDeleteCallback(productId);
  });

  // Populate detail panel
  const detailTr = document.getElementById(`row-detail-${productId}`);
  if (detailTr) {
    detailTr.querySelector("td").innerHTML = `
      <div class="detail-grid">
        <div class="detail-block detail-block--full">
          <div class="detail-section__label">Product Description</div>
          <div class="detail-section__content">${escapeHtml(asset.product_description || "")}</div>
        </div>
        <div class="detail-block detail-block--full">
          <div class="detail-section__label">Video Script</div>
          <div class="detail-section__content">${escapeHtml(asset.video_script || "")}</div>
        </div>
        <div class="detail-block detail-block--full">
          <div class="detail-section__label">Voiceover Copy</div>
          <div class="detail-section__content">${escapeHtml(asset.voiceover_copy || "")}</div>
        </div>
        <div class="detail-block">
          <div class="detail-section__label">Image Prompt</div>
          <div class="detail-section__content">${escapeHtml(asset.image_prompt || "")}</div>
        </div>
        <div class="detail-block">
          <div class="detail-section__label">Video Prompt</div>
          <div class="detail-section__content">${escapeHtml(asset.video_prompt || "")}</div>
        </div>
        <div class="detail-block">
          <div class="detail-section__label">Hashtags</div>
          <div class="detail-hashtags">${hashtagItems}</div>
        </div>
        <div class="detail-block">
          <div class="detail-section__label">DAM Filename</div>
          <div class="detail-section__content"><span class="dam-code">${escapeHtml(asset.dam_filename || "")}</span></div>
        </div>
        <div id="detail-video-${productId}" class="detail-block">
          <div class="detail-section__label">Video</div>
          <div class="detail-section__content">Generating...</div>
        </div>
      </div>
    `;
  }
}

/**
 * Update the thumbnail cell with the generated image (after row_image_done).
 */
export function updateCardImage(productId, imageUrl, status) {
  const tr = document.getElementById(`row-${productId}`);
  if (!tr) return;

  const thumbCell = tr.querySelector(".col-thumb");

  // Persist to asset store
  if (_assets[productId]) {
    _assets[productId].image_url = imageUrl;
    _assets[productId].image_status = status;
  }

  if (status === "done" && imageUrl) {
    const img = document.createElement("img");
    img.src = imageUrl;
    img.className = "row-thumb";
    img.alt = `Product ${productId}`;
    img.loading = "lazy";
    img.title = "Click to preview";
    img.onerror = () => {
      wrapper.replaceWith(_thumbFailed());
    };
    img.addEventListener("click", () => _openLightbox(imageUrl, `Product ${productId}`));

    // Download button overlaid on thumbnail
    const dlBtn = document.createElement("button");
    dlBtn.className = "thumb-download-btn";
    dlBtn.title = "Download image";
    dlBtn.setAttribute("aria-label", "Download image");
    dlBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;
    dlBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      _downloadFile(imageUrl, `product-${productId}.jpg`);
    });

    const wrapper = document.createElement("div");
    wrapper.className = "thumb-wrap";
    wrapper.appendChild(img);
    wrapper.appendChild(dlBtn);

    thumbCell.innerHTML = "";
    thumbCell.appendChild(wrapper);
  } else {
    thumbCell.innerHTML = "";
    thumbCell.appendChild(_thumbFailed());
  }
}

/**
 * Update the video status in the detail panel and add a play-badge to the
 * thumbnail cell (after row_video_done).
 */
export function updateCardVideo(productId, videoUrl, status, errorReason = "") {
  const tr = document.getElementById(`row-${productId}`);
  if (!tr) return;

  // Persist to asset store
  if (_assets[productId]) {
    _assets[productId].video_url = videoUrl;
    _assets[productId].video_status = status;
  }

  // ---- Thumbnail cell: add play-badge overlay ----
  if (status === "done" && videoUrl) {
    const thumbCell = tr.querySelector(".col-thumb");
    if (thumbCell) {
      // Add a play badge onto the existing thumb-wrap (or create one)
      let wrap = thumbCell.querySelector(".thumb-wrap");
      if (!wrap) {
        // No image: create a video-only placeholder
        wrap = document.createElement("div");
        wrap.className = "thumb-wrap thumb-wrap--video-only";
        thumbCell.innerHTML = "";
        thumbCell.appendChild(wrap);
      }
      // Remove any existing badge before re-adding
      wrap.querySelector(".thumb-play-btn")?.remove();
      const playBtn = document.createElement("button");
      playBtn.className = "thumb-play-btn";
      playBtn.title = "Preview video";
      playBtn.setAttribute("aria-label", "Preview video");
      playBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
      playBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        _openVideoLightbox(videoUrl, `video-${productId}.mp4`);
      });
      wrap.appendChild(playBtn);
    }
  }

  // ---- Detail panel: full video player ----
  const detailVideoEl = document.getElementById(`detail-video-${productId}`);
  if (detailVideoEl) {
    if (status === "done" && videoUrl) {
      detailVideoEl.innerHTML = `
        <div class="detail-section__label">Video</div>
        <video class="detail-video" src="${escapeHtml(videoUrl)}" controls loop playsinline></video>
        <div class="detail-video-actions">
          <button class="btn-download-media" data-url="${escapeHtml(videoUrl)}" data-filename="video-${escapeHtml(String(productId))}.mp4">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Download
          </button>
          <button class="btn-preview-video" data-url="${escapeHtml(videoUrl)}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Full preview
          </button>
        </div>
      `;
      detailVideoEl.querySelector(".btn-download-media").addEventListener("click", (e) => {
        const btn = e.currentTarget;
        _downloadFile(btn.dataset.url, btn.dataset.filename);
      });
      detailVideoEl.querySelector(".btn-preview-video").addEventListener("click", (e) => {
        _openVideoLightbox(e.currentTarget.dataset.url, `video-${productId}.mp4`);
      });
    } else {
      let msg = status === "skipped"
        ? "Video generation skipped — add GOOGLE_API_KEY to enable"
        : "Video generation failed";
      if (status === "failed" && errorReason) msg += ` — ${errorReason}`;
      detailVideoEl.innerHTML = `
        <div class="detail-section__label">Video</div>
        <div class="detail-section__content" style="color:var(--color-text-muted);font-style:italic">${escapeHtml(msg)}</div>
      `;
    }
  }
}

/**
 * Update the status badge to "done" (called on row_done).
 */
export function markCardDone(productId) {
  const tr = document.getElementById(`row-${productId}`);
  if (!tr) return;
  tr.querySelector(".col-status").innerHTML = `<span class="status-badge status-badge--done">&#10003; Done</span>`;
}

/**
 * Mark a row as failed (after row_error).
 */
export function markCardError(productId, errorMsg) {
  const tr = document.getElementById(`row-${productId}`);
  if (!tr) return;
  tr.querySelector(".col-status").innerHTML = `<span class="status-badge status-badge--error">&#10007; Error</span>`;

  const detailTr = document.getElementById(`row-detail-${productId}`);
  if (detailTr) {
    detailTr.querySelector("td").innerHTML = `
      <div class="detail-block">
        <div class="detail-section__label" style="color:var(--color-error)">Error</div>
        <div class="detail-section__content">${escapeHtml(errorMsg)}</div>
      </div>
    `;
  }

  // Ensure expand + delete buttons exist for error rows
  const actionsCell = tr.querySelector(".col-actions");
  if (!actionsCell.querySelector(".expand-btn")) {
    actionsCell.innerHTML = `
      <div class="actions-wrap">
        <button class="expand-btn" aria-label="Expand details" data-product-id="${escapeHtml(String(productId))}">&#9660;</button>
        <button class="delete-btn" aria-label="Delete record" data-product-id="${escapeHtml(String(productId))}" title="Delete this record">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        </button>
      </div>
    `;
    actionsCell.querySelector(".expand-btn").addEventListener("click", () => _toggleDetail(productId));
    actionsCell.querySelector(".delete-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      _onDeleteCallback && _onDeleteCallback(productId);
    });
  }
}

// ---- Errors ----

export function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.classList.remove("hidden");
}

export function hideError() {
  errorBanner.classList.add("hidden");
  errorBanner.textContent = "";
}

// ---- Reset ----

export function resetUI() {
  hideError();
  hideProgress();
  resultsSection.classList.add("hidden");
  if (resultsTbody) resultsTbody.innerHTML = "";
  resultsCount.textContent = "";
  // Clear asset store
  for (const key of Object.keys(_assets)) {
    delete _assets[key];
  }
}

// ---- Image Lightbox ----

const _lightbox = document.getElementById("lightbox");
const _lightboxImg = document.getElementById("lightbox-img");
const _lightboxClose = document.getElementById("lightbox-close");

// ---- Video Lightbox ----

const _videoLightbox = document.getElementById("video-lightbox");
const _videoLightboxPlayer = document.getElementById("video-lightbox-player");
const _videoLightboxClose = document.getElementById("video-lightbox-close");
const _videoLightboxDl = document.getElementById("video-lightbox-dl");

function _openVideoLightbox(src, filename) {
  if (!_videoLightbox || !_videoLightboxPlayer) return;
  _videoLightboxPlayer.src = src;
  if (_videoLightboxDl) {
    _videoLightboxDl.onclick = () => _downloadFile(src, filename || "video.mp4");
  }
  _videoLightbox.classList.add("open");
  _videoLightboxPlayer.play().catch(() => {});
}

function _closeVideoLightbox() {
  if (!_videoLightbox || !_videoLightboxPlayer) return;
  _videoLightboxPlayer.pause();
  _videoLightboxPlayer.src = "";
  _videoLightbox.classList.remove("open");
}

if (_videoLightboxClose) {
  _videoLightboxClose.addEventListener("click", _closeVideoLightbox);
}
if (_videoLightbox) {
  _videoLightbox.addEventListener("click", (e) => {
    if (e.target === _videoLightbox) _closeVideoLightbox();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _closeVideoLightbox();
  });
}

const _lightboxDl = document.getElementById("lightbox-dl");

function _openLightbox(src, alt) {
  _lightboxImg.src = src;
  _lightboxImg.alt = alt || "Full size image";
  if (_lightboxDl) {
    _lightboxDl.onclick = () => _downloadFile(src, `${(alt || "image").replace(/\s+/g, "-").toLowerCase()}.jpg`);
  }
  _lightbox.classList.add("open");
}

if (_lightboxClose) {
  _lightboxClose.addEventListener("click", () => _lightbox.classList.remove("open"));
}
if (_lightbox) {
  _lightbox.addEventListener("click", (e) => {
    if (e.target === _lightbox) _lightbox.classList.remove("open");
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _lightbox.classList.remove("open");
  });
}

// ---- Private helpers ----

/**
 * Download a file. Uses fetch+blob for same-origin URLs; falls back to
 * opening a new tab for cross-origin resources where CORS may block the blob approach.
 */
async function _downloadFile(url, filename) {
  if (!url) return;
  try {
    const res = await fetch(url, { mode: "cors" });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  } catch (_) {
    // CORS blocked — open in new tab so user can save manually
    window.open(url, "_blank", "noopener");
  }
}

function _thumbFailed() {
  const div = document.createElement("div");
  div.className = "thumb-failed";
  div.textContent = "N/A";
  return div;
}

function _toggleDetail(productId) {
  const detailTr = document.getElementById(`row-detail-${productId}`);
  const btn = document.querySelector(`[data-product-id="${productId}"].expand-btn`);
  if (!detailTr) return;
  const isOpen = detailTr.classList.toggle("open");
  if (btn) btn.innerHTML = isOpen ? "&#9650;" : "&#9660;";
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
