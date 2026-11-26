document.addEventListener("DOMContentLoaded", () => {
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
