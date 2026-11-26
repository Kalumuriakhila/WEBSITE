document.addEventListener("DOMContentLoaded", () => {
  // -----------------------------------------------------------------------
  // Mobile navigation toggle
  // -----------------------------------------------------------------------
  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");

  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!expanded));
      navLinks.classList.toggle("open");
    });
  }

  // -----------------------------------------------------------------------
  // Flash messages — auto-dismiss after 5 seconds and manual close
  // -----------------------------------------------------------------------
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    // Manual close button
    const closeBtn = alert.querySelector(".alert-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => dismissAlert(alert));
    }

    // Auto-dismiss after 5 seconds
    setTimeout(() => dismissAlert(alert), 5000);
  });

  function dismissAlert(el) {
    if (el.classList.contains("dismissing")) return;
    el.classList.add("dismissing");
    el.addEventListener("transitionend", () => el.remove(), { once: true });
    // Fallback removal if transitionend doesn't fire
    setTimeout(() => { if (el.parentNode) el.remove(); }, 500);
  }

  // -----------------------------------------------------------------------
  // Drag-and-drop upload zone
  // -----------------------------------------------------------------------
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("videoInput");
  const fileNameLabel = document.getElementById("selectedFileName");
  const uploadForm = document.getElementById("uploadForm");
  const processingBanner = document.getElementById("processingBanner");
  const uploadBtn = document.getElementById("uploadBtn");

  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileNameLabel.textContent = `${file.name} (${sizeMB} MB)`;
      } else {
        fileNameLabel.textContent = "No file chosen";
      }
    });

    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        const file = e.dataTransfer.files[0];
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileNameLabel.textContent = `${file.name} (${sizeMB} MB)`;
      }
    });
  }

  if (uploadForm && processingBanner && uploadBtn) {
    uploadForm.addEventListener("submit", (e) => {
      if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        e.preventDefault();
        alert("Please select a video file first.");
        return;
      }
      processingBanner.classList.add("active");
      uploadBtn.disabled = true;
      uploadBtn.textContent = "Analyzing Video...";
    });
  }
});
