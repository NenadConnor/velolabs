# Aether — Computational Engineering Model foundation

Aether is a domain-specific extension of VeloLabs alpha, not universal engineering intelligence. Milestone 1 implements a deterministic cold-plate model with inspectable assumptions. There are no trained surrogates, The Well datasets, CFD capabilities or physical validation in this milestone.

## Engineering loop

Requirements → validated domain specification → parameterized geometry → reduced-order physics → constraints → bounded optimization → selected CAD → engineering report and validation evidence.

Natural-language input uses the existing server-side Ollama connection and planner transport. A separate prompt and strict Pydantic contract constrain output to `ColdPlateSpecification`. The UI presents the resulting specification for review; planning does not automatically evaluate or build. Numerical engineering inputs remain editable. Model output is always data, never executable Python.

## Components and connection points

- `engine/aether/core/`: SI conversions, typed physics/evaluation results, constraint margins, evaluator protocol and deterministic sampling primitive.
- `engine/aether/cold_plate/schema.py`: bounded geometry, thermal, fluid, material, design limits and optimization settings; cross-field validation.
- `geometry.py`: pure mapping to the existing `Design`/`Part`/`Feature` contract. The original kernel still owns Open CASCADE validation, triangulation and STEP export.
- `physics.py`: implemented `ReducedOrderEvaluator`; only fully developed laminar rectangular-channel correlations.
- `objective.py`: explicit constraint statuses and lexicographic candidate ranking.
- `optimizer.py`: deterministic bounded search with every attempted candidate, including rejected candidates.
- `report.py`: versioned JSON evidence with UTC timestamp and SHA-256 of canonical inputs.
- `engine/aether/api.py`: thin router with injected existing job admission, execution gate, planner transport and CAD builder.
- `app/aether-panel.tsx`: a bounded workspace entry point. Built solids are passed into the existing Three.js viewer and STEP export controls.

Evaluation/optimization do not create CAD solids. Until `/build` succeeds, `geometry_checked` is false and connected-solid status is `NOT_EVALUATED`. The adapter revalidates geometry before the existing bounded CAD subprocess runs. The kernel code and FEA solver are unchanged.

All new jobs share the existing four-job admission limit, one-job execution semaphore, origin checks and optional access token. Computation remains local. Reports and STEP artifacts use existing local job directories. No new dependencies were added; Python standard-library search and existing Pydantic/FastAPI/CAD components suffice.

## Evidence, not certification

`model_feasible` means the supported reduced-order inequalities pass and the selected correlations pass their application gates. It does not mean every requirement is validated. Total system pressure, local device maximum temperature, manufacturing process and physical validation remain `NOT_EVALUATED`. See [the cold-plate model](AETHER_COLD_PLATE.md) for the exact scope.

## Future extension

`PhysicsEvaluator[Specification]` is a typed protocol implemented by the reduced-order evaluator. A future solver or learned surrogate can be added behind an appropriate domain contract, with provenance, validity and failure behavior. No fake CFD or neural implementation is included. Future domains should own their schemas, geometry adapters, validity gates and benchmark suites rather than extend the HTTP layer with engineering equations.

Milestone 2 should add a high-fidelity thermal/fluid solver adapter, explicit manifold and boundary-condition geometry, mesh-convergence benchmarks and a reproducible dataset-generation pipeline. Physical experiments should eventually connect measurements to exact geometry/specification revisions. Surrogate training should follow validated solver data and held-out benchmarks, not precede them.
