"""
Flask API for K-Means Image Compression
=========================================
Handles image upload, compression via custom K-Means, and result delivery.
"""

import os
import io
import base64
import sys

from flask import Flask, request, jsonify, send_from_directory
from PIL import Image
import numpy as np

# Add parent to path so we can import from backend package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kmeans import compress_image, percentage_to_k

app = Flask(__name__, static_folder=None)

# 50 MB upload limit
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# Paths
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


# ── Static file serving ──────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ── API endpoints ────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/compress", methods=["POST"])
def compress():
    """
    Compress an uploaded image using K-Means colour quantisation.

    Expects multipart form data:
        - file: image file (JPEG, PNG, WebP)
        - compression: int 0-100 (compression strength percentage)

    Returns JSON:
        - compressed_image: base64-encoded JPEG
        - stats: compression statistics
    """
    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate compression parameter
    try:
        compression = int(request.form.get("compression", 50))
        compression = max(0, min(100, compression))
    except (ValueError, TypeError):
        compression = 50

    # Read and validate image
    try:
        image = Image.open(file.stream)
        # Convert to RGB if necessary (handles RGBA, palette, grayscale)
        if image.mode != "RGB":
            image = image.convert("RGB")
    except Exception:
        return jsonify({"error": "Invalid image file. Please upload a JPEG, PNG, or WebP image."}), 400

    # Get original file size
    file.stream.seek(0)
    original_bytes = len(file.stream.read())

    # Convert to numpy array
    image_array = np.array(image)

    # Map compression percentage to k
    k = percentage_to_k(compression)

    # Run K-Means compression
    try:
        compressed_array, stats = compress_image(image_array, k)
    except Exception as e:
        return jsonify({"error": f"Compression failed: {str(e)}"}), 500

    # Convert compressed array back to image
    compressed_image = Image.fromarray(compressed_array)

    # Encode as JPEG with optimal Huffman tables and calibrated quality curve
    jpeg_quality = max(45, 85 - int(compression * 0.4))

    buffer = io.BytesIO()
    compressed_image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
    compressed_bytes = buffer.getvalue()

    # If JPEG re-encode is larger than original input, dynamically lower quality to guarantee size reduction
    while len(compressed_bytes) >= original_bytes and jpeg_quality > 35:
        jpeg_quality -= 10
        buffer = io.BytesIO()
        compressed_image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        compressed_bytes = buffer.getvalue()

    compressed_b64 = base64.b64encode(compressed_bytes).decode("utf-8")

    # Extract labels and centroids for direct PNG palette creation
    labels_2d = stats.pop("labels_2d", None)
    centroids_uint8 = stats.pop("centroids_uint8", None)

    # Create an optimized 1-channel Indexed Palette PNG using exact K-Means centroids
    png_buffer = io.BytesIO()
    if labels_2d is not None and centroids_uint8 is not None:
        try:
            png_img = Image.fromarray(labels_2d, mode="P")
            palette_bytes = np.zeros((256, 3), dtype=np.uint8)
            palette_bytes[:len(centroids_uint8)] = centroids_uint8
            png_img.putpalette(palette_bytes.tobytes())
            png_img.save(png_buffer, format="PNG", optimize=True)
        except Exception:
            compressed_image.save(png_buffer, format="PNG", optimize=True)
    else:
        compressed_image.save(png_buffer, format="PNG", optimize=True)

    png_bytes = png_buffer.getvalue()
    png_b64 = base64.b64encode(png_bytes).decode("utf-8")

    # Compute effective size reduction based on smallest output option
    effective_bytes = min(len(compressed_bytes), len(png_bytes))
    size_reduction = max(0.0, round((1 - effective_bytes / original_bytes) * 100, 1))

    # Add file size stats
    stats["original_size_bytes"] = original_bytes
    stats["compressed_size_bytes"] = len(compressed_bytes)
    stats["png_size_bytes"] = len(png_bytes)
    stats["size_reduction_percent"] = size_reduction

    return jsonify({
        "compressed_image": compressed_b64,
        "compressed_png": png_b64,
        "stats": stats,
    })


# ── Error handlers ───────────────────────────────────────────────────

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 50 MB."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)
