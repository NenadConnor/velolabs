"""Thin API adapter reusing VeloLabs job admission, gate, planner and CAD builder."""
import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import Field
from .cold_plate.schema import ColdPlateSpecification, Strict
from .cold_plate.geometry import design
from .cold_plate.optimizer import optimize, OptimizationResult
from .cold_plate.report import report

class PlanRequest(Strict):
    prompt: str = Field(min_length=3, max_length=12000)
    model: str = Field(default='glm-5.3-flash:cloud', min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_.:/-]+$')
    specification: ColdPlateSpecification = Field(default_factory=ColdPlateSpecification)

def create_router(*, jobs: dict, new_job: Callable, launch: Callable, gate: asyncio.Semaphore,
                  build: Callable, data: Path, chat: Callable) -> APIRouter:
    router = APIRouter(prefix='/aether/cold-plate', tags=['Aether cold plate'])

    def queue(operation: str, spec: ColdPlateSpecification | PlanRequest,
              optimization_job_id: str | None = None) -> dict[str, str]:
        history = None
        if optimization_job_id:
            stored = jobs.get(optimization_job_id, {}).get('result', {})
            if not stored.get('optimizer'):
                raise HTTPException(404, 'Optimization history is unavailable; rerun optimization or build without history.')
            history = OptimizationResult.model_validate(stored['optimizer'])
            if not any(c.specification == spec for c in history.candidates):
                raise HTTPException(422, 'Build inputs do not match a candidate in this optimization job.')
        job_id = new_job()
        async def run() -> None:
            try:
                async with gate:
                    jobs[job_id].update(status='planning' if operation == 'plan' else 'building', message=f'Aether: {operation}…')
                    if operation == 'plan':
                        messages = [{'role': 'system', 'content':
                            'Return only JSON matching ColdPlateSpecification. Never return source code. '
                            'Only straight parallel rectangular passages, open at both ends, are supported. '
                            'Preserve explicit requirements; list all inferred defaults in assumptions. '
                            'No manifolds, CFD, certification or physical validation. Return the full specification.'},
                            {'role': 'user', 'content': 'Current specification: ' + spec.specification.model_dump_json() + '\nRequest: ' + spec.prompt}]
                        planned = await chat(messages, spec.model, ColdPlateSpecification)
                        result: Any = {'specification': planned.model_dump(), 'review_required': True}
                    elif operation == 'optimize':
                        outcome = await asyncio.to_thread(optimize, spec)
                        chosen = outcome.best_candidate.specification if outcome.best_candidate else spec
                        result = report(chosen, outcome)
                        result['optimization_job_id'] = job_id
                    else:
                        result = report(spec, history)
                        if history:
                            result['optimization_job_id'] = optimization_job_id
                        if operation == 'build':
                            cad = await asyncio.to_thread(build, design(spec), data / job_id)
                            cad['id'] = job_id
                            result['geometry_checked'] = True
                            result['validation_status'] = 'GEOMETRY CHECKED; NOT PHYSICALLY VALIDATED'
                            result['cad_job_id'] = job_id
                            result['cad_checks'] = cad['checks']
                            for constraint in result['constraints']:
                                if constraint['name'] == 'Connected B-Rep solid':
                                    constraint.update(status='PASS', value=1, limit=1, margin=0,
                                                      explanation='Existing kernel checked one valid connected solid and exported STEP.')
                            import json
                            (data/job_id/'engineering_report.json').write_text(json.dumps(result, indent=2, allow_nan=False), 'utf-8')
                            result = {'cad': cad, 'report': result}
                    jobs[job_id].update(status='complete', result=result)
            except Exception as error:
                jobs[job_id].update(status='failed', error=str(error)[:2000])
        launch(run())
        return {'id': job_id}

    @router.get('/defaults')
    async def defaults():
        return ColdPlateSpecification().model_dump()

    @router.post('/plan')
    async def plan(req: PlanRequest):
        return queue('plan', req)

    @router.post('/validate')
    async def validate(spec: ColdPlateSpecification):
        return spec.model_dump()

    @router.post('/evaluate')
    async def evaluate_endpoint(spec: ColdPlateSpecification):
        return queue('evaluate', spec)

    @router.post('/optimize')
    async def optimize_endpoint(spec: ColdPlateSpecification):
        return queue('optimize', spec)

    @router.post('/build')
    async def build_endpoint(spec: ColdPlateSpecification,
                             optimization_job_id: str | None = Query(default=None, pattern=r'^[a-f0-9]{32}$')):
        return queue('build', spec, optimization_job_id)

    return router
