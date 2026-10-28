from math import pi as PI

import numpy as np

MAX_FLOAT = np.finfo(np.float32).max
_SRGB_TO_LINEAR_THRESHOLD = 0.0404482362771082
_LINEAR_TO_SRGB_THRESHOLD = 0.0031308
_SRGB_TO_XYZ_D65_MATRIX = (
    (0.4124, 0.3576, 0.1805),
    (0.2126, 0.7152, 0.0722),
    (0.0193, 0.1192, 0.9505),
)
_XYZ_D65_TO_SRGB_MATRIX = (
    (3.2406255, -1.5372080, -0.4986286),
    (-0.9689307, 1.8757561, 0.0415175),
    (0.0557101, -0.2040211, 1.0569959),
)
_BRADFORD_MATRIX = (
    (0.8951, 0.2664, -0.1614),
    (-0.7502, 1.7135, 0.0367),
    (0.0389, -0.0685, 1.0296),
)
_BRADFORD_INVERSE_MATRIX = (
    (0.9869929, -0.1470543, 0.1599627),
    (0.4323053, 0.5183603, 0.0492912),
    (-0.0085287, 0.0400428, 0.9684867),
)
_REFERENCE_ILLUMINANTS = {
    "D65": (0.950489, 1.0, 1.088840),
    "D50": (0.964212, 1.0, 0.825188),
}
_LINEAR_SRGB_TO_OKLAB_LMS_MATRIX = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)
_LMS_CUBE_ROOT_TO_OKLAB_MATRIX = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)
_OKLAB_TO_LMS_CUBE_ROOT_MATRIX = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480),
)
_LMS_TO_LINEAR_SRGB_MATRIX = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)


def _require_color_array(color_array: np.ndarray) -> np.ndarray:
    if color_array.ndim != 3 or color_array.shape[0] != 3:
        raise ValueError("color_array must be a 3xHxW array")
    return color_array


def _require_reference_illuminant(reference_illuminant: str) -> str:
    normalized = reference_illuminant.upper()
    if normalized not in _REFERENCE_ILLUMINANTS:
        raise ValueError(f"Unsupported reference_illuminant: {reference_illuminant}")
    return normalized


def _full_like_spatial(reference_array: np.ndarray, fill_value: float) -> np.ndarray:
    return np.full(reference_array.shape[1:], fill_value, dtype=reference_array.dtype)


def _degrees_from_unit_hue(unit_hue_array: np.ndarray) -> np.ndarray:
    return np.remainder(unit_hue_array * 360.0, 360.0)


def _unit_hue_from_degrees(hue_array: np.ndarray) -> np.ndarray:
    return np.remainder(hue_array, 360.0) / 360.0


def _matrix_tensor(matrix: tuple[tuple[float, ...], ...], reference_array: np.ndarray) -> np.ndarray:
    return np.array(matrix, dtype=reference_array.dtype)


def _apply_matrix(matrix: tuple[tuple[float, ...], ...], color_array: np.ndarray) -> np.ndarray:
    return np.einsum("rc,cwh->rwh", _matrix_tensor(matrix, color_array), color_array)


def _reference_white_tensor(reference_illuminant: str, reference_array: np.ndarray) -> np.ndarray:
    return np.array(_REFERENCE_ILLUMINANTS[reference_illuminant], dtype=reference_array.dtype).reshape(3, 1, 1)


def _adapt_xyz(xyz_array: np.ndarray, source_illuminant: str, target_illuminant: str) -> np.ndarray:
    xyz_array = _require_color_array(xyz_array)
    source_illuminant = _require_reference_illuminant(source_illuminant)
    target_illuminant = _require_reference_illuminant(target_illuminant)
    if source_illuminant == target_illuminant:
        return xyz_array
    source_white_lms = _apply_matrix(_BRADFORD_MATRIX, _reference_white_tensor(source_illuminant, xyz_array))
    target_white_lms = _apply_matrix(_BRADFORD_MATRIX, _reference_white_tensor(target_illuminant, xyz_array))
    xyz_lms = _apply_matrix(_BRADFORD_MATRIX, xyz_array)
    adapted_lms = xyz_lms * (target_white_lms / source_white_lms)
    return _apply_matrix(_BRADFORD_INVERSE_MATRIX, adapted_lms)


