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
    Initialise k centroids by randomly sampling k unique pixels.

    Uses K-Means++ inspired seeding: first centroid is random,
    subsequent centroids are chosen proportional to squared distance
    from the nearest existing centroid. This gives better convergence
    than pure random initialisation.

    Parameters
    ----------
    pixels : np.ndarray, shape (n_pixels, 3)
        Flattened image pixels in RGB.
    k : int
        Number of clusters.

    Returns
    -------
    centroids : np.ndarray, shape (k, 3)
        Initial centroid positions.
    """
    n_pixels = pixels.shape[0]
    centroids = np.empty((k, 3), dtype=np.float64)

    # First centroid: random pixel
    idx = np.random.randint(0, n_pixels)
    centroids[0] = pixels[idx]

    for i in range(1, k):
        # Compute squared distances from each pixel to the nearest centroid so far
        diffs = pixels[:, np.newaxis, :] - centroids[np.newaxis, :i, :]  # (n, i, 3)
        sq_dists = np.sum(diffs ** 2, axis=2)  # (n, i)
        min_sq_dists = np.min(sq_dists, axis=1)  # (n,)

        # Choose next centroid with probability proportional to sq distance
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

    return centroids


def assign_clusters(pixels, centroids):
    """
    Assign each pixel to the nearest centroid using Euclidean distance.

    Parameters
    ----------
    pixels : np.ndarray, shape (n_pixels, 3)
    centroids : np.ndarray, shape (k, 3)

    Returns
    -------
    labels : np.ndarray, shape (n_pixels,)
        Cluster index for each pixel.
    """
    # Vectorised: compute distance from every pixel to every centroid
    # Using the expansion: ||a - b||^2 = ||a||^2 - 2*a·b + ||b||^2
    # This avoids creating a huge (n_pixels, k, 3) intermediate array
    pixel_sq = np.sum(pixels ** 2, axis=1, keepdims=True)    # (n, 1)
    centroid_sq = np.sum(centroids ** 2, axis=1, keepdims=True)  # (k, 1)
    cross_term = pixels @ centroids.T                         # (n, k)

    distances = pixel_sq - 2 * cross_term + centroid_sq.T     # (n, k)
    labels = np.argmin(distances, axis=1)
    return labels


def update_centroids(pixels, labels, k):
    """
    Recompute centroids as the mean of all pixels assigned to each cluster.

    If a cluster has no pixels assigned, reinitialise it to a random pixel.

    Parameters
    ----------
    pixels : np.ndarray, shape (n_pixels, 3)
    labels : np.ndarray, shape (n_pixels,)
    k : int

    Returns
    -------
    new_centroids : np.ndarray, shape (k, 3)
    """
    new_centroids = np.empty((k, 3), dtype=np.float64)

    for i in range(k):
        mask = labels == i
        if np.any(mask):
            new_centroids[i] = pixels[mask].mean(axis=0)
        else:
            # Empty cluster — reinitialise to a random pixel
            new_centroids[i] = pixels[np.random.randint(0, pixels.shape[0])]

    return new_centroids


def kmeans(pixels, k, max_iters=20, tol=1e-4):
    """
    Run K-Means clustering on pixel data.

    Parameters
    ----------
    pixels : np.ndarray, shape (n_pixels, 3)
        Normalised pixel values in [0, 1].
    k : int
        Number of clusters.
    max_iters : int
        Maximum iterations before stopping.
    tol : float
        Convergence tolerance — stop when centroid shift is below this.

    Returns
    -------
    centroids : np.ndarray, shape (k, 3)
        Final centroid positions.
    labels : np.ndarray, shape (n_pixels,)
        Cluster assignment for each pixel.
    iterations : int
        Number of iterations run.
    """
    centroids = initialize_centroids(pixels, k)

    for iteration in range(1, max_iters + 1):
        labels = assign_clusters(pixels, centroids)
        new_centroids = update_centroids(pixels, labels, k)

        # Check convergence: max centroid shift
        shift = np.sqrt(np.sum((new_centroids - centroids) ** 2, axis=1)).max()
        centroids = new_centroids

        if shift < tol:
            break

    return centroids, labels, iteration


def compress_image(image_array, k):
    """
    Compress an image using K-Means colour quantisation.

    Parameters
    ----------
    image_array : np.ndarray, shape (H, W, 3)
        Original image as uint8 RGB array.
    k : int
        Number of colour clusters.

    Returns
    -------
    compressed : np.ndarray, shape (H, W, 3)
        Reconstructed image using only k colours.
    stats : dict
        Compression statistics.
    """
    start_time = time.time()

    h, w, c = image_array.shape
    total_pixels = h * w

    # Normalise to [0, 1] for numerical stability
    pixels = image_array.reshape(-1, 3).astype(np.float64) / 255.0

    # For large images, find centroids on a subsample then apply to all pixels
    subsample_threshold = 500_000  # 500k pixels
    if total_pixels > subsample_threshold:
        # Random subsample for centroid discovery
        indices = np.random.choice(total_pixels, subsample_threshold, replace=False)
        sample = pixels[indices]
        centroids, _, iterations = kmeans(sample, k, max_iters=30)

        # Assign ALL pixels to the discovered centroids
        labels = assign_clusters(pixels, centroids)
    else:
        centroids, labels, iterations = kmeans(pixels, k, max_iters=30)

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
