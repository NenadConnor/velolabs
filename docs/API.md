# Engine API

## Aether cold plate

The `/aether/cold-plate` router adds `GET /defaults`, `POST /validate`, and queued `POST /plan`, `/evaluate`, `/optimize`, `/build`. Evaluate/optimize/build consume only validated `ColdPlateSpecification` data. Plan returns reviewable structured inputs through the existing Ollama transport. Jobs share the existing limits and authentication. Build returns `{cad, report}` and exports `engineering_report.json` through the existing file route. See [AETHER_COLD_PLATE.md](AETHER_COLD_PLATE.md) for complete contracts, sample inputs and explicit numerical limitations.

The default base URL is `http://127.0.0.1:8765`. All responses use JSON except file downloads. When `VELOLABS_TOKEN` is configured, send it in `X-Velolabs-Token`.

## Health

`GET /health` reports the engine version, whether Ollama is reachable, the visible models, and a user-facing connection error when unavailable.

## Generate a design

`POST /generate`

```json
{
  "prompt": "Create a 100 x 60 x 8 mm plate with four 6 mm holes",
  "model": "glm-5.3-flash:cloud",
  "design": null,
  "history": []
}
```

The endpoint validates the request, queues a job, and returns `{ "id": "..." }`. `design` can contain the current complete design for conversational revision. The server asks the model for the entire revised design, validates it, builds each solid, exports STEP, checks overlaps, and returns either a completed result or a failure.

## Job status

`GET /jobs/{job_id}` returns `queued`, `planning`, `building`, `repairing`, `simulating`, `complete`, or `failed`. A completed generation result contains the validated design, preview meshes, solid checks, overlap checks, and design ID. Failed jobs include a bounded error string.

## Rebuild edited geometry

`POST /rebuild` accepts one complete design object matching the schema from `engine/schema.py`. It returns a job ID and does not call Ollama.

## Download STEP

`GET /files/{design_id}/assembly.step` downloads the built assembly. `GET /files/{design_id}/{part_id}.step` downloads one part. IDs and filenames must match the server's restricted patterns.

## Run a structural test

`POST /simulate/{design_id}`

```json
{
  "part_id": "plate",
  "axis": "x",
  "force": [0, 0, -100],
  "young_mpa": 69000,
  "poisson": 0.33,
  "yield_mpa": 276,
  "mesh_divisions": 8
}
```

The response is a job ID. The result includes mesh size, maximum nodal displacement, maximum element von Mises stress, yield-to-peak-stress ratio, free-degree residual, reaction vector, loaded area, settings, and assumptions. See [ENGINEERING.md](ENGINEERING.md) before interpreting these values.

## Limits

- Prompt: 3–12,000 characters.
- At most 24 parts, 40 features per part, and 160 features per design.
- Numeric geometry inputs are bounded to ±10,000 mm; positive dimensions are at most 10,000 mm.
- Polygon extrusions have at most 64 points.
- No more than four queued/running jobs in the personal engine.
- A generated preview mesh is limited to 180,000 triangles per part.
- FEA is limited to 20,000 nodes and 80,000 tetrahedra.
