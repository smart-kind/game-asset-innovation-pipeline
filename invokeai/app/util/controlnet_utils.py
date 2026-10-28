"""The pieces of the retired controlnet preprocessing module that the API-only build still needs.

The torch/cv2 preprocessing functions and the SD-webui controlnet ports were removed with the
local-model stack. What remains is consumed by `invokeai.app.invocations.metadata` (the record
types stored in workflow metadata) and by the image-download endpoint
(`invokeai.app.api.routers.images` resizes downloaded images with `heuristic_resize_fast`).
"""

from typing import Literal

try:
    import cv2
except ImportError:  # API-only build: cv2 ships with the local-model stack and is absent here.
    cv2 = None  # type: ignore[assignment]
import numpy as np

CONTROLNET_RESIZE_VALUES = Literal[
    "just_resize",
    "crop_resize",
    "fill_resize",
    "just_resize_simple",
]
CONTROLNET_MODE_VALUES = Literal["balanced", "more_prompt", "more_control", "unbalanced"]


def heuristic_resize_fast(np_img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    h, w = np_img.shape[:2]
    # early exit
    if (w, h) == size:
        return np_img

    if cv2 is None:
        raise RuntimeError("cv2 is not installed; resized image downloads are unavailable")

    # precomputed here rather than at module scope so the module imports without cv2
    kernel3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dirs = [
        np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0]], np.uint8),
        np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], np.uint8),
        np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.uint8),
        np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], np.uint8),
    ]

    # separate alpha channel
    img = np_img
    alpha = None
    if img.ndim == 3 and img.shape[2] == 4:
        alpha, img = img[:, :, 3], img[:, :, :3]

    # build small sample for unique-color & binary detection
    flat = img.reshape(-1, img.shape[-1])
    N = flat.shape[0]
    # include four corners to avoid missing extreme values
    corners = np.vstack([img[0, 0], img[0, w - 1], img[h - 1, 0], img[h - 1, w - 1]])
    cnt = min(N, 100_000)
    samp = np.vstack([corners, flat[np.random.choice(N, cnt, replace=False)]])
    uc = np.unique(samp, axis=0).shape[0]
    vmin, vmax = samp.min(), samp.max()

    # detect binary edge map & one-pixel-edge case
    is_binary = uc == 2 and vmin < 16 and vmax > 240
    one_pixel_edge = False
    if is_binary:
        # single gray conversion
        gray0 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        grad = cv2.morphologyEx(gray0, cv2.MORPH_GRADIENT, kernel3)
        cnt_edge = cv2.countNonZero(grad)
        cnt_all = cv2.countNonZero((gray0 > 127).astype(np.uint8))
        one_pixel_edge = (2 * cnt_edge) > cnt_all

    # choose interp for color/seg/grayscale
    area_new, area_old = size[0] * size[1], w * h
    if 2 < uc < 200:  # segmentation map
        interp = cv2.INTER_NEAREST
    elif area_new < area_old:
        interp = cv2.INTER_AREA
    else:
        interp = cv2.INTER_CUBIC

    # single resize pass on RGB
    resized = cv2.resize(img, size, interpolation=interp)

    if is_binary:
        # convert to gray & apply NMS via C++ dilate
        gray_r = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        nms = np.zeros_like(gray_r)
        for K in dirs:
            d = cv2.dilate(gray_r, K)
            mask = d == gray_r
            nms[mask] = gray_r[mask]

        # threshold + thinning if needed
        _, bw = cv2.threshold(nms, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        out_bin = cv2.ximgproc.thinning(bw) if one_pixel_edge else bw
        # restore 3 channels
        resized = np.stack([out_bin] * 3, axis=2)

    # restore alpha with same interp as RGB for consistency
    if alpha is not None:
        am = cv2.resize(alpha, size, interpolation=interp)
        am = (am > 127).astype(np.uint8) * 255
        resized = np.dstack((resized, am))

    return resized
