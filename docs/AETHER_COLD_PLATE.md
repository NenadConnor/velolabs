# Aether Cold Plate CEM v0.1

This is a deterministic reduced-order engineering model for early comparison. It is not CFD, conjugate heat transfer, turbulence-resolved simulation, certification, manufacturing validation, fatigue analysis, pressure-vessel analysis or physical validation. It does not replace professional engineering review.

## Supported geometry and units

One rectangular plate, centered at the origin, with 1–32 identical rectangular passages running along X. Channels are centered symmetrically along Y and open through both X end faces. Box subtraction creates real internal passages. Base, ribs, side walls and top cover remain connected. The adapter emits at most 33 features and uses the unchanged cadgen/build123d/Open CASCADE kernel.

Geometry inputs use mm, heat uses W, temperatures use °C, pressure uses Pa. Fluid properties use kg/m³, Pa·s, W/(m·K), J/(kg·K). Material density uses kg/m³. Exactly one of volumetric flow in L/min or mass flow in kg/s must be supplied; set the other to null. Physics uses SI conversions in `core/units.py`.

Actual cover = total thickness − base thickness − channel height. `minimum_cover_mm` is a minimum, allowing the optimizer to vary channel height at fixed overall thickness. Side wall = [width − N·channel_width − (N−1)·rib]/2. All four wall types must meet `minimum_wall_mm`. Footprint is centered and must lie inside the plate envelope. Numeric inputs are finite and bounded; unknown fields and arbitrary source text are rejected.

There are no inlet/outlet manifolds, circular ports, fittings or seals. External headers are required to feed the passages. The idealized single solid does not represent the fabrication or joining of a cover. A process choice records intent only; tool access, additive support, tolerances, pressure containment and bonding are not checked.

## Equations

Let N be channel count, w/h the internal width/height in meters, L the plate length, α=min(w,h)/max(w,h), Vdot total volumetric flow, and Q total heat load.

```
velocity v = Vdot / (N*w*h)
hydraulic diameter Dh = 2*w*h/(w+h)
Re = rho*v*Dh/mu
Pr = mu*cp/k
Pe = Re*Pr

Darcy f = 96/Re * (1 − 1.3553α + 1.9467α² − 1.7012α³ + 0.9564α⁴ − 0.2537α⁵)
channel dp = f*(L/Dh)*rho*v²/2
Nu = 7.541*(1 − 2.610α + 4.970α² − 5.119α³ + 2.702α⁴ − 0.548α⁵)
heat-transfer coefficient hc = Nu*k/Dh

mdot = rho*Vdot
coolant rise = Q/(mdot*cp)
Tout = Tin + coolant rise
base resistance Rb = base/(material_k*footprint_area)
wetted area A = N*2*(w+h)*L
capacity C = mdot*cp
thermal resistance R = Rb + 1/[C*(1−exp(−hc*A/C))]
representative plate temperature = Tin + Q*R
mass = density_material*L*(plate_width*plate_thickness − N*w*h)
```

The friction and Nusselt expressions are Shah–London rectangular-duct polynomial fits. `f` is **Darcy**, four times the Fanning factor. Parallel-channel pressure drop equals one channel's drop, not N times that value. The square-duct series reference for Darcy f·Re is approximately 56.91; the rounded polynomial yields 56.9184. Nu for the square constant-temperature duct is approximately 2.9786.

The thermal network uses the exact energy balance for a constant-temperature wall and plug-flow bulk coolant, plus one-dimensional base conduction. This is internally consistent with the constant-wall-temperature Nu boundary condition. It is not a local maximum-temperature solution: all channel walls are assumed isothermal and equally effective. Real base spreading, rib efficiency, uneven heat loading and contact resistance can produce much higher device hot spots.

