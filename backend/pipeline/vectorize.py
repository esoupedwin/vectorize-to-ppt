"""
vectorize.py
Extract colour-grouped shape contours from a quantised image.

Key fix for line-art / outlined images
───────────────────────────────────────
Problem: white background and white character-interior share the same K-means
cluster.  If the black outline has even a 1-px gap (JPEG artefact, AA) the two
white regions are ONE connected component → findContours returns one huge shape,
the black silhouette is drawn over it, white interior never reappears.

Fix: before extracting light-colour contours, build a "dark separator" from all
dark K-means colours, dilate it by ~3 px to close hairline gaps, then AND-NOT it
from every light-colour mask.  This forces the interior and background white into
separate connected components regardless of outline quality.

Smoothing pipeline (unchanged from previous version)
─────────────────────────────────────────────────────
1. Gaussian filter (wrap)       – removes pixel-staircase noise
2. Uniform arc-length resample  – evenly-spaced Catmull-Rom anchors
"""

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from typing import List, Tuple

ShapesData = List[Tuple[Tuple[int, int, int], List[List[Tuple[float, float]]]]]

MAX_POINTS = 400
# Luminance below this → colour is treated as a "dark outline"
# 50 catches black/very-dark-gray but not coloured pixels (red lum≈76, etc.)
_DARK_LUM = 50


def _contour_depth(idx: int, hier: np.ndarray) -> int:
    """Walk up the RETR_TREE hierarchy to compute how deep a contour is."""
    depth, parent = 0, hier[0][idx][3]
    while parent != -1:
        depth += 1
        parent = hier[0][parent][3]
    return depth


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lum(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _gaussian_smooth(pts: np.ndarray, sigma: float) -> np.ndarray:
    xs = gaussian_filter1d(pts[:, 0].astype(float), sigma=sigma, mode="wrap")
    ys = gaussian_filter1d(pts[:, 1].astype(float), sigma=sigma, mode="wrap")
    return np.column_stack([xs, ys])


def _resample_uniform(pts: np.ndarray, n: int) -> np.ndarray:
    closed = np.vstack([pts, pts[:1]])
    diffs = np.diff(closed, axis=0)
    seg_len = np.sqrt((diffs ** 2).sum(axis=1))
    cumlen = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cumlen[-1]
    if total < 1e-6:
        return pts[:n] if len(pts) >= n else pts
    t = np.linspace(0.0, total, n, endpoint=False)
    xs = np.interp(t, cumlen, closed[:, 0])
    ys = np.interp(t, cumlen, closed[:, 1])
    return np.column_stack([xs, ys])


def _build_dark_separator(
    quantized_img: np.ndarray,
    centers: np.ndarray,
    h: int,
    w: int,
) -> np.ndarray:
    """
    Union of all dark-colour masks, dilated to close outline gaps.
    Returns a uint8 mask (255 = dark/outline zone, 0 = safe for light regions).
    """
    dark = np.zeros((h, w), dtype=np.uint8)
    for c in centers:
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        if _lum(r, g, b) < _DARK_LUM:
            dark |= cv2.inRange(quantized_img, c, c)

    # Dilate to close outline gaps up to ~4 px wide (JPEG artefacts, AA, etc.)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.dilate(dark, ker, iterations=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_shapes(
    quantized_img: np.ndarray,
    centers: np.ndarray,
    detail_level: float = 0.5,
) -> ShapesData:
    """
    Return (colour, list-of-point-lists) pairs, sorted largest-area-first so
    backgrounds are painted before foreground details.

    detail_level 0–1:
      • target_spacing  6–28 px  (arc-length gap between resampled points)
      • smooth_sigma    1–3.5    (Gaussian σ along the raw contour)
    """
    h, w = quantized_img.shape[:2]
    total_pixels = h * w
    min_area = max(30, total_pixels * 0.0002)

    target_spacing = 6.0 + (1.0 - detail_level) * 22.0
    smooth_sigma   = 1.0 + (1.0 - detail_level) * 2.5

    # ── Dark separator: closes outline gaps so light interiors are isolated ──
    dark_sep = _build_dark_separator(quantized_img, centers, h, w)
    light_ok  = cv2.bitwise_not(dark_sep)   # pixels safe for light-colour masks

    all_shapes: List[Tuple[float, Tuple[int, int, int], list]] = []

    for color in centers:
        r, g, b = int(color[0]), int(color[1]), int(color[2])
        color_tuple = (r, g, b)
        is_dark = _lum(r, g, b) < _DARK_LUM

        mask = cv2.inRange(quantized_img, color, color)

        if not is_dark:
            # Force separation: remove light pixels that are inside the dilated
            # dark zone → background and enclosed interiors become distinct
            # connected components even when the raw outline has tiny gaps.
            mask = cv2.bitwise_and(mask, light_ok)

        if np.count_nonzero(mask) < min_area:
            continue

        # Tiny morphological close: seal hairline gaps within this shape
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ker, iterations=1)

        # RETR_TREE + even-depth filter: captures foreground regions at all
        # nesting levels (depth 0 = outer, depth 2 = island inside a hole,
        # depth 4 = island inside hole inside island, …).
        # RETR_EXTERNAL only returns depth-0 contours, missing "islands"
        # such as the white body enclosed by a black outline ring.
        contours, hier = cv2.findContours(
            mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
        )

        for idx, contour in enumerate(contours):
            if hier is not None and _contour_depth(idx, hier) % 2 != 0:
                continue  # odd depth = hole inside a foreground region
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter < 10:
                continue

            pts_raw    = contour.reshape(-1, 2).astype(float)
            pts_smooth = _gaussian_smooth(pts_raw, sigma=smooth_sigma)
            n_pts      = max(6, min(MAX_POINTS, int(perimeter / target_spacing)))
            pts_final  = _resample_uniform(pts_smooth, n_pts)

            points = [(float(x), float(y)) for x, y in pts_final]
            if len(points) >= 3:
                all_shapes.append((area, color_tuple, points))

    # Sort globally by area descending so large background shapes paint first.
    #
    # IMPORTANT: do NOT group same-colour shapes together.  A black outline
    # ring's outer contour (RETR_TREE depth-0) has a larger reported area than
    # the white interior island (depth-2), so the ring sorts BEFORE the
    # interior — but if we group both whites together the interior gets drawn
    # before the black ring, producing a black silhouette.  Each shape is its
    # own entry so the pptx builder respects the global Z-order.
    all_shapes.sort(key=lambda s: s[0], reverse=True)

    # Each shape is wrapped in a length-1 list so pptx_builder's interface
    # (colour, list-of-contours) still works without changes.
    return [(ct, [pts]) for _, ct, pts in all_shapes]
