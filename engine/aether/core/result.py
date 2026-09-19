"""Typed analysis evidence, independent of HTTP and CAD rendering."""
from typing import Literal, Protocol, TypeVar
from pydantic import BaseModel
from .constraints import ConstraintResult

class PhysicsResult(BaseModel):
    velocity_m_s: float
    hydraulic_diameter_m: float
    mass_flow_kg_s: float
    reynolds: float
    prandtl: float
    regime: Literal['laminar', 'transitional', 'turbulent']
    darcy_friction_factor: float | None
    channel_pressure_drop_pa: float | None
    total_pressure_drop_pa: float | None = None
    coolant_rise_k: float
    coolant_outlet_c: float
    nusselt: float | None
    heat_transfer_w_m2k: float | None
    conduction_resistance_k_w: float
    thermal_resistance_k_w: float | None
    representative_temperature_c: float | None
    mass_kg: float
    correlation_valid: bool
    equations: dict[str, str]
    validity: list[str]
    warnings: list[str]
    assumptions: list[str]
    unsupported_physics: list[str]

class Evaluation(BaseModel):
    physics: PhysicsResult
    constraints: list[ConstraintResult]
    model_feasible: bool
    geometry_checked: bool = False
    physical_validation: bool = False
    high_fidelity_simulation: bool = False

Spec = TypeVar('Spec', contravariant=True)
class PhysicsEvaluator(Protocol[Spec]):
    def evaluate(self, specification: Spec) -> PhysicsResult: ...
