# Image Compression using K-Means Clustering

A full-stack web application that compresses images using a **custom-built K-Means clustering algorithm** for colour quantisation. The K-Means engine is implemented from scratch using NumPy — no scikit-learn.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-API-000000?logo=flask)
![NumPy](https://img.shields.io/badge/NumPy-Vectorised-013243?logo=numpy)

---

## How It Works

The application reduces the number of distinct colours in an image by grouping similar pixel colours into **k representative centroids** using K-Means clustering. Each pixel is then replaced with its nearest centroid colour, producing a visually similar image with far fewer unique colours — which compresses significantly better.

### K-Means Pipeline

```
Original Image → Reshape to (N, 3) pixels
    → Initialise k centroids (K-Means++ seeding)
    → Iterate:
        → Assign each pixel to nearest centroid (Euclidean distance)
        → Recompute centroids as cluster means
        → Check convergence (centroid shift < tolerance)
    → Replace pixels with centroid colours
    → Reshape back to image
```

### Key Implementation Details

- **K-Means++ Initialisation**: Centroids are seeded proportional to squared distance from existing centroids, avoiding poor random starts
- **Vectorised Distance Computation**: Uses the algebraic expansion `‖a-b‖² = ‖a‖² - 2a·b + ‖b‖²` to avoid creating large intermediate arrays
- **Subsample Strategy**: For images with 500K+ pixels, centroids are discovered on a random subsample and then applied to the full image for speed
- **Empty Cluster Handling**: If a cluster loses all members, it's reinitialised to a random pixel

## Features

- Upload images up to 50 MB (JPEG, PNG, WebP)
- Adjustable compression strength via slider (maps to k = 2–128 colours)
- Draggable before/after comparison viewer
- Download compressed image as JPEG or PNG
- Real-time stats: size reduction %, PSNR, MSE, processing time
- Responsive, premium UI

## Project Structure

```
├── backend/
│   ├── kmeans.py          # Custom K-Means engine (NumPy only)
│   └── app.py             # Flask API server
├── frontend/
│   ├── index.html         # Single-page application
│   ├── style.css          # Styling
│   └── app.js             # Upload, compress, compare, download logic
├── requirements.txt
├── run.py                 # One-command startup
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.8+

### Installation

```bash
git clone https://github.com/hasansaylawala529-bit/kmeans-image-compression.git
cd kmeans-image-compression
pip install -r requirements.txt
```

### Run

```bash
python run.py
```

The app opens at **http://localhost:5000**

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Engine | Custom K-Means (NumPy) |
| Backend | Flask |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Image I/O | Pillow |

## Compression Examples

| Compression | k | Colours | Typical Size Reduction |
|------------|---|---------|----------------------|
| Subtle | 64 | 64 | ~20% |
| Moderate | 16 | 16 | ~60% |
| Aggressive | 4 | 4 | ~85% |

## License

MIT
