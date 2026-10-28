"""API-only build: local diffusers pipelines and torch were removed.

`PipelineIntermediateState` is reduced to the small data carrier that the
remaining image invocations (`image.py`) and `step_callback` read back off a
denoise step. In an API-only build the external-provider path never populates
a live pipeline, so this is a plain value holder, not a diffusers object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL.Image import Image


@dataclass
class PipelineIntermediateState:
    """Placeholder intermediate state for the API-only build.

    Carries whatever a denoise step would have produced, so callers that read
    `image`, `current_step`, or `total_steps` keep working without torch.
    """

    image: "Image | None" = None
    current_step: int = 0
    total_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def last_image(self) -> "Image | None":
        return self.image

    def advance(self, steps: int = 1) -> None:
        self.current_step = min(self.current_step + steps, self.total_steps)