def srgb_from_linear_srgb(linear_srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW linear-light sRGB array in [0, 1] to gamma-corrected sRGB."""

    linear_srgb_array = _require_color_array(linear_srgb_array)
    linear_srgb_array = np.clip(linear_srgb_array, 0.0, 1.0)
    return np.where(
        linear_srgb_array <= _LINEAR_TO_SRGB_THRESHOLD,
        linear_srgb_array * 12.92,
        1.055 * np.power(linear_srgb_array, 1.0 / 2.4) - 0.055,
    )


def linear_srgb_from_srgb(srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array in [0, 1] to linear-light sRGB."""

    srgb_array = _require_color_array(srgb_array)
    return np.where(
        srgb_array <= _SRGB_TO_LINEAR_THRESHOLD,
        srgb_array / 12.92,
        np.power((srgb_array + 0.055) / 1.055, 2.4),
    )


def xyz_from_linear_srgb(linear_srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW linear-light sRGB array to normalized XYZ, where D65 white is approximately 1.0."""

    linear_srgb_array = _require_color_array(linear_srgb_array)
    return _apply_matrix(_SRGB_TO_XYZ_D65_MATRIX, linear_srgb_array)


def linear_srgb_from_xyz(xyz_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW normalized XYZ array, where D65 white is approximately 1.0, to linear-light sRGB."""

    xyz_array = _require_color_array(xyz_array)
    return _apply_matrix(_XYZ_D65_TO_SRGB_MATRIX, xyz_array)


def xyz_from_srgb(srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array to normalized XYZ, where D65 white is approximately 1.0."""

    srgb_array = _require_color_array(srgb_array)
    return xyz_from_linear_srgb(linear_srgb_from_srgb(srgb_array))


def srgb_from_xyz(xyz_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW normalized XYZ array, where D65 white is approximately 1.0, to gamma-corrected sRGB."""

    xyz_array = _require_color_array(xyz_array)
    return srgb_from_linear_srgb(linear_srgb_from_xyz(xyz_array))


def xyz_d65_to_d50(xyz_array: np.ndarray) -> np.ndarray:
    """Adapt a 3xHxW normalized XYZ array from D65 to D50 using Bradford chromatic adaptation."""

    return _adapt_xyz(xyz_array, source_illuminant="D65", target_illuminant="D50")


def xyz_d50_to_d65(xyz_array: np.ndarray) -> np.ndarray:
    """Adapt a 3xHxW normalized XYZ array from D50 to D65 using Bradford chromatic adaptation."""

    return _adapt_xyz(xyz_array, source_illuminant="D50", target_illuminant="D65")


def _lab_from_xyz_helper(channel_illuminant_quotient_array: np.ndarray) -> np.ndarray:
    delta = 6.0 / 29.0
    return np.where(
        channel_illuminant_quotient_array > delta**3.0,
        np.power(channel_illuminant_quotient_array, 1.0 / 3.0),
        channel_illuminant_quotient_array / (3.0 * (delta**2.0)) + 4.0 / 29.0,
    )


def _xyz_from_lab_helper(channel_array: np.ndarray) -> np.ndarray:
    delta = 6.0 / 29.0
    return np.where(
        channel_array > delta,
        np.power(channel_array, 3.0),
        3.0 * (delta**2.0) * (channel_array - 4.0 / 29.0),
    )


def lab_from_xyz(xyz_array: np.ndarray, reference_illuminant: str = "D65") -> np.ndarray:
    """Convert a 3xHxW normalized XYZ array to CIELAB using the given reference illuminant."""

    xyz_array = _require_color_array(xyz_array)
    reference_illuminant = _require_reference_illuminant(reference_illuminant)
    illuminant = _reference_white_tensor(reference_illuminant, xyz_array)
    l_array = _lab_from_xyz_helper(xyz_array[1, :, :] / illuminant[1]) * 116.0 - 16.0
    a_array = (
        _lab_from_xyz_helper(xyz_array[0, :, :] / illuminant[0])
        - _lab_from_xyz_helper(xyz_array[1, :, :] / illuminant[1])
    ) * 500.0
    b_array = (
        _lab_from_xyz_helper(xyz_array[1, :, :] / illuminant[1])
        - _lab_from_xyz_helper(xyz_array[2, :, :] / illuminant[2])
    ) * 200.0
    return np.stack([l_array, a_array, b_array])


def xyz_from_lab(lab_array: np.ndarray, reference_illuminant: str = "D65") -> np.ndarray:
    """Convert a 3xHxW CIELAB array to normalized XYZ using the given reference illuminant."""

    lab_array = _require_color_array(lab_array)
    reference_illuminant = _require_reference_illuminant(reference_illuminant)
    illuminant = _reference_white_tensor(reference_illuminant, lab_array)
    fy_array = (lab_array[0, :, :] + 16.0) / 116.0
    fx_array = fy_array + (lab_array[1, :, :] / 500.0)
    fz_array = fy_array - (lab_array[2, :, :] / 200.0)
    return np.stack(
        [
            illuminant[0] * _xyz_from_lab_helper(fx_array),
            illuminant[1] * _xyz_from_lab_helper(fy_array),
            illuminant[2] * _xyz_from_lab_helper(fz_array),
        ]
    )


def lab_from_linear_srgb(linear_srgb_array: np.ndarray, reference_illuminant: str = "D65") -> np.ndarray:
    """Convert a 3xHxW linear-light sRGB array to CIELAB using the given reference illuminant."""

    linear_srgb_array = _require_color_array(linear_srgb_array)
    reference_illuminant = _require_reference_illuminant(reference_illuminant)
    xyz_array = xyz_from_linear_srgb(linear_srgb_array)
    if reference_illuminant != "D65":
        xyz_array = _adapt_xyz(xyz_array, source_illuminant="D65", target_illuminant=reference_illuminant)
    return lab_from_xyz(xyz_array, reference_illuminant=reference_illuminant)


def linear_srgb_from_lab(lab_array: np.ndarray, reference_illuminant: str = "D65") -> np.ndarray:
    """Convert a 3xHxW CIELAB array to linear-light sRGB using the given reference illuminant."""

    lab_array = _require_color_array(lab_array)
    reference_illuminant = _require_reference_illuminant(reference_illuminant)
    xyz_array = xyz_from_lab(lab_array, reference_illuminant=reference_illuminant)
    if reference_illuminant != "D65":
        xyz_array = _adapt_xyz(xyz_array, source_illuminant=reference_illuminant, target_illuminant="D65")
    return linear_srgb_from_xyz(xyz_array)


def lab_from_srgb(srgb_array: np.ndarray, reference_illuminant: str = "D65") -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array to CIELAB using the given reference illuminant."""

    srgb_array = _require_color_array(srgb_array)
    return lab_from_linear_srgb(linear_srgb_from_srgb(srgb_array), reference_illuminant=reference_illuminant)


def srgb_from_lab(lab_array: np.ndarray, reference_illuminant: str = "D65") -> np.ndarray:
    """Convert a 3xHxW CIELAB array to gamma-corrected sRGB using the given reference illuminant."""

    lab_array = _require_color_array(lab_array)
    return srgb_from_linear_srgb(linear_srgb_from_lab(lab_array, reference_illuminant=reference_illuminant))


def oklab_from_linear_srgb(linear_srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW linear-light sRGB array to Oklab."""

    linear_srgb_array = _require_color_array(linear_srgb_array)
    lms_array = _apply_matrix(_LINEAR_SRGB_TO_OKLAB_LMS_MATRIX, linear_srgb_array)
    lms_cbrt_array = np.sign(lms_array) * np.power(np.abs(lms_array), 1.0 / 3.0)
    return _apply_matrix(_LMS_CUBE_ROOT_TO_OKLAB_MATRIX, lms_cbrt_array)


def linear_srgb_from_oklab(oklab_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklab array to linear-light sRGB."""

    oklab_array = _require_color_array(oklab_array)
    lms_cbrt_array = _apply_matrix(_OKLAB_TO_LMS_CUBE_ROOT_MATRIX, oklab_array)
    lms_array = lms_cbrt_array**3
    return _apply_matrix(_LMS_TO_LINEAR_SRGB_MATRIX, lms_array)


def oklab_from_srgb(srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array to Oklab."""

    srgb_array = _require_color_array(srgb_array)
    return oklab_from_linear_srgb(linear_srgb_from_srgb(srgb_array))


def srgb_from_oklab(oklab_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklab array to gamma-corrected sRGB."""

    oklab_array = _require_color_array(oklab_array)
    return srgb_from_linear_srgb(linear_srgb_from_oklab(oklab_array))


def oklab_from_xyz(xyz_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW normalized XYZ array, where D65 white is approximately 1.0, to Oklab."""

    xyz_array = _require_color_array(xyz_array)
    return oklab_from_linear_srgb(linear_srgb_from_xyz(xyz_array))


def xyz_from_oklab(oklab_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklab array to normalized XYZ, where D65 white is approximately 1.0."""

    oklab_array = _require_color_array(oklab_array)
    return xyz_from_linear_srgb(linear_srgb_from_oklab(oklab_array))


def oklch_from_oklab(oklab_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklab array to Oklch, with hue in degrees."""

    oklab_array = _require_color_array(oklab_array)
    lightness = oklab_array[0, ...]
    chroma = np.sqrt(oklab_array[1, ...] ** 2 + oklab_array[2, ...] ** 2)
    hue = np.remainder(np.rad2deg(np.arctan2(oklab_array[2, ...], oklab_array[1, ...])), 360.0)
    return np.stack([lightness, chroma, hue])


def oklab_from_oklch(oklch_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklch array, with hue in degrees, to Oklab."""

    oklch_array = _require_color_array(oklch_array)
    hue_radians = np.deg2rad(oklch_array[2, ...])
    a_channel = oklch_array[1, ...] * np.cos(hue_radians)
    b_channel = oklch_array[1, ...] * np.sin(hue_radians)
    return np.stack([oklch_array[0, ...], a_channel, b_channel])


def linear_srgb_from_oklch(oklch_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklch array directly to linear-light sRGB."""

    oklch_array = _require_color_array(oklch_array)
    return linear_srgb_from_oklab(oklab_from_oklch(oklch_array))


def oklch_from_linear_srgb(linear_srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW linear-light sRGB array directly to Oklch."""

    linear_srgb_array = _require_color_array(linear_srgb_array)
    return oklch_from_oklab(oklab_from_linear_srgb(linear_srgb_array))


def oklch_from_srgb(srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array directly to Oklch."""

    srgb_array = _require_color_array(srgb_array)
    return oklch_from_linear_srgb(linear_srgb_from_srgb(srgb_array))


def srgb_from_oklch(oklch_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklch array directly to gamma-corrected sRGB."""

    oklch_array = _require_color_array(oklch_array)
    return srgb_from_linear_srgb(linear_srgb_from_oklch(oklch_array))


def oklch_from_xyz(xyz_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW normalized XYZ array, where D65 white is approximately 1.0, to Oklch."""

    xyz_array = _require_color_array(xyz_array)
    return oklch_from_oklab(oklab_from_xyz(xyz_array))


def xyz_from_oklch(oklch_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW Oklch array to normalized XYZ, where D65 white is approximately 1.0."""

    oklch_array = _require_color_array(oklch_array)
    return xyz_from_oklab(oklab_from_oklch(oklch_array))


def _max_srgb_saturation_array(units_ab_array: np.ndarray, steps: int = 1) -> np.ndarray:
    rgb_k_matrix = np.array(
        [
            [1.19086277, 1.76576728, 0.59662641, 0.75515197, 0.56771245],
            [0.73956515, -0.45954494, 0.08285427, 0.12541070, 0.14503204],
            [1.35733652, -0.00915799, -1.15130210, -0.50559606, 0.00692167],
        ],
        dtype=units_ab_array.dtype,
    )
    rgb_w_matrix = _matrix_tensor(_LMS_TO_LINEAR_SRGB_MATRIX, units_ab_array)
    cond_r_array = -1.88170328 * units_ab_array[0, :, :] + -0.80936493 * units_ab_array[1, :, :]
    cond_g_array = 1.81444104 * units_ab_array[0, :, :] + -1.19445276 * units_ab_array[1, :, :]
    terms_array = np.stack(
        [
            np.ones(units_ab_array.shape[1:], dtype=units_ab_array.dtype),
            units_ab_array[0, :, :],
            units_ab_array[1, :, :],
            np.power(units_ab_array[0, :, :], 2.0),
            units_ab_array[0, :, :] * units_ab_array[1, :, :],
        ]
    )
    s_array = np.where(
        cond_r_array > 1.0,
        np.einsum("twh, t -> wh", terms_array, rgb_k_matrix[0]),
        np.where(
            cond_g_array > 1.0,
            np.einsum("twh, t -> wh", terms_array, rgb_k_matrix[1]),
            np.einsum("twh, t -> wh", terms_array, rgb_k_matrix[2]),
        ),
    )
    k_lms_matrix = _matrix_tensor(tuple(row[1:] for row in _OKLAB_TO_LMS_CUBE_ROOT_MATRIX), units_ab_array)
    k_lms_array = np.einsum("tc, cwh -> twh", k_lms_matrix, units_ab_array)
    for _ in range(steps):
        root_lms_array = k_lms_array * s_array + 1.0
        lms_array = np.power(root_lms_array, 3.0)
        lms_ds_array = (np.power(root_lms_array, 2.0) * k_lms_array) * 3.0
        lms_ds2_array = (np.power(k_lms_array, 2.0) * root_lms_array) * 6.0
        f_array = np.where(
            cond_r_array > 1.0,
            np.einsum("c, cwh -> wh", rgb_w_matrix[0], lms_array),
            np.where(
                cond_g_array > 1.0,
                np.einsum("c, cwh -> wh", rgb_w_matrix[1], lms_array),
                np.einsum("c, cwh -> wh", rgb_w_matrix[2], lms_array),
            ),
        )
        f_array_1 = np.where(
            cond_r_array > 1.0,
            np.einsum("c, cwh -> wh", rgb_w_matrix[0], lms_ds_array),
            np.where(
                cond_g_array > 1.0,
                np.einsum("c, cwh -> wh", rgb_w_matrix[1], lms_ds_array),
                np.einsum("c, cwh -> wh", rgb_w_matrix[2], lms_ds_array),
            ),
        )
        f_array_2 = np.where(
            cond_r_array > 1.0,
            np.einsum("c, cwh -> wh", rgb_w_matrix[0], lms_ds2_array),
            np.where(
                cond_g_array > 1.0,
                np.einsum("c, cwh -> wh", rgb_w_matrix[1], lms_ds2_array),
                np.einsum("c, cwh -> wh", rgb_w_matrix[2], lms_ds2_array),
            ),
        )
        s_array = s_array - (f_array * f_array_1) / (np.power(f_array_1, 2.0) - (f_array * f_array_2) * 0.5)
    return s_array


def _find_cusp_array(units_ab_array: np.ndarray, steps: int = 1) -> np.ndarray:
    s_cusp_array = _max_srgb_saturation_array(units_ab_array, steps=steps)
    oklab_array = np.stack(
        [
            np.ones(s_cusp_array.shape, dtype=s_cusp_array.dtype),
            s_cusp_array * units_ab_array[0, :, :],
            s_cusp_array * units_ab_array[1, :, :],
        ]
    )
    rgb_at_max_array = linear_srgb_from_oklab(oklab_array)
    l_cusp_array = np.power(1.0 / rgb_at_max_array.max(axis=0), 1.0 / 3.0)
    c_cusp_array = l_cusp_array * s_cusp_array
    return np.stack([l_cusp_array, c_cusp_array])


def _find_gamut_intersection_array(
    units_ab_array: np.ndarray,
    l_1_array: np.ndarray,
    c_1_array: np.ndarray,
    l_0_array: np.ndarray,
    steps: int = 1,
    steps_outer: int = 1,
    lc_cusps_array: np.ndarray | None = None,
) -> np.ndarray:
    if lc_cusps_array is None:
        lc_cusps_array = _find_cusp_array(units_ab_array, steps=steps)
    cond_array = (l_1_array - l_0_array) * lc_cusps_array[1, :, :] - (lc_cusps_array[0, :, :] - l_0_array) * c_1_array
    t_array = np.where(
        cond_array <= 0.0,
        (lc_cusps_array[1, :, :] * l_0_array)
        / (c_1_array * lc_cusps_array[0, :, :] + lc_cusps_array[1, :, :] * (l_0_array - l_1_array)),
        (lc_cusps_array[1, :, :] * (l_0_array - 1.0))
        / (c_1_array * (lc_cusps_array[0, :, :] - 1.0) + lc_cusps_array[1, :, :] * (l_0_array - l_1_array)),
    )
    for _ in range(steps_outer):
        dl_array = l_1_array - l_0_array
        dc_array = c_1_array
        k_lms_matrix = _matrix_tensor(tuple(row[1:] for row in _OKLAB_TO_LMS_CUBE_ROOT_MATRIX), units_ab_array)
        k_lms_array = np.einsum("tc, cwh -> twh", k_lms_matrix, units_ab_array)
        lms_dt_array = k_lms_array * dc_array + dl_array
        for _ in range(steps):
            l_array = l_0_array * (t_array * -1.0 + 1.0) + t_array * l_1_array
            c_array = t_array * c_1_array
            root_lms_array = k_lms_array * c_array + l_array
            lms_array = np.power(root_lms_array, 3.0)
            lms_dt_array_1 = (np.power(root_lms_array, 2.0) * lms_dt_array) * 3.0
            lms_dt2_array = (np.power(lms_dt_array, 2.0) * root_lms_array) * 6.0
            rgb_matrix = _matrix_tensor(_LMS_TO_LINEAR_SRGB_MATRIX, units_ab_array)
            rgb_array = np.einsum("qt, twh -> qwh", rgb_matrix, lms_array) - 1.0
            rgb_array_1 = np.einsum("qt, twh -> qwh", rgb_matrix, lms_dt_array_1)
            rgb_array_2 = np.einsum("qt, twh -> qwh", rgb_matrix, lms_dt2_array)
            u_rgb_array = rgb_array_1 / (np.power(rgb_array_1, 2.0) - (rgb_array * rgb_array_2) * 0.5)
            t_rgb_raw = rgb_array * -1.0 * u_rgb_array
            max_floats = np.full(t_rgb_raw.shape, MAX_FLOAT, dtype=t_rgb_raw.dtype)
            t_rgb_array = np.where(u_rgb_array < 0.0, max_floats, t_rgb_raw)
            t_array = np.where(cond_array > 0.0, t_array + t_rgb_array.min(axis=0), t_array)
    return t_array


def gamut_clip_tensor(rgb_l_array: np.ndarray, alpha: float = 0.05, steps: int = 1, steps_outer: int = 1) -> np.ndarray:
    rgb_l_array = _require_color_array(rgb_l_array)
    lab_array = oklab_from_linear_srgb(rgb_l_array)
    epsilon = 0.00001
    chroma_array = np.sqrt(np.power(lab_array[1, :, :], 2.0) + np.power(lab_array[2, :, :], 2.0))
    chroma_array = np.where(chroma_array < epsilon, epsilon, chroma_array)
    units_ab_array = lab_array[1:, :, :] / chroma_array
    l_d_array = lab_array[0] - 0.5
    e_1_array = np.abs(l_d_array) + chroma_array * alpha + 0.5
    l_0_array = (
        np.sign(l_d_array) * (e_1_array - np.sqrt(np.power(e_1_array, 2.0) - np.abs(l_d_array) * 2.0)) + 1.0
    ) * 0.5
    t_array = _find_gamut_intersection_array(
        units_ab_array, lab_array[0, :, :], chroma_array, l_0_array, steps=steps, steps_outer=steps_outer
    )
    l_clipped_array = l_0_array * (t_array * -1 + 1.0) + t_array * lab_array[0, :, :]
    c_clipped_array = t_array * chroma_array
    return np.where(
        np.logical_or(rgb_l_array.max(axis=0) > 1.0, rgb_l_array.min(axis=0) < 0.0),
        linear_srgb_from_oklab(
            np.stack(
                [
                    l_clipped_array,
                    c_clipped_array * units_ab_array[0, :, :],
                    c_clipped_array * units_ab_array[1, :, :],
                ]
            )
        ),
        rgb_l_array,
    )


def _st_cusps_from_lc(lc_cusps_array: np.ndarray) -> np.ndarray:
    return np.stack(
        [
            lc_cusps_array[1, :, :] / lc_cusps_array[0, :, :],
            lc_cusps_array[1, :, :] / (lc_cusps_array[0, :, :] * -1.0 + 1),
        ]
    )


def _ok_l_r_from_l_array(x_array: np.ndarray) -> np.ndarray:
    k_1 = 0.206
    k_2 = 0.03
    k_3 = (1.0 + k_1) / (1.0 + k_2)
    return ((x_array * k_3 - k_1) + np.sqrt(np.power(x_array * k_3 - k_1, 2.0) + x_array * k_3 * k_2 * 4.0)) * 0.5


def _ok_l_from_lr_array(x_array: np.ndarray) -> np.ndarray:
    k_1 = 0.206
    k_2 = 0.03
    k_3 = (1.0 + k_1) / (1.0 + k_2)
    return (np.power(x_array, 2.0) + x_array * k_1) / ((x_array + k_2) * k_3)


def srgb_from_okhsv(okhsv_array: np.ndarray, alpha: float = 0.05, steps: int = 1) -> np.ndarray:
    """Convert a 3xHxW Okhsv array, with hue in degrees, to gamma-corrected sRGB."""

    okhsv_array = _require_color_array(okhsv_array)
    okhsv_array = okhsv_array.copy()
    okhsv_array[1:, ...] = np.clip(okhsv_array[1:, ...], 0.0, 1.0)
    unit_hue_array = _unit_hue_from_degrees(okhsv_array[0, :, :])
    units_ab_array = np.stack([np.cos(unit_hue_array * (2.0 * PI)), np.sin(unit_hue_array * (2.0 * PI))])
    lc_cusps_array = _find_cusp_array(units_ab_array, steps=steps)
    st_max_array = _st_cusps_from_lc(lc_cusps_array)
    s_0_array = _full_like_spatial(st_max_array, 0.5)
    k_array = (s_0_array / st_max_array[0, :, :]) * -1.0 + 1
    lc_v_base_array = s_0_array + (st_max_array[1, :, :] - st_max_array[1, :, :] * (k_array * okhsv_array[1, :, :]))
    lc_v_array = np.stack(
        [
            (okhsv_array[1, :, :] * s_0_array * -1.0) / lc_v_base_array + 1.0,
            (okhsv_array[1, :, :] * st_max_array[1, :, :] * s_0_array) / lc_v_base_array,
        ]
    )
    lc_array = okhsv_array[2, :, :] * lc_v_array
    l_vt_array = _ok_l_from_lr_array(lc_v_array[0, :, :])
    c_vt_array = lc_v_array[1, :, :] * (l_vt_array / lc_v_array[0, :, :])
    l_new_array = _ok_l_from_lr_array(lc_array[0, :, :])
    lc_array[1, :, :] = lc_array[1, :, :] * (l_new_array / lc_array[0, :, :])
    lc_array[0, :, :] = l_new_array
    rgb_scale_array = linear_srgb_from_oklab(
        np.stack(
            [
                l_vt_array,
                units_ab_array[0, :, :] * c_vt_array,
                units_ab_array[1, :, :] * c_vt_array,
            ]
        )
    )
    scale_l_array = np.power(
        1.0 / np.maximum(rgb_scale_array.max(axis=0), np.zeros(rgb_scale_array.shape[1:], dtype=rgb_scale_array.dtype)),
        1.0 / 3.0,
    )
    lc_array = lc_array * np.broadcast_to(scale_l_array, lc_array.shape)
    rgb_array = linear_srgb_from_oklab(
        np.stack(
            [
                lc_array[0, :, :],
                units_ab_array[0, :, :] * lc_array[1, :, :],
                units_ab_array[1, :, :] * lc_array[1, :, :],
            ]
        )
    )
    rgb_array = srgb_from_linear_srgb(gamut_clip_tensor(rgb_array, alpha=alpha, steps=steps))
    return np.clip(np.where(np.isnan(rgb_array), 0.0, rgb_array), 0.0, 1.0)


def okhsv_from_srgb(srgb_array: np.ndarray, steps: int = 1) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array to Okhsv, with hue in degrees."""

    srgb_array = _require_color_array(srgb_array)
    lab_array = oklab_from_linear_srgb(linear_srgb_from_srgb(srgb_array))
    c_array = np.sqrt(np.power(lab_array[1, :, :], 2.0) + np.power(lab_array[2, :, :], 2.0))
    units_ab_array = lab_array[1:, :, :] / c_array
    h_array = np.arctan2(lab_array[2, :, :] * -1.0, lab_array[1, :, :] * -1.0) * 0.5 / PI + 0.5
    lc_cusps_array = _find_cusp_array(units_ab_array, steps=steps)
    st_max_array = _st_cusps_from_lc(lc_cusps_array)
    s_0_array = _full_like_spatial(st_max_array, 0.5)
    k_array = (s_0_array / st_max_array[0, :, :]) * -1.0 + 1
    t_array = st_max_array[1, :, :] / (c_array + lab_array[0, :, :] * st_max_array[1, :, :])
    l_v_array = t_array * lab_array[0, :, :]
    c_v_array = t_array * c_array
    l_vt_array = _ok_l_from_lr_array(l_v_array)
    c_vt_array = c_v_array * (l_vt_array / l_v_array)
    rgb_scale_array = linear_srgb_from_oklab(
        np.stack(
            [
                l_vt_array,
                units_ab_array[0, :, :] * c_vt_array,
                units_ab_array[1, :, :] * c_vt_array,
            ]
        )
    )
    scale_l_array = np.power(
        1.0 / np.maximum(rgb_scale_array.max(axis=0), np.zeros(rgb_scale_array.shape[1:], dtype=rgb_scale_array.dtype)),
        1.0 / 3.0,
    )
    lab_array[0, :, :] = lab_array[0, :, :] / scale_l_array
    c_array = c_array / scale_l_array
    c_array = c_array * (_ok_l_r_from_l_array(lab_array[0, :, :]) / lab_array[0, :, :])
    lab_array[0, :, :] = _ok_l_r_from_l_array(lab_array[0, :, :])
    v_array = lab_array[0, :, :] / l_v_array
    s_array = ((s_0_array + st_max_array[1, :, :]) * c_v_array) / (
        st_max_array[1, :, :] * s_0_array + st_max_array[1, :, :] * (k_array * c_v_array)
    )
    hsv_array = np.stack([_degrees_from_unit_hue(h_array), s_array, v_array])
    hsv_array = np.where(np.isnan(hsv_array), 0.0, hsv_array)
    hsv_array[1:, ...] = np.clip(hsv_array[1:, ...], 0.0, 1.0)
    return hsv_array


def _get_st_mid_array(units_ab_array: np.ndarray) -> np.ndarray:
    a = units_ab_array[0, :, :]
    b = units_ab_array[1, :, :]
    return np.stack(
        [
            1.0
            / (
                b * 4.15901240
                + a
                * (
                    b * 1.75198401
                    + a * (b * -10.02301043 + a * (b * 5.38770819 + a * 4.69891013 + -4.24894561) + -2.13704948)
                    + -2.19557347
                )
                + 7.44778970
            )
            + 0.11516993,
            1.0
            / (
                b * -0.68124379
                + a
                * (
                    b * 0.90148123
                    + a * (b * 0.61223990 + a * (b * -0.45399568 + a * -0.14661872 + 0.00299215) + -0.27087943)
                    + 0.40370612
                )
                + 1.61320320
            )
            + 0.11239642,
        ]
    )


def _get_cs_array(l_array: np.ndarray, units_ab_array: np.ndarray, steps: int = 1, steps_outer: int = 1) -> np.ndarray:
    lc_cusps_array = _find_cusp_array(units_ab_array, steps=steps)
    c_max_array = _find_gamut_intersection_array(
        units_ab_array,
        l_array,
        np.ones(l_array.shape, dtype=l_array.dtype),
        l_array,
        lc_cusps_array=lc_cusps_array,
        steps=steps,
        steps_outer=steps_outer,
    )
    st_max_array = _st_cusps_from_lc(lc_cusps_array)
    k_array = c_max_array / np.minimum(l_array * st_max_array[0, :, :], (l_array * -1.0 + 1.0) * st_max_array[1, :, :])
    st_mid_array = _get_st_mid_array(units_ab_array)
    c_a_array = l_array * st_mid_array[0, :, :]
    c_b_array = (l_array * -1.0 + 1.0) * st_mid_array[1, :, :]
    c_mid_array = (
        k_array * np.sqrt(np.sqrt(1.0 / (1.0 / np.power(c_a_array, 4.0) + 1.0 / np.power(c_b_array, 4.0)))) * 0.9
    )
    c_a_array = l_array * 0.4
    c_b_array = (l_array * -1.0 + 1.0) * 0.8
    c_0_array = np.sqrt(1.0 / (1.0 / np.power(c_a_array, 2.0) + 1.0 / np.power(c_b_array, 2.0)))
    return np.stack([c_0_array, c_mid_array, c_max_array])


def srgb_from_okhsl(hsl_array: np.ndarray, alpha: float = 0.05, steps: int = 1, steps_outer: int = 1) -> np.ndarray:
    """Convert a 3xHxW Okhsl array, with hue in degrees, to gamma-corrected sRGB."""

    hsl_array = _require_color_array(hsl_array)
    hsl_array = hsl_array.copy()
    hsl_array[1:, ...] = np.clip(hsl_array[1:, ...], 0.0, 1.0)
    l_ones_mask = hsl_array[2, :, :] == 1.0
    l_zeros_mask = hsl_array[2, :, :] == 0.0
    calc_rgb_mask = np.logical_not(np.logical_or(l_ones_mask, l_zeros_mask))
    rgb_array = np.empty_like(hsl_array)
    rgb_array = np.where(l_ones_mask, 1.0, np.where(l_zeros_mask, 0.0, rgb_array))
    unit_hue_array = _unit_hue_from_degrees(hsl_array[0, :, :])
    units_ab_array = np.stack([np.cos(unit_hue_array * (2.0 * PI)), np.sin(unit_hue_array * (2.0 * PI))])
    l_2_array = _ok_l_from_lr_array(hsl_array[2, :, :])
    cs_array = _get_cs_array(l_2_array, units_ab_array, steps=steps, steps_outer=steps_outer)
    mid = 0.8
    mid_inv = 1.25
    s_lt_mid_mask = hsl_array[1, :, :] < mid
    t_array = np.where(s_lt_mid_mask, hsl_array[1, :, :] * mid_inv, (hsl_array[1, :, :] - mid) / (1.0 - mid))
    k_1_array = np.where(
        s_lt_mid_mask,
        cs_array[0, :, :] * mid,
        ((np.power(cs_array[1, :, :], 2.0) * mid_inv**2.0) * (1.0 - mid)) / cs_array[0, :, :],
    )
    k_2_array = np.where(
        s_lt_mid_mask,
        (k_1_array / cs_array[1, :, :]) * -1.0 + 1.0,
        (k_1_array / (cs_array[2, :, :] - cs_array[1, :, :])) * -1.0 + 1.0,
    )
    c_array = (t_array * k_1_array) / ((k_2_array * t_array) * -1.0 + 1.0)
    c_array = np.where(s_lt_mid_mask, c_array, cs_array[1, :, :] + c_array)
    rgb_array = np.where(
        calc_rgb_mask,
        linear_srgb_from_oklab(
            np.stack([l_2_array, c_array * units_ab_array[0, :, :], c_array * units_ab_array[1, :, :]])
        ),
        rgb_array,
    )
    rgb_array = srgb_from_linear_srgb(gamut_clip_tensor(rgb_array, alpha=alpha, steps=steps, steps_outer=steps_outer))
    return np.clip(np.where(np.isnan(rgb_array), 0.0, rgb_array), 0.0, 1.0)


def okhsl_from_srgb(rgb_array: np.ndarray, steps: int = 1, steps_outer: int = 1) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array to Okhsl, with hue in degrees."""

    rgb_array = _require_color_array(rgb_array)
    lab_array = oklab_from_linear_srgb(linear_srgb_from_srgb(rgb_array))
    c_array = np.sqrt(np.power(lab_array[1, :, :], 2.0) + np.power(lab_array[2, :, :], 2.0))
    units_ab_array = np.stack([lab_array[1, :, :] / c_array, lab_array[2, :, :] / c_array])
    h_array = np.arctan2(lab_array[2, :, :] * -1.0, lab_array[1, :, :] * -1.0) * 0.5 / PI + 0.5
    cs_array = _get_cs_array(lab_array[0, :, :], units_ab_array, steps=steps, steps_outer=steps_outer)
    mid = 0.8
    mid_inv = 1.25
    c_lt_c_mid_mask = c_array < cs_array[1, :, :]
    k_1_array = np.where(
        c_lt_c_mid_mask,
        cs_array[0, :, :] * mid,
        ((np.power(cs_array[1, :, :], 2.0) * mid_inv**2) * (1.0 - mid)) / cs_array[0, :, :],
    )
    k_2_array = np.where(
        c_lt_c_mid_mask,
        (k_1_array / cs_array[1, :, :]) * -1.0 + 1.0,
        (k_1_array / (cs_array[2, :, :] - cs_array[1, :, :])) * -1.0 + 1.0,
    )
    t_array = np.where(
        c_lt_c_mid_mask,
        c_array / (k_1_array + k_2_array * c_array),
        (c_array - cs_array[1, :, :]) / (k_1_array + k_2_array * (c_array - cs_array[1, :, :])),
    )
    s_array = np.where(c_lt_c_mid_mask, t_array * mid, t_array * (1.0 - mid) + mid)
    l_array = _ok_l_r_from_l_array(lab_array[0, :, :])
    hsl_array = np.stack([_degrees_from_unit_hue(h_array), s_array, l_array])
    hsl_array = np.where(np.isnan(hsl_array), 0.0, hsl_array)
    hsl_array[1:, ...] = np.clip(hsl_array[1:, ...], 0.0, 1.0)
    return hsl_array


def hsl_from_srgb(rgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW gamma-corrected sRGB array to HSL, with hue in degrees."""

    rgb_array = _require_color_array(rgb_array)
    c_max_array = rgb_array.max(axis=0)
    c_min_array = rgb_array.min(axis=0)
    c_sum_array = c_max_array + c_min_array
    c_range_array = c_max_array - c_min_array
    l_array = c_sum_array / 2.0
    s_array = np.where(
        c_max_array == c_min_array,
        0.0,
        np.where(
            l_array < 0.5,
            c_range_array / c_sum_array,
            c_range_array / ((c_max_array + c_min_array) * -1.0 + 2.0),
        ),
    )
    rgb_c_array = (c_max_array - rgb_array) / c_range_array
    h_array = np.where(
        c_max_array == c_min_array,
        0.0,
        np.where(
            rgb_array[0, :, :] == c_max_array,
            rgb_c_array[2, :, :] - rgb_c_array[1, :, :],
            np.where(
                rgb_array[1, :, :] == c_max_array,
                (rgb_c_array[0, :, :] - rgb_c_array[2, :, :]) + 2.0,
                (rgb_c_array[1, :, :] - rgb_c_array[0, :, :]) + 4.0,
            ),
        ),
    )
    h_array = _degrees_from_unit_hue(np.remainder(h_array / 6.0, 1.0))
    return np.stack([h_array, s_array, l_array])


def srgb_from_hsl(hsl_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW HSL array, with hue in degrees, to gamma-corrected sRGB."""

    hsl_array = _require_color_array(hsl_array)
    hsl_array = hsl_array.copy()
    hsl_array[1:, ...] = np.clip(hsl_array[1:, ...], 0.0, 1.0)
    rgb_array = np.empty_like(hsl_array)
    s_0_mask = hsl_array[1, :, :] == 0.0
    rgb_array = np.where(s_0_mask, hsl_array[2, :, :], rgb_array)
    m2_array = np.where(
        hsl_array[2, :, :] <= 0.5,
        hsl_array[2, :, :] * (hsl_array[1, :, :] + 1.0),
        (hsl_array[2, :, :] + hsl_array[1, :, :]) - hsl_array[2, :, :] * hsl_array[1, :, :],
    )
    m1_array = hsl_array[2, :, :] * 2.0 - m2_array
    unit_hue_array = _unit_hue_from_degrees(hsl_array[0, :, :])

    def hsl_values(m1_array: np.ndarray, m2_array: np.ndarray, h_array: np.ndarray) -> np.ndarray:
        h_array = np.remainder(h_array, 1.0)
        result_array = m1_array.copy()
        return np.where(
            h_array < 1.0 / 6.0,
            m1_array + (m2_array - m1_array) * (h_array * 6.0),
            np.where(
                h_array < 0.5,
                m2_array,
                np.where(
                    h_array < 2.0 / 3.0,
                    m1_array + (m2_array - m1_array) * ((h_array * -1.0 + 2.0 / 3.0) * 6.0),
                    result_array,
                ),
            ),
        )

    return np.stack(
        [
            hsl_values(m1_array, m2_array, unit_hue_array + 1.0 / 3.0),
            hsl_values(m1_array, m2_array, unit_hue_array),
            hsl_values(m1_array, m2_array, unit_hue_array - 1.0 / 3.0),
        ]
    )


def hsl_from_linear_srgb(linear_srgb_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW linear-light sRGB array directly to HSL, with hue in degrees."""

    linear_srgb_array = _require_color_array(linear_srgb_array)
    return hsl_from_srgb(srgb_from_linear_srgb(linear_srgb_array))


def linear_srgb_from_hsl(hsl_array: np.ndarray) -> np.ndarray:
    """Convert a 3xHxW HSL array, with hue in degrees, directly to linear-light sRGB."""

    hsl_array = _require_color_array(hsl_array)
    return linear_srgb_from_srgb(srgb_from_hsl(hsl_array))
