"""Validated inputs for one bounded cold-plate topology."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Dimension = Annotated[float, Field(ge=1, le=1000)]
Channel = Annotated[float, Field(ge=0.2, le=50)]
Variable = Literal['channel_count', 'channel_width_mm', 'channel_height_mm', 'rib_mm']
VARIABLE_LIMITS = {
    'channel_count': (1, 32), 'channel_width_mm': (0.2, 50),
    'channel_height_mm': (0.2, 50), 'rib_mm': (0.2, 50),
}

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False, validate_default=True)

class Geometry(Strict):
    length_mm: Dimension = 200
    width_mm: Dimension = 60
    thickness_mm: Annotated[float, Field(ge=1, le=100)] = 8
    base_mm: Channel = 2
    minimum_cover_mm: Channel = 2
    channel_count: int = Field(default=8, ge=1, le=32)
    channel_width_mm: Channel = 2
    channel_height_mm: Channel = 2
    rib_mm: Channel = 2

    @property
    def side_wall_mm(self) -> float:
        return (self.width_mm - self.channel_count * self.channel_width_mm
                - (self.channel_count - 1) * self.rib_mm) / 2

    @property
    def cover_mm(self) -> float:
        return self.thickness_mm - self.base_mm - self.channel_height_mm

class Thermal(Strict):
    heat_w: Annotated[float, Field(ge=0.001, le=100000)] = 10
    footprint_length_mm: Dimension = 200
    footprint_width_mm: Dimension = 60
    inlet_c: Annotated[float, Field(ge=5, le=80)] = 20
    maximum_temperature_c: Annotated[float, Field(ge=5, le=200)] = 60

class Fluid(Strict):
    coolant: Literal['water', 'user_supplied'] = 'water'
    volumetric_flow_l_min: Annotated[float, Field(ge=0.000001, le=100)] | None = 0.02
    mass_flow_kg_s: Annotated[float, Field(ge=0.00000001, le=10)] | None = None
    density_kg_m3: Annotated[float, Field(ge=100, le=3000)] = 998.2
    viscosity_pa_s: Annotated[float, Field(ge=0.00001, le=1)] = 0.001002
    conductivity_w_mk: Annotated[float, Field(ge=0.01, le=10)] = 0.598
    specific_heat_j_kgk: Annotated[float, Field(ge=100, le=10000)] = 4182
    property_temperature_c: Annotated[float, Field(ge=5, le=80)] = 20
    property_source: str = Field(default='Illustrative liquid water at 20 C; user must confirm', min_length=1, max_length=300)

    @model_validator(mode='after')
    def one_flow(self):
        if (self.volumetric_flow_l_min is None) == (self.mass_flow_kg_s is None):
            raise ValueError('Supply exactly one flow: volumetric_flow_l_min or mass_flow_kg_s')
        return self

class Material(Strict):
    name: str = Field(default='Illustrative aluminum', min_length=1, max_length=100)
    conductivity_w_mk: Annotated[float, Field(ge=1, le=500)] = 167
    density_kg_m3: Annotated[float, Field(ge=100, le=25000)] = 2700

class Limits(Strict):
    minimum_wall_mm: Channel = 1
    minimum_channel_mm: Channel = 0.5
    maximum_length_mm: Dimension = 500
    maximum_width_mm: Dimension = 500
    maximum_thickness_mm: Dimension = 100
    maximum_channel_pressure_drop_pa: Annotated[float, Field(ge=0.001, le=1e7)] = 10000
    process: Literal['unspecified', 'machining_and_bonding', 'additive'] = 'unspecified'

class Bounds(Strict):
    minimum: Annotated[float, Field(ge=0.2, le=50)]
    maximum: Annotated[float, Field(ge=0.2, le=50)]

    @model_validator(mode='after')
    def ordered(self):
        if self.minimum > self.maximum:
            raise ValueError('Optimization bounds must be ordered')
        return self

class Optimization(Strict):
    bounds: dict[Variable, Bounds] = Field(default_factory=lambda: {
        'channel_count': Bounds(minimum=4, maximum=12),
        'channel_width_mm': Bounds(minimum=1, maximum=3),
        'channel_height_mm': Bounds(minimum=1, maximum=3),
        'rib_mm': Bounds(minimum=1, maximum=2),
    }, max_length=4)
    maximum_evaluations: int = Field(default=40, ge=1, le=256)

    @model_validator(mode='after')
    def safe_bounds(self):
        for name, bounds in self.bounds.items():
            low, high = VARIABLE_LIMITS[name]
            if bounds.minimum < low or bounds.maximum > high:
                raise ValueError(f'{name} bounds must stay in [{low}, {high}]')
            if name == 'channel_count' and any(v != int(v) for v in (bounds.minimum, bounds.maximum)):
                raise ValueError('Channel count bounds must be integers')
        return self

class ColdPlateSpecification(Strict):
    geometry: Geometry = Field(default_factory=Geometry)
    thermal: Thermal = Field(default_factory=Thermal)
    fluid: Fluid = Field(default_factory=Fluid)
    material: Material = Field(default_factory=Material)
    limits: Limits = Field(default_factory=Limits)
    optimization: Optimization = Field(default_factory=Optimization)
    assumptions: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def envelope(self):
        g, t, c = self.geometry, self.thermal, self.limits
        if any(len(a) > 300 for a in self.assumptions):
            raise ValueError('Each assumption must be at most 300 characters')
        if min(g.side_wall_mm, g.rib_mm, g.base_mm, g.cover_mm) < c.minimum_wall_mm - 1e-9:
            raise ValueError('Channels violate minimum side wall, rib, base or cover thickness')
        if g.cover_mm < g.minimum_cover_mm - 1e-9:
            raise ValueError('Channel height leaves less than the requested cover')
        if min(g.channel_width_mm, g.channel_height_mm) < c.minimum_channel_mm:
            raise ValueError('Channel dimensions violate the minimum channel size')
        if any(a > b for a, b in zip((g.length_mm, g.width_mm, g.thickness_mm),
                                    (c.maximum_length_mm, c.maximum_width_mm, c.maximum_thickness_mm))):
            raise ValueError('Plate exceeds the allowed envelope')
        if t.footprint_length_mm > g.length_mm or t.footprint_width_mm > g.width_mm:
            raise ValueError('Centered heated footprint must fit on the plate')
        if t.maximum_temperature_c <= t.inlet_c:
            raise ValueError('Temperature limit must exceed the coolant inlet temperature')
        return self
