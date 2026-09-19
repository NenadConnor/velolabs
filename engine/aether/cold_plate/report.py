"""Versioned, self-contained JSON report tied to canonical structured inputs."""
import hashlib
import json
from datetime import datetime, timezone
from aether import VERSION
from .schema import ColdPlateSpecification
from .objective import evaluate
from .optimizer import OptimizationResult

def report(spec: ColdPlateSpecification, optimization: OptimizationResult | None = None) -> dict:
    canonical = json.dumps(spec.model_dump(), sort_keys=True, separators=(',', ':'), allow_nan=False)
    evaluation = evaluate(spec)
    return {
        'software': VERSION, 'report_schema_version': 1,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'input_sha256': hashlib.sha256(canonical.encode()).hexdigest(),
        'input_requirements': spec.model_dump(),
        'selected_design_parameters': spec.geometry.model_dump(),
        'geometry_dimensions_mm': {**spec.geometry.model_dump(), 'actual_cover_mm': spec.geometry.cover_mm,
                                   'side_wall_mm': spec.geometry.side_wall_mm},
        'material_assumptions': spec.material.model_dump(),
        'coolant_properties': spec.fluid.model_dump(),
        **evaluation.model_dump(),
        'optimizer': optimization.model_dump() if optimization else None,
        'validation_status': 'Analytical/schema checks only; CAD not built',
    }
