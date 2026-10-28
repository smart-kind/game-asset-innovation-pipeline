"""Conditioning object storage: removed with the local-model stack.

API-only builds never produce conditioning data (no encoders, no denoise nodes), but the
invocation context still wires a ``conditioning`` serializer slot, so this placeholder keeps
that slot type-checked and fails fast if anything ever tries to use it.
"""

from invokeai.app.services.object_serializer.object_serializer_base import ObjectSerializerBase


class ConditioningFieldData:
    """Placeholder for the conditioning payload type; the real classes lived in the torch stack."""


class NullConditioningSerializer(ObjectSerializerBase[ConditioningFieldData]):
    """Keeps the conditioning serializer slot constructible; every use raises with a clear reason."""

    def load(self, name: str) -> ConditioningFieldData:
        raise RuntimeError("conditioning storage is unavailable in the API-only build")

    def save(self, obj: ConditioningFieldData) -> str:
        raise RuntimeError("conditioning storage is unavailable in the API-only build")

    def delete(self, name: str) -> None:
        raise RuntimeError("conditioning storage is unavailable in the API-only build")
