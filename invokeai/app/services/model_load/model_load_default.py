"""API-only model load service.

The local-model loading stack (torch caches, the loader registry, per-device RAM/VRAM management)
was removed with the backend architectures. This service keeps the interface contract so the rest
of the model manager, its API routers and the invocation context can be constructed; anything that
would actually load weights into memory fails fast with a clear error instead.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from invokeai.app.services.config import InvokeAIAppConfig
from invokeai.app.services.invoker import Invoker
from invokeai.app.services.model_load.model_load_base import ModelLoadServiceBase
from invokeai.backend.model_manager.configs.factory import AnyModelConfig
from invokeai.backend.model_manager.taxonomy import SubModelType

logger = logging.getLogger(__name__)


class ModelLoadService(ModelLoadServiceBase):
    """A no-op model load service for API-only builds: nothing is ever loaded into memory."""

    def __init__(self, app_config: InvokeAIAppConfig):
        self._app_config = app_config
        self._invoker: Optional[Invoker] = None

    @property
    def invoker(self) -> Invoker:
        if self._invoker is None:
            raise RuntimeError("ModelLoadService.invoker accessed before the service was started")
        return self._invoker

    def start(self, invoker: Invoker) -> None:
        self._invoker = invoker
        logger.info("API-only build: no local model loading. Model load service is a no-op.")

    def stop(self, invoker: Invoker) -> None:
        pass

    @property
    def ram_cache(self) -> Any:
        return None

    @property
    def ram_caches(self) -> dict[str, Any]:
        return {}

    def load_model(
        self,
        model_config: AnyModelConfig,
        submodel_type: Optional[SubModelType] = None,
        user_id: Optional[str] = None,
    ) -> Any:
        raise RuntimeError("local model loading is disabled in API-only build")

    def load_model_from_path(self, model_path: Path, loader: Optional[Callable[[Path], Any]] = None) -> Any:
        raise RuntimeError("local model loading is disabled in API-only build")

    def apply_record_change(self, key: str, write: Callable[[], AnyModelConfig]) -> AnyModelConfig:
        # Nothing is cached, so no eviction or re-check is needed: run the write and return its result.
        return write()

    def drop_cached_models(self, keys: Iterable[str]) -> int:
        return 0
