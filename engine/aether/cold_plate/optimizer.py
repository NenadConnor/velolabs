"""Bounded reproducible search. Every attempt, including invalid geometry, is recorded."""
from time import perf_counter
from pydantic import BaseModel, ValidationError
from aether.core.optimization import radical_inverse
from aether.core.result import Evaluation
from .schema import ColdPlateSpecification
from .objective import evaluate, rank

class Candidate(BaseModel):
    index: int
    parameters: dict[str, float | int]
    specification: ColdPlateSpecification | None = None
    evaluation: Evaluation | None = None
    rejection: str | None = None

class OptimizationResult(BaseModel):
    starting_design: ColdPlateSpecification
    candidates: list[Candidate]
    best_candidate: Candidate | None
    runtime_s: float
    method: str = 'Baseline, lower corner, upper corner, then Halton bases 2/3/5/7 in sorted variable order'
    objective: str = 'Model feasible first; correlation validity, failures, representative temperature, channel pressure, mass'
    feasible_found: bool

def optimize(spec: ColdPlateSpecification) -> OptimizationResult:
    started = perf_counter()
    candidates: list[Candidate] = []
    names = sorted(spec.optimization.bounds)
    for index in range(spec.optimization.maximum_evaluations):
        raw = spec.model_dump()
        parameters = {name: raw['geometry'][name] for name in names}
        if index:
            for dimension, name in enumerate(names):
                bounds = spec.optimization.bounds[name]
                fraction = 0 if index == 1 else 1 if index == 2 else radical_inverse(index-2, (2, 3, 5, 7)[dimension])
                value = bounds.minimum + fraction * (bounds.maximum - bounds.minimum)
                parameters[name] = int(round(value)) if name == 'channel_count' else round(value, 8)
        candidate = Candidate(index=index, parameters=parameters)
        try:
            if any(not spec.optimization.bounds[k].minimum <= v <= spec.optimization.bounds[k].maximum
                   for k, v in parameters.items()):
                raise ValueError('Starting design is outside allowed optimization bounds; recorded but not evaluated')
            raw['geometry'].update(parameters)
            candidate.specification = ColdPlateSpecification.model_validate(raw)
            candidate.evaluation = evaluate(candidate.specification)
        except (ValidationError, ValueError) as error:
            candidate.rejection = str(error)[:2000]
        candidates.append(candidate)
    eligible = [c for c in candidates if c.evaluation is not None]
    best = min(eligible, key=lambda c: rank(c.evaluation)) if eligible else None
    return OptimizationResult(starting_design=spec, candidates=candidates, best_candidate=best,
                              runtime_s=perf_counter()-started,
                              feasible_found=bool(best and best.evaluation.model_feasible))
