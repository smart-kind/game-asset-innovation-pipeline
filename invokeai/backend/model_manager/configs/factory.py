import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from pydantic import Discriminator, TypeAdapter, ValidationError
from typing_extensions import Annotated, Any

from invokeai.app.util.misc import uuid_string
from invokeai.backend.model_hash.model_hash import HASHING_ALGORITHMS
from invokeai.backend.model_manager.configs.base import Config_Base
from invokeai.backend.model_manager.configs.external_api import ExternalApiModelConfig
from invokeai.backend.model_manager.configs.identification_utils import InvalidMatchError, NotAMatchError
from invokeai.backend.model_manager.configs.unknown import Unknown_Config
from invokeai.backend.model_manager.model_on_disk import ModelOnDisk
from invokeai.backend.model_manager.taxonomy import (
    BaseModelType,
    ModelFormat,
    ModelSourceType,
    ModelType,
    variant_type_adapter,
)

logger = logging.getLogger(__name__)

# Known model file extensions for sanity checking
_MODEL_EXTENSIONS = {
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".bin",
    ".gguf",
    ".onnx",
}

# Known config file names for diffusers/transformers models
_CONFIG_FILES = {
    "model_index.json",
    "modular_model_index.json",
    "config.json",
}

# Maximum number of files in a model directory to be considered a model
_MAX_FILES_IN_MODEL_DIR = 50

# Maximum depth to search for model files in directories
_MAX_SEARCH_DEPTH = 2


def _is_known_model_marker(config_name: str, config: Any) -> bool:
    """Return whether a root config names a class/model type provided by our model libraries.

    API-only builds install neither diffusers nor transformers: without the libraries there is
    nothing to resolve a `_class_name`/`model_type`/`architectures` entry against, so no directory
    config counts as a known model marker and validation falls through to the file-count checks.
    """
    if not isinstance(config, dict):
        return False

    try:
        import diffusers
        import transformers
        from diffusers.models.modeling_utils import ModelMixin
        from diffusers.pipelines.pipeline_utils import DiffusionPipeline
        from transformers import PretrainedConfig, PreTrainedModel
        from transformers.models.auto.configuration_auto import CONFIG_MAPPING_NAMES
    except ImportError:
        return False

    def has_model_export(module: Any, name: Any, expected_bases: tuple[type, ...]) -> bool:
        if not isinstance(name, str) or not name:
            return False
        try:
            exported = getattr(module, name, None)
            return (
                isinstance(exported, type) and exported not in expected_bases and issubclass(exported, expected_bases)
            )
        except Exception:
            return False

    if config_name in ("model_index.json", "modular_model_index.json"):
        class_name = config.get("_class_name")
        # Non-str _class_name (e.g. a list) must read as "not a marker", not TypeError on the set lookup.
        return has_model_export(diffusers, class_name, (DiffusionPipeline,))

    class_name = config.get("_class_name")
    if (
        has_model_export(diffusers, class_name, (ModelMixin, DiffusionPipeline))
        or has_model_export(transformers, class_name, (PreTrainedModel, PretrainedConfig))
    ):
        return True
    model_type = config.get("model_type")
    if isinstance(model_type, str) and model_type in CONFIG_MAPPING_NAMES:
        return True
    architectures = config.get("architectures")
    return isinstance(architectures, list) and any(
        has_model_export(transformers, name, (PreTrainedModel,)) for name in architectures
    )


# The types are listed explicitly because IDEs/LSPs can't identify the correct types
# when AnyModelConfig is constructed dynamically using Config_Base.all_config_classes.
# API-only builds identify external API models (which refuse disk probing) and fall back
# to Unknown_Config; the local architecture config classes were removed with the torch stack.
AnyModelConfig = Annotated[
    Union[
        Annotated[ExternalApiModelConfig, ExternalApiModelConfig.get_tag()],
        # Unknown model (fallback)
        Annotated[Unknown_Config, Unknown_Config.get_tag()],
    ],
    Discriminator(Config_Base.get_model_discriminator_value),
]

AnyModelConfigValidator = TypeAdapter[AnyModelConfig](AnyModelConfig)
"""Pydantic TypeAdapter for the AnyModelConfig union, used for parsing and validation.

If you need to parse/validate a dict or JSON into an AnyModelConfig, you should probably use
ModelConfigFactory.from_dict or ModelConfigFactory.from_json instead as they may implement
additional logic in the future.
"""


@dataclass
class ModelClassificationResult:
    """Result of attempting to classify a model on disk into a specific model config.

    Attributes:
        match: The best matching model config, or None if no match was found.
        results: A mapping of model config class names to either an instance of that config class (if it matched)
            or an Exception (if it didn't match or an error occurred during matching).
    """

    config: AnyModelConfig | None
    details: dict[str, AnyModelConfig | Exception]

    @property
    def all_matches(self) -> list[AnyModelConfig]:
        """Returns a list of all matching model configs found."""
        return [r for r in self.details.values() if isinstance(r, Config_Base)]

    @property
    def match_count(self) -> int:
        """Returns the number of matching model configs found."""
        return len(self.all_matches)

    @property
    def invalid_matches(self) -> list[InvalidMatchError]:
        """Rejections from config classes that recognised the model but found it unusable.

        Non-empty means `config` is None because the file is broken, not because it is unidentifiable
        — callers can report the specific reason instead of a generic "could not identify".
        """
        return [r for r in self.details.values() if isinstance(r, InvalidMatchError)]


