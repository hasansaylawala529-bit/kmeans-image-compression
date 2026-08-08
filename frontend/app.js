/* ══════════════════════════════════════════════════════
   Chromatic — App Logic
   Handles upload, compression, comparison, download
   ══════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // ── DOM refs ──────────────────────────────────────

    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");
    const filePreview = document.getElementById("file-preview");
    const previewThumb = document.getElementById("preview-thumb");
    const previewName = document.getElementById("preview-name");
    const previewSize = document.getElementById("preview-size");
    const previewRemove = document.getElementById("preview-remove");

    const controlsSection = document.getElementById("controls-section");
    const compressionSlider = document.getElementById("compression-slider");
    const sliderFill = document.getElementById("slider-fill");
    const sliderValue = document.getElementById("slider-value");
    const kBadge = document.getElementById("k-badge");
    const colourCount = document.getElementById("colour-count");
    const compressBtn = document.getElementById("compress-btn");

    const loadingSection = document.getElementById("loading-section");
    const loadingMessage = document.getElementById("loading-message");

    const resultsSection = document.getElementById("results-section");
    const statReduction = document.getElementById("stat-reduction");
    const statColours = document.getElementById("stat-colours");
    const statPsnr = document.getElementById("stat-psnr");
    const statTime = document.getElementById("stat-time");
    const originalImage = document.getElementById("original-image");
    const compressedImage = document.getElementById("compressed-image");
    const comparisonOverlay = document.getElementById("comparison-overlay");
    const comparisonHandle = document.getElementById("comparison-handle");
    const comparisonViewer = document.getElementById("comparison-viewer");
    const downloadJpgBtn = document.getElementById("download-jpg-btn");
    const downloadPngBtn = document.getElementById("download-png-btn");
    const resetBtn = document.getElementById("reset-btn");

    const errorToast = document.getElementById("error-toast");
    const toastMessage = document.getElementById("toast-message");

    // ── State ─────────────────────────────────────────

    let selectedFile = null;
    let compressedJpgData = null;
    let compressedPngData = null;
    let originalFileName = "";

    // ── Utility ───────────────────────────────────────

    function formatBytes(bytes) {
        if (bytes === 0) return "0 B";
        const units = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + " " + units[i];
    }

    function percentageToK(pct) {
        pct = Math.max(0, Math.min(100, pct));
        if (pct === 0) return 128;
        const ratio = 1.0 - pct / 100.0;
        let k = Math.floor(128 * Math.pow(ratio, 2));
        return Math.max(2, Math.min(128, k));
    }

    function showToast(message, duration) {
        duration = duration || 4000;
        toastMessage.textContent = message;
        errorToast.hidden = false;
        clearTimeout(showToast._timer);
        showToast._timer = setTimeout(function () {
            errorToast.hidden = true;
        }, duration);
    }

    // ── Loading messages ──────────────────────────────

    var loadingMessages = [
        "Clustering pixels…",
        "Finding colour centroids…",
        "Quantising palette…",
        "Crunching numbers…",
        "Optimising clusters…",
        "Reducing colour depth…",
    ];

    function cycleLoadingMessages() {
        var idx = 0;
        return setInterval(function () {
            idx = (idx + 1) % loadingMessages.length;
            loadingMessage.textContent = loadingMessages[idx];
        }, 2200);
    }

    // ── File handling ─────────────────────────────────

    function handleFile(file) {
        if (!file) return;

        // Validate type
        var validTypes = ["image/jpeg", "image/png", "image/webp"];
        if (validTypes.indexOf(file.type) === -1) {
            showToast("Please upload a JPEG, PNG, or WebP image.");
            return;
        }

        // Validate size (50 MB)
        if (file.size > 50 * 1024 * 1024) {
            showToast("File is too large. Maximum size is 50 MB.");
            return;
        }

        selectedFile = file;
        originalFileName = file.name.replace(/\.[^.]+$/, "");

        // Show preview
        var reader = new FileReader();
        reader.onload = function (e) {
            previewThumb.src = e.target.result;
            previewName.textContent = file.name;
            previewSize.textContent = formatBytes(file.size);
            filePreview.hidden = false;
            uploadZone.style.display = "none";

            // Show controls
            controlsSection.hidden = false;
            controlsSection.scrollIntoView({ behavior: "smooth", block: "center" });
        };
        reader.readAsDataURL(file);
    }

    function clearFile() {
        selectedFile = null;
        compressedJpgData = null;
        compressedPngData = null;
        originalFileName = "";
        fileInput.value = "";
        filePreview.hidden = true;
        uploadZone.style.display = "";
        controlsSection.hidden = true;
        loadingSection.hidden = true;
        resultsSection.hidden = true;
    }

    // Upload zone events
    uploadZone.addEventListener("click", function () {
        fileInput.click();
    });

    uploadZone.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInput.click();
        }
    });

    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });

    previewRemove.addEventListener("click", clearFile);

    // Drag and drop
    ["dragenter", "dragover"].forEach(function (evt) {
        uploadZone.addEventListener(evt, function (e) {
            e.preventDefault();
            uploadZone.classList.add("drag-over");
        });
    });

    ["dragleave", "drop"].forEach(function (evt) {
        uploadZone.addEventListener(evt, function (e) {
            e.preventDefault();
            uploadZone.classList.remove("drag-over");
        });
    });

    uploadZone.addEventListener("drop", function (e) {
        var files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // Prevent page-level drop
    document.addEventListener("dragover", function (e) { e.preventDefault(); });
    document.addEventListener("drop", function (e) { e.preventDefault(); });

    // ── Slider ────────────────────────────────────────

    function updateSlider() {
        var val = parseInt(compressionSlider.value, 10);
        var pct = ((val - 5) / (98 - 5)) * 100;
        sliderFill.style.width = pct + "%";
        sliderValue.textContent = val + "%";

        var k = percentageToK(val);
        kBadge.textContent = "k = " + k;
        colourCount.textContent = k;
    }

    compressionSlider.addEventListener("input", updateSlider);
    updateSlider();

    // ── Compress ──────────────────────────────────────

    compressBtn.addEventListener("click", function () {
        if (!selectedFile) {
            showToast("Please select an image first.");
            return;
        }

        var btnText = compressBtn.querySelector(".compress-btn-text");
        var btnLoading = compressBtn.querySelector(".compress-btn-loading");

        // Disable button
        compressBtn.disabled = true;
        btnText.hidden = true;
        btnLoading.hidden = false;

        // Show loading section, hide results
        loadingSection.hidden = false;
        resultsSection.hidden = true;
        loadingSection.scrollIntoView({ behavior: "smooth", block: "center" });

        var messageInterval = cycleLoadingMessages();

        // Build form data
        var formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("compression", compressionSlider.value);

        fetch("/api/compress", {
            method: "POST",
            body: formData,
        })
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (data) {
                        throw new Error(data.error || "Compression failed");
                    });
                }
                return res.json();
            })
            .then(function (data) {
                clearInterval(messageInterval);
                loadingSection.hidden = true;

                // Store data for download
                compressedJpgData = data.compressed_image;
                compressedPngData = data.compressed_png;

                // Populate stats
                var stats = data.stats;
                statReduction.textContent = stats.size_reduction_percent + "%";
                statColours.textContent = stats.k + " colours";
                statPsnr.textContent = stats.psnr;
                statTime.textContent = stats.processing_time + "s";

                // Set images for comparison
                originalImage.src = URL.createObjectURL(selectedFile);
                compressedImage.src = "data:image/jpeg;base64," + data.compressed_image;

                // Wait for images to load, then show results
                var imagesLoaded = 0;
                function onImgLoad() {
                    imagesLoaded++;
                    if (imagesLoaded >= 2) {
                        // Set compressed overlay image width to match container
                        var wrap = document.querySelector(".comparison-image-wrap");
                        compressedImage.style.width = wrap.offsetWidth + "px";

                        resultsSection.hidden = false;
                        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
                        initComparison();
                    }
                }
                originalImage.onload = onImgLoad;
                compressedImage.onload = onImgLoad;

                // Fallback in case images are cached
                if (originalImage.complete) onImgLoad();
                if (compressedImage.complete) onImgLoad();
            })
            .catch(function (err) {
                clearInterval(messageInterval);
                loadingSection.hidden = true;
                showToast(err.message || "Something went wrong. Please try again.");
            })
            .finally(function () {
                compressBtn.disabled = false;
                btnText.hidden = false;
                btnLoading.hidden = true;
            });
    });

    // ── Comparison slider ─────────────────────────────

    function initComparison() {
        var wrap = document.querySelector(".comparison-image-wrap");
        var isDragging = false;

        function setPosition(x) {
            var rect = wrap.getBoundingClientRect();
            var pos = Math.max(0, Math.min(1, (x - rect.left) / rect.width));
            var pct = pos * 100;
            comparisonOverlay.style.width = pct + "%";
            comparisonHandle.style.left = pct + "%";
        }

        function onPointerDown(e) {
            e.preventDefault();
            isDragging = true;
            setPosition(e.clientX || (e.touches && e.touches[0].clientX));
        }

        function onPointerMove(e) {
            if (!isDragging) return;
            e.preventDefault();
            setPosition(e.clientX || (e.touches && e.touches[0].clientX));
        }

        function onPointerUp() {
            isDragging = false;
        }

        // Remove old listeners by cloning
        var newWrap = wrap.cloneNode(true);
        wrap.parentNode.replaceChild(newWrap, wrap);

        // Re-grab references after cloning
        var freshOverlay = newWrap.querySelector(".comparison-overlay");
        var freshHandle = newWrap.querySelector(".comparison-handle");
        var freshOrigImg = newWrap.querySelector("#original-image");
        var freshCompImg = newWrap.querySelector("#compressed-image");

        // Ensure images are still set
        if (freshOrigImg && !freshOrigImg.src) {
            freshOrigImg.src = originalImage.src;
        }
        if (freshCompImg && !freshCompImg.src) {
            freshCompImg.src = compressedImage.src;
        }

        function setPos(x) {
            var rect = newWrap.getBoundingClientRect();
            var pos = Math.max(0, Math.min(1, (x - rect.left) / rect.width));
            var pct = pos * 100;
            freshOverlay.style.width = pct + "%";
            freshHandle.style.left = pct + "%";
        }

        var dragging = false;

        newWrap.addEventListener("mousedown", function (e) {
            e.preventDefault();
            dragging = true;
            setPos(e.clientX);
        });

        document.addEventListener("mousemove", function (e) {
            if (!dragging) return;
            e.preventDefault();
            setPos(e.clientX);
        });

        document.addEventListener("mouseup", function () {
            dragging = false;
        });

        newWrap.addEventListener("touchstart", function (e) {
            dragging = true;
            setPos(e.touches[0].clientX);
        }, { passive: true });

        document.addEventListener("touchmove", function (e) {
            if (!dragging) return;
            setPos(e.touches[0].clientX);
        }, { passive: true });

        document.addEventListener("touchend", function () {
            dragging = false;
        });
    }

    // Handle window resize for comparison image
    window.addEventListener("resize", function () {
        var wrap = document.querySelector(".comparison-image-wrap");
        var img = wrap && wrap.querySelector("#compressed-image");
        if (wrap && img) {
            img.style.width = wrap.offsetWidth + "px";
        }
    });

    // ── Downloads ─────────────────────────────────────

    function downloadBase64(data, filename, mimeType) {
        var byteString = atob(data);
        var ab = new ArrayBuffer(byteString.length);
        var ia = new Uint8Array(ab);
        for (var i = 0; i < byteString.length; i++) {
            ia[i] = byteString.charCodeAt(i);
        }
        var blob = new Blob([ab], { type: mimeType });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    downloadJpgBtn.addEventListener("click", function () {
        if (compressedJpgData) {
            downloadBase64(compressedJpgData, originalFileName + "_compressed.jpg", "image/jpeg");
        }
    });

    downloadPngBtn.addEventListener("click", function () {
        if (compressedPngData) {
            downloadBase64(compressedPngData, originalFileName + "_compressed.png", "image/png");
        }
    });

    // ── Reset ─────────────────────────────────────────

    resetBtn.addEventListener("click", function () {
        clearFile();
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

})();
