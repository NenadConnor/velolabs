"""Bounded, declarative CAD contract. AI output is data, never executable code."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(ge=-10000, le=10000, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, le=10000, allow_inf_nan=False)]
Vector = tuple[Number, Number, Number]

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Feature(Strict):
    name: str = Field(max_length=100)
    operation: Literal['add', 'subtract'] = 'add'
    shape: Literal['box', 'cylinder', 'sphere', 'cone', 'extrusion']
    size: tuple[Positive, Positive, Positive] = (10, 10, 10)
    radius: Positive = 5
    top_radius: Annotated[float, Field(ge=0, le=10000)] = 2
    height: Positive = 10
    points: list[tuple[Number, Number]] = Field(default_factory=list, max_length=64)
    position: Vector = (0, 0, 0)
    rotation: Vector = (0, 0, 0)

    @model_validator(mode='after')
    def polygon(self):
        if self.shape == 'extrusion' and len(self.points) < 3:
            raise ValueError('Extrusions need at least 3 polygon points')
        return self

class Joint(Strict):
    type: Literal['fixed', 'revolute', 'slider'] = 'fixed'
    axis: Literal['x', 'y', 'z'] = 'z'
    origin: Vector = (0, 0, 0)
    min: Number = 0
    max: Number = 90
    value: Number = 0

    @model_validator(mode='after')
    def limits(self):
        if self.min > self.max or not self.min <= self.value <= self.max:
            raise ValueError('Joint value must be within ordered limits')
        return self

class Part(Strict):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,49}$')
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default='#a7b9cf', pattern=r'^#[0-9a-fA-F]{6}$')
    material: str = Field(default='Unspecified', max_length=100)
    position: Vector = (0, 0, 0)
    rotation: Vector = (0, 0, 0)
    parent: str | None = None
    joint: Joint = Field(default_factory=Joint)
    features: list[Feature] = Field(min_length=1, max_length=40)

    @model_validator(mode='after')
    def first_feature(self):
        if self.features[0].operation != 'add':
            raise ValueError('First feature must add a solid')
        return self

class Design(Strict):
    title: str = Field(min_length=1, max_length=150)
    summary: str = Field(max_length=3000)
    units: Literal['mm'] = 'mm'
    assumptions: list[str] = Field(default_factory=list, max_length=30)
    questions: list[str] = Field(default_factory=list, max_length=8)
    parts: list[Part] = Field(default_factory=list, max_length=24)

    @model_validator(mode='after')
    def topology(self):
        ids = [p.id for p in self.parts]
        if len(set(ids)) != len(ids):
            raise ValueError('Part IDs must be unique')
        by_id = {p.id:p for p in self.parts}
        if sum(len(p.features) for p in self.parts) > 160:
            raise ValueError('Maximum 160 features per design')
        for p in self.parts:
            seen = {p.id}
            parent = p.parent
            while parent:
                if parent not in by_id or parent in seen:
                    raise ValueError('Invalid parent or assembly cycle')
                seen.add(parent)
                parent = by_id[parent].parent
        if not self.parts and not self.questions:
            raise ValueError('Provide parts or clarification questions')
        return self

class GenerateRequest(Strict):
    prompt: str = Field(min_length=3, max_length=12000)
    model: str = Field(default='glm-5.3-flash:cloud', min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_.:/-]+$')
    design: Design | None = None
    history: list[str] = Field(default_factory=list, max_length=12)

class SimulationRequest(Strict):
    part_id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,49}$')
    axis: Literal['x','y','z'] = 'x'
    force: Vector = (0,0,-100)
    young_mpa: Annotated[float, Field(gt=0, le=1000000, allow_inf_nan=False)] = 69000
    poisson: Annotated[float, Field(gt=0, lt=0.49)] = 0.33
    yield_mpa: Positive = 276
    mesh_divisions: int = Field(default=8, ge=4, le=16)
