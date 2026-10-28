"""The starter model catalogue.

`STARTER_MODELS` is a curated order, not a derived one: it is what the install dialog shows, in
the sequence someone decided on. API-only builds offer only the external provider models; the
per-architecture local starter modules were removed together with the torch stack.
"""

from invokeai.backend.model_manager.starter_models.external import (
    alibabacloud_qwen_image_2,
    alibabacloud_qwen_image_2_pro,
    alibabacloud_qwen_image_edit_max,
    alibabacloud_qwen_image_max,
    alibabacloud_wan26_t2i,
    atlascloud_flux_2_pro,
    atlascloud_flux_dev,
    atlascloud_flux_schnell,
    atlascloud_grok_imagine_image_2,
    atlascloud_hidream_o1_1_5,
    atlascloud_ideogram_v4_quality,
    atlascloud_ideogram_v4_turbo,
    atlascloud_krea_2_turbo,
    atlascloud_mai_image_2_5,
    atlascloud_nano_banana_2,
    atlascloud_qwen_image_3,
    atlascloud_z_image_turbo,
    gemini_3_1_flash_image_preview,
    gemini_flash_image,
    gemini_pro_image_preview,
    openai_dall_e_3,
    openai_gpt_image_1,
    openai_gpt_image_1_5,
    openai_gpt_image_1_mini,
    openai_gpt_image_2,
    seedream_4_0,
    seedream_4_5,
    seedream_5_0,
    seedream_5_0_lite,
)
from invokeai.backend.model_manager.starter_models.types import (
    StarterModel,
    StarterModelBundle,
    StarterModelWithoutDependencies,
)

STARTER_MODELS: list[StarterModel] = [
    # -- External providers --
    gemini_flash_image,
    gemini_pro_image_preview,
    gemini_3_1_flash_image_preview,
    atlascloud_flux_schnell,
    atlascloud_flux_dev,
    atlascloud_flux_2_pro,
    atlascloud_qwen_image_3,
    atlascloud_z_image_turbo,
    atlascloud_mai_image_2_5,
    atlascloud_ideogram_v4_turbo,
    atlascloud_ideogram_v4_quality,
    atlascloud_krea_2_turbo,
    atlascloud_hidream_o1_1_5,
    atlascloud_grok_imagine_image_2,
    atlascloud_nano_banana_2,
    openai_gpt_image_2,
    openai_gpt_image_1_5,
    openai_gpt_image_1,
    openai_gpt_image_1_mini,
    openai_dall_e_3,
    seedream_5_0,
    seedream_5_0_lite,
    seedream_4_5,
    seedream_4_0,
    alibabacloud_qwen_image_2_pro,
    alibabacloud_qwen_image_2,
    alibabacloud_qwen_image_max,
    alibabacloud_wan26_t2i,
    alibabacloud_qwen_image_edit_max,
]

STARTER_BUNDLES: dict[str, StarterModelBundle] = {}

assert len(STARTER_MODELS) == len({m.source for m in STARTER_MODELS}), "Duplicate starter models"

__all__ = [
    "STARTER_BUNDLES",
    "STARTER_MODELS",
    "StarterModel",
    "StarterModelBundle",
    "StarterModelWithoutDependencies",
]
