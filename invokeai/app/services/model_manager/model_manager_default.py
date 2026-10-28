"""Implementation of ModelManagerServiceBase."""

from typing_extensions import Self

from invokeai.app.services.config.config_default import InvokeAIAppConfig
from invokeai.app.services.download.download_base import DownloadQueueServiceBase
from invokeai.app.services.events.events_base import EventServiceBase
from invokeai.app.services.invoker import Invoker
from invokeai.app.services.model_install.model_install_base import ModelInstallServiceBase
from invokeai.app.services.model_install.model_install_default import ModelInstallService
from invokeai.app.services.model_load.model_load_base import ModelLoadServiceBase
from invokeai.app.services.model_load.model_load_default import ModelLoadService
from invokeai.app.services.model_manager.model_manager_base import ModelManagerServiceBase
from invokeai.app.services.model_records.model_records_base import (
    InvalidModelException,
    ModelRecordChanges,
    ModelRecordServiceBase,
)
from invokeai.backend.model_manager.configs.factory import AnyModelConfig
from invokeai.backend.model_manager.taxonomy import ModelSourceType


class ModelManagerService(ModelManagerServiceBase):
    """
    The ModelManagerService handles various aspects of model installation, maintenance and loading.

    It bundles three distinct services:
    model_manager.store   -- Routines to manage the database of model configuration records.
    model_manager.install -- Routines to install, move and delete models.
    model_manager.load    -- Routines to load models into memory.
    """

    def __init__(
        self,
        store: ModelRecordServiceBase,
        install: ModelInstallServiceBase,
        load: ModelLoadServiceBase,
    ):
        self._store = store
        self._install = install
        self._load = load

    @property
    def store(self) -> ModelRecordServiceBase:
        return self._store

    @property
    def install(self) -> ModelInstallServiceBase:
        return self._install

    @property
    def load(self) -> ModelLoadServiceBase:
        return self._load

    def update_model_record(self, key: str, changes: ModelRecordChanges) -> AnyModelConfig:
        return self._load.apply_record_change(
            key, lambda: self._store.update_model(key, changes=changes, allow_class_change=True)
        )

    def reidentify_model(self, key: str) -> AnyModelConfig:
        config = self._store.get_model(key)
        if config.source_type != ModelSourceType.External:
            # API-only build: local model identification (disk probing of checkpoint/LoRA/VAE
            # formats) was removed. Only external-provider records exist; they have no
            # on-disk weights to re-probe.
            raise InvalidModelException("local model re-identification is not available in API-only build")
        return self._load.apply_record_change(key, lambda: config)

    def start(self, invoker: Invoker) -> None:
        for service in [self._store, self._install, self._load]:
            if hasattr(service, "start"):
                service.start(invoker)

    def stop(self, invoker: Invoker) -> None:
        # API-only build: the load service keeps no per-device caches to shut down.
        for service in [self._store, self._install, self._load]:
            if hasattr(service, "stop"):
                service.stop(invoker)

    @classmethod
    def build_model_manager(
        cls,
        app_config: InvokeAIAppConfig,
        model_record_service: ModelRecordServiceBase,
        download_queue: DownloadQueueServiceBase,
        events: EventServiceBase,
    ) -> Self:
        """
        Construct the model manager service instance.

        For simplicity, use this class method rather than the __init__ constructor.
        """
        loader = ModelLoadService(app_config=app_config)
        installer = ModelInstallService(
            app_config=app_config,
            record_store=model_record_service,
            download_queue=download_queue,
            event_bus=events,
        )
        return cls(store=model_record_service, install=installer, load=loader)
