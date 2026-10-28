"""Initialization file for model manager service."""

from invokeai.app.services.model_manager.model_manager_default import ModelManagerService, ModelManagerServiceBase

__all__ = [
    "ModelManagerServiceBase",
    "ModelManagerService",
]
