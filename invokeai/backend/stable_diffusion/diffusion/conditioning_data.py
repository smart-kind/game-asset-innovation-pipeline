"""Conditioning payload types: the local diffusion stack that produced them was removed.

API-only builds never populate these. The classes are kept as plain data carriers so that
`invokeai.invocation_api` keeps its published node-pack surface; nothing here touches torch.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BasicConditioningInfo:
    embeds: Any = None


@dataclass
class SDXLConditioningInfo(BasicConditioningInfo):
    pooled_embeds: Any = None
    add_time_ids: Any = None


@dataclass
class FLUXConditioningInfo:
    clip_embeds: Any = None


@dataclass
class SD3ConditioningInfo:
    clip_l_pooled_embeds: Any = None
    clip_l_embeds: Any = None
    clip_g_pooled_embeds: Any = None
    clip_g_embeds: Any = None


@dataclass
class CogView4ConditioningInfo:
    glm_embeds: Any = None


@dataclass
class ZImageConditioningInfo:
    prompt_embeds: Any = None


@dataclass
class ErnieImageConditioningInfo:
    prompt_embeds: Any = None


@dataclass
class Ideogram4ConditioningInfo:
    prompt_embeds: Any = None


@dataclass
class QwenImageConditioningInfo:
    prompt_embeds: Any = None
    prompt_embeds_mask: Any = None


@dataclass
class Krea2ConditioningInfo:
    prompt_embeds: Any = None
    prompt_embeds_mask: Any = None


@dataclass
class QwenImage21ConditioningInfo:
    prompt_embeds: Any = None


@dataclass
class AnimaConditioningInfo:
    qwen3_embeds: Any = None
    t5xxl_ids: Any = None
    t5xxl_weights: Any = None
    qwen35_states: Any = None
    qwen35_mask: Any = None


@dataclass
class MiniMaxH3ConditioningInfo:
    prompt_embeds: Any = None
    text_token_tags: Any = None
    keyframe_anchors: tuple[str, ...] = ()
    width: int | None = None
    height: int | None = None
    reference_signature: tuple[str, ...] = ()
    reference_num_frames: int | None = None


@dataclass
class LTX2ConditioningInfo:
    video_embeds: Any = None
    audio_embeds: Any = None
    attention_mask: Any = None


@dataclass
class WanConditioningInfo:
    prompt_embeds: Any = None
    prompt_attention_mask: Any = None


@dataclass
class ConditioningFieldData:
    conditionings: list[Any] = field(default_factory=list)
