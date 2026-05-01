import io
import cv2
import numpy as np
from PIL import Image


def preprocess_image(image_bytes: bytes, n_colors: int = 8):
    """
    Load image, composite alpha on white, resize if huge, quantize to n_colors.
    Returns (quantized_rgb_array, height, width, color_centers).
    """
    img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    # Composite on white background to handle PNG transparency
    background = Image.new("RGBA", img_pil.size, (255, 255, 255, 255))
    background.paste(img_pil, mask=img_pil.split()[3])
    img_rgb = background.convert("RGB")

    # Resize if too large — keeps processing fast
    max_dim = 1200
    w, h = img_rgb.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img_rgb = img_rgb.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    img_array = np.array(img_rgb)
    h, w = img_array.shape[:2]

    n_colors = max(2, min(24, n_colors))

    # K-means colour quantisation
    data = img_array.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
    _, labels, centers = cv2.kmeans(
        data, n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS
    )
    centers = np.round(centers).clip(0, 255).astype(np.uint8)
    quantized = centers[labels.flatten()].reshape(img_array.shape)

    return quantized, h, w, centers
