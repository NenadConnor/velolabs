"""Requirement checks; model feasibility never implies complete system feasibility."""
from aether.core.constraints import ConstraintResult, compare
from aether.core.result import Evaluation, PhysicsEvaluator
from .physics import ReducedOrderEvaluator
from .schema import ColdPlateSpecification

def evaluate(spec: ColdPlateSpecification,
             evaluator: PhysicsEvaluator[ColdPlateSpecification] | None = None) -> Evaluation:
    spec = ColdPlateSpecification.model_validate(spec.model_dump())
    p = (evaluator or ReducedOrderEvaluator()).evaluate(spec)
    g, limits = spec.geometry, spec.limits
    checks = [
        compare('Representative plate temperature', p.representative_temperature_c,
                spec.thermal.maximum_temperature_c, 'C', 'Idealized model estimate only; local device maximum not resolved.'),
        compare('Channel pressure drop', p.channel_pressure_drop_pa, limits.maximum_channel_pressure_drop_pa,
                'Pa', 'Straight passage friction only. No system pressure-drop claim.'),
        compare('Minimum wall', min(g.rib_mm, g.side_wall_mm, g.base_mm, g.cover_mm),
                limits.minimum_wall_mm, 'mm', 'Algebraic wall envelope check.', minimum=True),
        compare('Channel width', g.channel_width_mm, limits.minimum_channel_mm, 'mm', 'Nominal width.', minimum=True),
        compare('Channel height', g.channel_height_mm, limits.minimum_channel_mm, 'mm', 'Nominal height.', minimum=True),
        compare('Requested cover', g.cover_mm, g.minimum_cover_mm, 'mm', 'Actual top cover thickness.', minimum=True),
        compare('Envelope length', g.length_mm, limits.maximum_length_mm, 'mm', 'Plate envelope.'),
        compare('Envelope width', g.width_mm, limits.maximum_width_mm, 'mm', 'Plate envelope.'),
        compare('Envelope thickness', g.thickness_mm, limits.maximum_thickness_mm, 'mm', 'Plate envelope.'),
        compare('Channel containment', g.side_wall_mm, limits.minimum_wall_mm, 'mm', 'Passages open intentionally at X ends.', minimum=True),
        ConstraintResult(name='Correlation validity', value=None, limit=None, unit='', margin=None,
                         status='PASS' if p.correlation_valid else 'WARNING', explanation='; '.join(p.validity)),
    ]
    feasible = p.correlation_valid and all(c.status == 'PASS' for c in checks)
    for name, explanation in [
        ('Connected B-Rep solid', 'Not checked until a CAD build succeeds.'),
        ('Total system pressure drop', 'External manifolds and fittings are not modeled.'),
        ('Device maximum temperature', 'Local spreading, contact resistance and hot spots are not modeled.'),
        ('Manufacturing process', f'{limits.process}: tool access, bonding, seals, print support and tolerances are not verified.'),
        ('Physical validation', 'No prototype measurements exist for this design.'),
    ]:
        checks.append(ConstraintResult(name=name, value=None, limit=None, unit='', margin=None,
                                       status='NOT_EVALUATED', explanation=explanation))
    return Evaluation(physics=p, constraints=checks, model_feasible=feasible)

def rank(result: Evaluation) -> tuple[float, ...]:
    """Feasible first, then temperature, pressure and mass; no hidden weighted sum."""
    p = result.physics
    failures = sum(c.status == 'FAIL' for c in result.constraints)
    return (0 if result.model_feasible else 1, 0 if p.correlation_valid else 1, failures,
            p.representative_temperature_c if p.representative_temperature_c is not None else float('inf'),
            p.channel_pressure_drop_pa if p.channel_pressure_drop_pa is not None else float('inf'), p.mass_kg)
