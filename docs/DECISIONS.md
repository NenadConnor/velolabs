# Architecture decisions

## Declarative AI output

The model returns a strict design object rather than executable CAD source. This limits expressiveness but makes input bounds, validation, persistence, and repair behavior inspectable. New geometry operations should be added to the schema and implemented by trusted code.

## Solid CAD as the source artifact

STEP B-rep geometry is the exported artifact. Browser triangles are derived previews and may be regenerated. This supports dimensional geometry and downstream CAD use while keeping the viewer responsive.

## Local native engine

Open CASCADE, Gmsh, and SciPy run in a Python service on the user's computer. This avoids exposing proprietary designs by default and supports native numerical libraries. The hosted interface remains optional and cannot provide full functionality without a reachable engine.

## Explicit stale state

Changing a dimension, feature, placement, or joint creates an unbuilt draft and invalidates prior exports and simulations. This prevents a result from appearing tied to geometry that no longer exists.

## Bounded engineering claims

Geometry validity, overlap checks, motion preview, numerical simulation, and physical validation are distinct states. The interface reports the evidence it has and states missing validation. A solver completion is never presented as certification.

## Personal alpha storage

Jobs and generated artifacts live below the ignored `work/` directory, while project files are saved explicitly by the user. This avoids pretending the alpha has durable cloud storage. Production persistence will require per-user isolation, lifecycle policy, and audit history.
