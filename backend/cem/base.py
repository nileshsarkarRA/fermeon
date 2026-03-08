"""
Fermeon — Computational Engineering Model (CEM) Foundation
Following the Leap 71 / Noyron architecture: engineers write robust geometries,
LLMs only configure their high-level parameters via JSON.
"""

from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel
import cadquery as cq


class CEMParams(BaseModel):
    """
    Base class for all CEM parameters.
    Subclasses define the specific parameters (width, height, count, etc.)
    with default values and validation rules.
    """
    pass


class ComputationalModel(ABC):
    """
    Base class for all Computational Engineering Models.
    A CEM takes a set of validated parameters and returns a 100% robust,
    error-free CadQuery Workplane.
    """
    def __init__(self, params: CEMParams):
        self.params = params
        self.geometry: cq.Workplane | None = None

    @classmethod
    @abstractmethod
    def get_param_schema(cls) -> Type[CEMParams]:
        """Return the Pydantic model class for this CEM's parameters."""
        pass

    @abstractmethod
    def build(self) -> cq.Workplane:
        """
        Construct and return the physical geometry based on self.params.
        This must be human-written, deterministic CadQuery code that
        cannot fail due to syntax or method errors.
        """
        pass

    def __call__(self) -> cq.Workplane:
        """Convenience method to build and return geometry."""
        if self.geometry is None:
            self.geometry = self.build()
        return self.geometry
