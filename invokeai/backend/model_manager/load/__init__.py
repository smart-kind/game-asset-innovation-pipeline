"""
Model loading package.

API-only builds retain only the capability metadata (fp8_capability) and cache statistics DTOs (model_cache.cache_stats)
that the model-manager API still serves; the torch loader stack was removed with the local-model backends.
"""
