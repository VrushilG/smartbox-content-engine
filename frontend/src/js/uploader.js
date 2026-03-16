/**
 * uploader.js — drag-drop CSV handler and file validation
 *
 * Responsibilities:
 * - Handles drag-and-drop and click-to-browse on the drop zone
 * - Validates that the selected file is a .csv
 * - Calls an onFileSelected(file) callback when a valid file is chosen
 * - Calls onFileCleared() when the file is removed
 */

const ACCEPTED_MIME = ["text/csv", "application/vnd.ms-excel"];

export function initUploader({ onFileSelected, onFileCleared }) {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileInfo = document.getElementById("file-info");
  const fileName = document.getElementById("file-name");
  const clearBtn = document.getElementById("clear-file");

  // ---- Drag events ----

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drop-zone--active");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drop-zone--active");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drop-zone--active");
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  });

  // ---- Keyboard accessibility ----

  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  // ---- Native file input ----

  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (file) handleFile(file);
  });

  // ---- Clear selection ----

  clearBtn.addEventListener("click", () => {
    fileInput.value = "";
    fileInfo.classList.add("hidden");
    dropZone.classList.remove("hidden");
    onFileCleared();
  });

  // ---- Validation & callback ----

  function handleFile(file) {
    if (!isValidCsv(file)) {
      alert("Please select a .csv file.");
      return;
    }
    fileName.textContent = file.name;
    fileInfo.classList.remove("hidden");
    onFileSelected(file);
  }

  function isValidCsv(file) {
    const byExtension = file.name.toLowerCase().endsWith(".csv");
    const byMime = !file.type || ACCEPTED_MIME.includes(file.type);
    return byExtension || byMime;
  }
}
