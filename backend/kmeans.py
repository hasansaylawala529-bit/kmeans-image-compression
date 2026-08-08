"""
Custom K-Means Clustering for Image Colour Quantisation
========================================================
Implements K-Means from scratch using NumPy.
No scikit-learn dependency — all logic is hand-rolled.
"""

import numpy as np
import time


def initialize_centroids(pixels, k):
    """
    Initialise k centroids using incremental K-Means++ seeding.
    Fast O(N) update per iteration tracking minimum distance so far.
    """
    n_pixels = pixels.shape[0]
    centroids = np.empty((k, 3), dtype=np.float64)

    # First centroid: random pixel
    idx = np.random.randint(0, n_pixels)
    centroids[0] = pixels[idx]

    # Track minimum squared distance from each pixel to any centroid so far
    min_sq_dists = np.sum((pixels - centroids[0]) ** 2, axis=1)

    for i in range(1, k):
        total_dist = min_sq_dists.sum()
        if total_dist > 0:
            probabilities = min_sq_dists / total_dist
        else:
            probabilities = np.ones(n_pixels) / n_pixels

        cumulative = np.cumsum(probabilities)
        r = np.random.random()
        idx = np.searchsorted(cumulative, r)
        idx = min(idx, n_pixels - 1)
        centroids[i] = pixels[idx]

        # Incremental update: update min_sq_dists with distance to the newly picked centroid
        new_dists = np.sum((pixels - centroids[i]) ** 2, axis=1)
        min_sq_dists = np.minimum(min_sq_dists, new_dists)

    return centroids


def assign_clusters(pixels, centroids):
    """
    Assign each pixel to the nearest centroid using Euclidean distance.
    Vectorised matrix dot product formulation.
    """
    pixel_sq = np.sum(pixels ** 2, axis=1, keepdims=True)    # (n, 1)
    centroid_sq = np.sum(centroids ** 2, axis=1, keepdims=True)  # (k, 1)
    cross_term = pixels @ centroids.T                         # (n, k)

    distances = pixel_sq - 2 * cross_term + centroid_sq.T     # (n, k)
    labels = np.argmin(distances, axis=1)
    return labels


def update_centroids(pixels, labels, k):
    """
    Recompute centroids as the mean of all pixels assigned to each cluster.
    """
    new_centroids = np.empty((k, 3), dtype=np.float64)

    for i in range(k):
        mask = labels == i
        if np.any(mask):
            new_centroids[i] = pixels[mask].mean(axis=0)
        else:
            new_centroids[i] = pixels[np.random.randint(0, pixels.shape[0])]

    return new_centroids


def kmeans(pixels, k, max_iters=15, tol=1e-3):
    """
    Run K-Means clustering on pixel data.
    """
    centroids = initialize_centroids(pixels, k)

    for iteration in range(1, max_iters + 1):
        labels = assign_clusters(pixels, centroids)
        new_centroids = update_centroids(pixels, labels, k)

        shift = np.sqrt(np.sum((new_centroids - centroids) ** 2, axis=1)).max()
        centroids = new_centroids

        if shift < tol:
            break

    return centroids, labels, iteration


def compress_image(image_array, k):
    """
    Compress an image using K-Means colour quantisation.
    """
    start_time = time.time()

    h, w, c = image_array.shape
    total_pixels = h * w

    pixels = image_array.reshape(-1, 3).astype(np.float64) / 255.0

    # Subsample threshold for fast centroid discovery (100,000 pixels is plenty for palette learning)
    subsample_threshold = 100_000
    if total_pixels > subsample_threshold:
        indices = np.random.choice(total_pixels, subsample_threshold, replace=False)
        sample = pixels[indices]
        centroids, _, iterations = kmeans(sample, k, max_iters=15)
        labels = assign_clusters(pixels, centroids)
    else:
        centroids, labels, iterations = kmeans(pixels, k, max_iters=15)

    # Reconstruct: replace each pixel with its centroid colour
    compressed_pixels = centroids[labels]

    # Denormalise back to uint8
    compressed = (compressed_pixels * 255.0).clip(0, 255).astype(np.uint8)
    compressed = compressed.reshape(h, w, c)

    elapsed = time.time() - start_time

    mse = calculate_mse(image_array, compressed)

    stats = {
        "k": k,
        "iterations": iterations,
        "mse": round(float(mse), 4),
        "psnr": round(float(calculate_psnr(mse)), 2),
        "original_colours": int(min(len(np.unique(pixels, axis=0)), total_pixels)),
        "compressed_colours": k,
        "processing_time": round(elapsed, 2),
        "resolution": f"{w}x{h}",
        "labels_2d": labels.reshape(h, w).astype(np.uint8),
        "centroids_uint8": (centroids * 255.0).clip(0, 255).astype(np.uint8),
    }

    return compressed, stats


def calculate_mse(original, compressed):
    """
    Compute Mean Squared Error between original and compressed images.

    Parameters
    ----------
    original : np.ndarray, shape (H, W, 3), uint8
    compressed : np.ndarray, shape (H, W, 3), uint8

    Returns
    -------
    mse : float
    """
    diff = original.astype(np.float64) - compressed.astype(np.float64)
    return np.mean(diff ** 2)


def calculate_psnr(mse):
    """
    Compute Peak Signal-to-Noise Ratio from MSE.

    Parameters
    ----------
    mse : float

    Returns
    -------
    psnr : float (in dB)
    """
    if mse == 0:
        return float("inf")
    return 10 * np.log10((255.0 ** 2) / mse)


def percentage_to_k(percentage):
    """
    Map a compression percentage (0–100) to a k value.

    Lower k = more compression = fewer colours.
    The mapping uses exponential interpolation for a more intuitive feel.

    Parameters
    ----------
    percentage : int or float
        Compression strength, 0 (no compression) to 100 (maximum).

    Returns
    -------
    k : int
        Number of colour clusters, range [2, 128].
    """
    # Clamp input
    percentage = max(0, min(100, percentage))

    if percentage == 0:
        return 128

    # Exponential mapping: k = 128 * (1 - p/100)^2, clamped to [2, 128]
    ratio = 1.0 - (percentage / 100.0)
    k = int(128 * (ratio ** 2))
    k = max(2, min(128, k))
    return k
