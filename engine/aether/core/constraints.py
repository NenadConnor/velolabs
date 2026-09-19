"""Constraint margins are positive when the specified inequality is satisfied."""
from typing import Literal
from pydantic import BaseModel

class ConstraintResult(BaseModel):
    name: str
    value: float | None
    limit: float | None
    unit: str
    status: Literal['PASS', 'FAIL', 'WARNING', 'NOT_EVALUATED']
    margin: float | None
    explanation: str

def compare(name: str, value: float | None, limit: float, unit: str,
            explanation: str, *, minimum: bool = False) -> ConstraintResult:
    margin = None if value is None else value - limit if minimum else limit - value
    return ConstraintResult(name=name, value=value, limit=limit, unit=unit,
                            margin=margin, status='NOT_EVALUATED' if margin is None else
                            'PASS' if margin >= -1e-9 else 'FAIL', explanation=explanation)
