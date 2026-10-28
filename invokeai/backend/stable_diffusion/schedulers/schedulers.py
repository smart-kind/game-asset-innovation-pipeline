"""API-only build: no local denoising stack, so the scheduler vocabulary is a
plain data set. Mirrors the names the pre-trim build offered, as literal
strings only — no torch or diffusers scheduler objects are constructed.
"""

from __future__ import annotations

from typing import Literal

SCHEDULER_NAME_VALUES = Literal[
    "euler",
    "euler_a",
    "ddim",
    "heun",
    "dpm_2",
    "dpm_2_a",
    "lms",
    "unipc",
    "ddim_inv",
    "sd_cd_ancestral",
    "ddim_static",
]

SchedulerPredictionType = Literal[
    "epsilon",
    "v_prediction",
    "lms",
    "ddpm",
    "ddim",
]