Sources: [University of Illinois engineering report, sections 2.1.2 and 2.2.2](https://www.ideals.illinois.edu/items/11059/bitstreams/40706/data.pdf); [Maya HTT rectangular-duct validation reference](https://help.mayahtt.com/tmg/topics/validation/VVC6_forced_convection_in_rectangular_duct.html); [F-Chart laminar duct reference](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm). F-Chart includes entrance corrections that this implementation does **not** implement.

## Validity and refusal behavior

- Smooth, straight, identical rectangular passages with equal flow; Newtonian incompressible single-phase liquid and constant properties.
- Flow classification: laminar Re<2300; transitional 2300≤Re<4000; turbulent Re≥4000. Only laminar correlations are implemented. Other regimes return null pressure and thermal estimates.
- Conservative application gates: Pe≥100; estimated entrance length `0.05*Re*Dh*max(1,Pr)` no greater than 10% of L; inlet and outlet within 10 K of the supplied property temperature; liquid operating envelope 5–80 °C. These are explicit application policies, not proven accuracy bounds. Entrance effects within the allowed fraction are still omitted.
- Outside those gates, correlation estimates are withheld and `model_feasible=false`. Energy-balance outlet temperature remains a diagnostic calculation and may itself indicate an invalid single-phase assumption. A diagnostic wall estimate above 80 °C is withheld and validity fails.
- Partial footprints generate an additional spreading-resistance warning. Local device maximum temperature remains unevaluated even when a representative plate-temperature inequality passes.
- Fluid defaults are illustrative water at 20 °C. The coolant label does not load a database or validate user properties. The user must supply consistent properties and provenance for their actual coolant. Material defaults are illustrative aluminum, not a verified alloy/temper specification.

Unsupported effects include headers, minor losses, maldistribution, roughness, fouling, entrance corrections, turbulence, phase change, buoyancy, temperature-dependent properties, environmental losses, contact/spreading resistance and local hot spots. `total_pressure_drop_pa` is null. No certified maximum device-temperature or complete pump-pressure claim is made.

## Constraint and optimization behavior

Constraint records contain name, value, limit, unit, status, margin and explanation. Positive margin means the inequality is satisfied. Unknown metrics use null rather than zero. Geometry envelope checks are algebraic; the connected B-Rep check remains `NOT_EVALUATED` until CAD build succeeds.

Search variables are explicitly listed in `optimization.bounds`: channel count, width, height and rib thickness. Omitted variables remain fixed. Maximum evaluations is 1–256. Candidate 0 is the starting design, candidates 1 and 2 are lower/upper corners, and subsequent candidates use a deterministic Halton sequence with bases 2,3,5,7 in sorted variable order. Count is rounded to an integer. Every attempted candidate consumes the budget, including duplicates, out-of-bounds starting designs and rejected geometries. Invalid candidates record reasons and cannot become best.

Ranking is lexicographic: supported model feasibility, correlation validity, number of failed constraints, representative temperature, channel pressure and mass. This is a transparent search, not a guarantee of a global optimum. With no feasible candidate, the best available diagnostic candidate is clearly labeled. With no valid candidates, best is null. Runtime and timestamp vary; candidate parameters and numerical results reproduce for identical inputs/software.

## API and UI

Open **Aether CEM** in the workspace header. Edit Requirements, Geometry, Coolant, Material and Constraints, or use the planner and review its assumptions. Use the structured-input editor to change optimization bounds. Edits invalidate the visible report. Select **Evaluate**, **Optimize**, or inspect an individual candidate. **Build selected CAD** creates a checked solid; close the panel to inspect the existing Three.js viewer and export STEP. **Save JSON report** downloads the complete analysis and retained search history.

`GET /aether/cold-plate/defaults` returns a complete example. `POST /validate` returns a validated specification. `POST /plan` accepts `{prompt, model, specification}`; `/evaluate`, `/optimize`, `/build` accept a specification. All except `/validate` return job IDs and use the existing `/jobs/{id}` polling protocol. The build result contains `cad` and `report`; STEP and server report use `/files/{id}/assembly.step` and `/files/{id}/engineering_report.json`.

The server build report is a fresh evaluation of the selected inputs. To retain search history, `/build?optimization_job_id=<id>` references a completed optimization job. The server verifies that the requested specification exactly matches a recorded candidate before including its history. The UI sends this reference automatically; downloaded and server reports retain the same history. Missing history after restart/eviction requires rerunning optimization. Report fields include version, UTC timestamp, canonical-input hash, complete inputs and properties, dimensions, equations, estimates, validity gates, warnings, constraints, optional optimizer history, and explicit `physical_validation:false` and `high_fidelity_simulation:false`. No confidence scores are generated.

## Reproducible example

[Complete input](examples/cold-plate.json) and [sample report](examples/cold-plate-report.json) are committed. Empty `{}` also selects schema defaults, but use the complete file for reproducibility.

200 × 60 × 8 mm plate; eight 2 × 2 mm channels; 2 mm ribs/base; actual cover 4 mm; 10 W over the full footprint; water 20 °C at 0.02 L/min. Default properties are included in the sample.

| Result | Value |
|---|---:|
| Velocity | 0.0104167 m/s |
| Hydraulic diameter | 0.002 m |
| Reynolds number | 20.7543 (laminar) |
| Darcy friction factor | 2.74248 |
| Channel pressure drop | 14.8521 Pa |
| Coolant rise | 7.18654 K |
| Coolant outlet | 27.1865 °C |
| Nusselt number | 2.978695 |
| Heat-transfer coefficient | 890.630 W/m²K |
| Thermal resistance | 0.719851 K/W |
| Representative plate temperature | 27.1985 °C |
| Solid mass | 0.24192 kg |

These numbers describe the idealized network, not measured device performance. A 40-attempt default search evaluates all configured variables; all candidates and the selected result are inspectable.

## Verification status and next milestone

Tests cover input bounds, unsafe/extra fields, flow exclusivity, hand-calculated square-duct pressure, energy balance, thermal-network balance, invalid correlation domains, constraints, repeatable search, candidate rejection, geometry dimensions/volume/channel centers/ribs, connected-solid validity, STEP re-import and API job/security behavior. Existing CAD and axial FEA regression tests must pass too.

No physical experiment or independent high-fidelity comparison has validated this cold-plate model. Milestone 2 should introduce a real thermal/fluid solver and benchmark/data-generation infrastructure, including manifold flow distribution and conjugate wall conduction, with mesh convergence and provenance. It is not implemented here.
