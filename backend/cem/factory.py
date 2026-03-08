"""
CEM Factory — Maps intent to the correct Computational Engineering Model class
"""

from .furniture.sofa import SofaModel
from .electronics.handheld import HandheldDeviceModel
from .base import ComputationalModel

_CEM_REGISTRY = {
    # Furniture
    "sofa": SofaModel,
    "couch": SofaModel,
    "chair": SofaModel,  # Fallback to sofa logic for now

    # Consumer electronics — handheld devices
    "handheld_device": HandheldDeviceModel,
    "ipod": HandheldDeviceModel,
    "iphone": HandheldDeviceModel,
    "phone": HandheldDeviceModel,
    "smartphone": HandheldDeviceModel,
    "tablet": HandheldDeviceModel,
    "ipad": HandheldDeviceModel,
    "phablet": HandheldDeviceModel,
}

from typing import Type

def get_cem_class(entity_name: str) -> Type[ComputationalModel]:
    """Return the CEM class for a given entity name (e.g., 'sofa') if it exists."""
    return _CEM_REGISTRY.get(entity_name.lower())