class ModelConfigFactory:
    @staticmethod
    def _detach_traceback(e: Exception) -> Exception:
        """Drop the traceback and exception chain from a failed match before it is stored.

        A stored traceback pins the frames of the config class that raised it, and those frames hold
        local objects that outlive the match. Nothing reads these tracebacks: `details` is only ever
        consumed for the exception's type and message.
        """
        e.__traceback__ = None
        e.__context__ = None
        e.__cause__ = None
        return e

    @staticmethod
    def from_dict(fields: dict[str, Any]) -> AnyModelConfig:
        """Return the appropriate config object from raw dict values."""
        model = AnyModelConfigValidator.validate_python(fields)
        return model

    @staticmethod
    def from_json(json: str | bytes | bytearray) -> AnyModelConfig:
        """Return the appropriate config object from json."""
        model = AnyModelConfigValidator.validate_json(json)
        return model

    @staticmethod
    def build_common_fields(
        mod: ModelOnDisk,
        override_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Builds the common fields for all model configs.

        Args:
            mod: The model on disk to extract fields from.
            overrides: A optional dictionary of fields to override. These fields will take precedence over the values
                extracted from the model on disk.

        - Casts string fields to their Enum types.
        - Does not validate the fields against the model config schema.
        """

        _overrides: dict[str, Any] = override_fields or {}
        fields: dict[str, Any] = {}

        if "type" in _overrides:
            fields["type"] = ModelType(_overrides["type"])

        if "format" in _overrides:
            fields["format"] = ModelFormat(_overrides["format"])

        if "base" in _overrides:
            fields["base"] = BaseModelType(_overrides["base"])

        if "source_type" in _overrides:
            fields["source_type"] = ModelSourceType(_overrides["source_type"])

        if "variant" in _overrides:
            fields["variant"] = variant_type_adapter.validate_strings(_overrides["variant"])

        fields["path"] = mod.path.as_posix()
        fields["source"] = _overrides.get("source") or fields["path"]
        fields["source_type"] = _overrides.get("source_type") or ModelSourceType.Path
        fields["name"] = _overrides.get("name") or mod.name
        fields["hash"] = _overrides.get("hash") or mod.hash()
        fields["key"] = _overrides.get("key") or uuid_string()
        fields["description"] = _overrides.get("description")
        fields["file_size"] = _overrides.get("file_size") or mod.size()

        return fields

    @staticmethod
    def _validate_path_looks_like_model(path: Path) -> None:
        """Perform basic sanity checks to ensure a path looks like a model.

        This prevents wasting time trying to identify obviously non-model paths like
        home directories or downloads folders. Raises ValueError if the path doesn't
        pass basic checks.

        Args:
            path: The path to validate

        Raises:
            ValueError: If the path doesn't look like a model
        """
        if path.is_file():
            # For files, just check the extension
            if path.suffix.lower() not in _MODEL_EXTENSIONS:
                raise ValueError(
                    f"File extension {path.suffix} is not a recognized model format. "
                    f"Expected one of: {', '.join(sorted(_MODEL_EXTENSIONS))}"
                )
        else:
            # Recognized Diffusers/Transformers configs are safe model markers. A generic config.json
            # is not sufficient because many large application directories contain one.
            recognized_root_config = False
            for config_name in _CONFIG_FILES:
                config_path = path / config_name
                if not config_path.exists():
                    continue
                try:
                    # Model config.json files are UTF-8; read explicitly so a non-ASCII value does not
                    # raise UnicodeDecodeError under a cp1252 (Windows) locale and get mis-treated as
                    # "unrecognized", which would wrongly reject a valid model directory.
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                recognized_root_config = _is_known_model_marker(config_name, config)
                if recognized_root_config:
                    break
            if recognized_root_config:
                return

            # For directories, do a quick file count check with early exit
            total_files = 0
            # Ignore hidden files and directories
            paths_to_check = (
                p
                for p in path.rglob("*")
                if not p.name.startswith(".") and not any(part.startswith(".") for part in p.parts)
            )
            for item in paths_to_check:
                if item.is_file():
                    total_files += 1
                    if total_files > _MAX_FILES_IN_MODEL_DIR:
                        raise ValueError(
                            f"Directory contains more than {_MAX_FILES_IN_MODEL_DIR} files. "
                            "This looks like a general-purpose directory rather than a model. "
                            "Please provide a path to a specific model file or model directory."
                        )

            # Otherwise, search for model files within depth limit
            def find_model_files(current_path: Path, depth: int) -> bool:
                if depth > _MAX_SEARCH_DEPTH:
                    return False
                try:
                    for item in current_path.iterdir():
                        if item.is_file() and item.suffix.lower() in _MODEL_EXTENSIONS:
                            return True
                        elif item.is_dir() and find_model_files(item, depth + 1):
                            return True
                except PermissionError:
                    pass
                return False

            if not find_model_files(path, 0):
                raise ValueError(
                    f"No model files or config files found in directory {path}. "
                    f"Expected to find model files with extensions: {', '.join(sorted(_MODEL_EXTENSIONS))} "
                    f"or config files: {', '.join(sorted(_CONFIG_FILES))}"
                )

    @staticmethod
    def matches_sort_key(m: AnyModelConfig) -> int:
        """Sort key function to prioritize model config matches in case of multiple matches."""
        # API-only builds have a single disk-probing config class (Unknown), so this order is
        # currently moot; it is kept so that re-added config classes sort predictably.
        match m.type:
            case ModelType.ExternalImageGenerator:
                return 0
            case _:
                return 3

    @staticmethod
    def from_model_on_disk(
        mod: str | Path | ModelOnDisk,
        override_fields: dict[str, Any] | None = None,
        hash_algo: HASHING_ALGORITHMS = "blake3_single",
        allow_unknown: bool = True,
    ) -> ModelClassificationResult:
        """Classify a model on disk and return the best matching model config.

        Args:
            mod: The model on disk to classify. Can be a path (str or Path) or a ModelOnDisk instance.
            override_fields: Optional dictionary of fields to override. These fields will take precedence
                over the values extracted from the model on disk, but this cannot force a match if the
                model on disk doesn't actually match the config class.
            hash_algo: The hashing algorithm to use when computing the model hash if needed.

        Returns:
            A ModelClassificationResult containing the best matching model config (or None if no match)
            and a mapping of all attempted model config classes to either an instance of that class (if it matched)
            or an Exception (if it didn't match or an error occurred during matching).

        Raises:
            ValueError: If the provided path doesn't look like a model.
        """
        if isinstance(mod, Path | str):
            mod = ModelOnDisk(Path(mod), hash_algo)

        # Perform basic sanity checks before attempting any config matching
        # This rejects obviously non-model paths early, saving time
        ModelConfigFactory._validate_path_looks_like_model(mod.path)

        # We will always need these fields to build any model config.
        fields = ModelConfigFactory.build_common_fields(mod, override_fields)

        # Store results as a mapping of config class to either an instance of that class or an exception
        # that was raised when trying to build it.
        details: dict[str, AnyModelConfig | Exception] = {}

        # Try to build an instance of each model config class that uses the classify API.
        # Each class will either return an instance of itself or raise NotAMatch if it doesn't match.
        for candidate_class in filter(lambda x: x is not Unknown_Config, Config_Base.CONFIG_CLASSES):
            candidate_name = candidate_class.__name__
            try:
                candidate = candidate_class.from_model_on_disk(mod, fields)
                details[candidate_name] = candidate  # type: ignore
            except NotAMatchError as e:
                # This means the model didn't match this config class. It's not an error, just no match.
                details[candidate_name] = ModelConfigFactory._detach_traceback(e)
            except InvalidMatchError as e:
                # The model *is* this config class' kind of model, but is unusable (e.g. a truncated
                # checkpoint). Recorded like any other result here; the fallback below treats this
                # differently from a plain no-match.
                details[candidate_name] = ModelConfigFactory._detach_traceback(e)
            except ValidationError as e:
                # The model matched, but the pydantic model instance could not be created.
                details[candidate_name] = ModelConfigFactory._detach_traceback(e)
            except Exception as e:
                # Some other unexpected error occurred. Store the exception for reporting later.
                details[candidate_name] = ModelConfigFactory._detach_traceback(e)

        # Extract just the successful matches
        matches = [r for r in details.values() if isinstance(r, Config_Base)]

        if not matches:
            if any(isinstance(r, InvalidMatchError) for r in details.values()):
                # A config class recognised the model and rejected it as unusable. That is not the same
                # as "unidentifiable": falling back to Unknown_Config here would register a file we know
                # to be broken as a normal model record, so the rejection wins over allow_unknown.
                return ModelClassificationResult(config=None, details=details)
            if not allow_unknown:
                # No matches and we are not allowed to fall back to Unknown_Config
                return ModelClassificationResult(config=None, details=details)
            else:
                # Fall back to Unknown_Config
                # This should always succeed as Unknown_Config.from_model_on_disk never raises NotAMatch
                config = Unknown_Config.from_model_on_disk(mod, fields)
                details[Unknown_Config.__name__] = config
                return ModelClassificationResult(config=config, details=details)

        matches.sort(key=ModelConfigFactory.matches_sort_key)
        config = matches[0]

        return ModelClassificationResult(config=config, details=details)
